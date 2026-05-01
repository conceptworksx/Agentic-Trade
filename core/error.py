import time
import logging
import functools
import traceback
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class AgentError(Exception):
    """Base class for all agentic workflow errors."""
    def __init__(self, message: str, original: Exception | None = None):
        super().__init__(message)
        self.original  = original
        self.message   = message

    def __str__(self):
        if self.original:
            return f"{self.message} | caused by: {type(self.original).__name__}: {self.original}"
        return self.message


# ── LLM / Model errors ───────────────────────────────────────

class RateLimitError(AgentError):
    """
    API rate limit or quota exceeded.
    Groq: 429, groq.RateLimitError
    Anthropic: 429, anthropic.RateLimitError
    """
    pass


class TokenLimitError(AgentError):
    """
    Prompt or completion exceeds model context window.
    Groq: 400 with 'context_length_exceeded' in message
    """
    pass


class ToolCallError(AgentError):
    """
    LLM generated invalid tool call JSON or skipped tool calling
    and wrote prose instead.
    Groq: 400 tool_use_failed with failed_generation in response
    """
    def __init__(self, message: str, failed_generation: str = "",
                 original: Exception | None = None):
        super().__init__(message, original)
        self.failed_generation = failed_generation


class ModelUnavailableError(AgentError):
    """
    Model endpoint is down or overloaded.
    Groq: 503, 502
    """
    pass


class AuthenticationError(AgentError):
    """
    Invalid or expired API key.
    Groq/Anthropic: 401
    """
    pass


class BadRequestError(AgentError):
    """
    Malformed request — usually prompt/schema mismatch.
    Groq: 400 (non tool_use_failed variant)
    """
    pass


# ── Tool / Data errors ───────────────────────────────────────

class ToolExecutionError(AgentError):
    """
    Tool function raised an exception during execution.
    e.g. yfinance returned None, network timeout in data fetch.
    """
    def __init__(self, tool_name: str, message: str,
                 original: Exception | None = None):
        super().__init__(message, original)
        self.tool_name = tool_name


class DataFetchError(AgentError):
    """
    yfinance or external data source returned empty/None.
    Retries exhausted.
    """
    def __init__(self, source: str, symbol: str,
                 original: Exception | None = None):
        msg = f"Data fetch failed for {symbol} from {source}"
        super().__init__(msg, original)
        self.source = source
        self.symbol = symbol


class DataParseError(AgentError):
    """
    Fetched data was malformed or missing expected fields.
    """
    pass


# ── Graph / Workflow errors ───────────────────────────────────

class NodeExecutionError(AgentError):
    """
    A LangGraph node raised an unhandled exception.
    """
    def __init__(self, node_name: str, message: str,
                 original: Exception | None = None):
        super().__init__(message, original)
        self.node_name = node_name


class StateError(AgentError):
    """
    Required key missing from LangGraph state dict.
    e.g. state["ticker_of_company"] is None or absent.
    """
    def __init__(self, key: str, original: Exception | None = None):
        super().__init__(f"Required state key missing or None: '{key}'", original)
        self.key = key


class MaxRetriesExceeded(AgentError):
    """
    Retry budget exhausted across any retryable operation.
    """
    def __init__(self, operation: str, attempts: int,
                 original: Exception | None = None):
        super().__init__(
            f"Max retries ({attempts}) exceeded for: {operation}", original
        )
        self.operation = operation
        self.attempts  = attempts



#  2. ERROR CLASSIFIER


def classify_llm_error(exc: Exception) -> AgentError:
    """
    Inspect a raw LLM/Groq/Anthropic exception and return
    the correct typed AgentError subclass.

    Handles:
        - groq.RateLimitError
        - groq.BadRequestError (tool_use_failed, context_length, generic)
        - groq.APIStatusError (502, 503)
        - groq.AuthenticationError
        - anthropic.* equivalents
        - Generic HTTP / network errors
    """
    exc_str  = str(exc).lower()
    exc_type = type(exc).__name__

    # ── Rate limit ────────────────────────────────────────────
    if any(k in exc_str for k in ["rate_limit", "rate limit", "429",
                                   "too many requests", "quota"]):
        return RateLimitError(
            "API rate limit hit — back off and retry", original=exc
        )

    # ── Tool call failure (Groq specific) ─────────────────────
    if "tool_use_failed" in exc_str or "failed_generation" in exc_str:
        # Extract the failed_generation text if present
        failed_gen = ""
        if hasattr(exc, "response"):
            try:
                body = exc.response.json()
                failed_gen = (body.get("error", {})
                                  .get("failed_generation", ""))
            except Exception:
                pass
        return ToolCallError(
            "LLM generated prose instead of a valid tool call JSON. "
            "Prompt may be too narrative — add explicit tool-first instruction.",
            failed_generation=failed_gen,
            original=exc,
        )

    # ── Context / token limit ─────────────────────────────────
    if any(k in exc_str for k in ["context_length", "token", "maximum context",
                                   "too long", "max_tokens"]):
        return TokenLimitError(
            "Prompt exceeds model context window — reduce input size", original=exc
        )

    # ── Auth ─────────────────────────────────────────────────
    if any(k in exc_str for k in ["401", "authentication", "invalid api key",
                                   "unauthorized"]):
        return AuthenticationError(
            "Invalid or expired API key", original=exc
        )

    # ── Service unavailable ───────────────────────────────────
    if any(k in exc_str for k in ["502", "503", "service unavailable",
                                   "bad gateway", "overloaded"]):
        return ModelUnavailableError(
            "Model endpoint unavailable — retry later", original=exc
        )

    # ── Generic 400 bad request ───────────────────────────────
    if "400" in exc_str or "bad_request" in exc_str.replace(" ", "_"):
        return BadRequestError(
            f"Bad request to LLM API: {exc}", original=exc
        )

    # ── Fallback ──────────────────────────────────────────────
    return AgentError(f"Unclassified LLM error [{exc_type}]: {exc}", original=exc)



#  3. RETRY CONFIG

# Which errors are safe to retry automatically
RETRYABLE_ERRORS = (RateLimitError, ModelUnavailableError, ToolCallError)

# How long to wait before retrying each error type
RETRY_DELAYS: dict[type, float] = {
    RateLimitError:       30.0,   # back off hard on rate limits
    ModelUnavailableError: 5.0,
    ToolCallError:         2.0,   # usually a transient model glitch
}



#  4. DECORATORS

def handle_llm_errors(
    retries: int = 3,
    reraise: bool = True,
) -> Callable[[F], F]:
    """
    Decorator for agent _invoke() methods and any function that
    calls an LLM API directly.

    - Classifies raw exceptions into typed AgentErrors
    - Retries RateLimitError, ModelUnavailableError, ToolCallError
    - Logs every attempt with context
    - Re-raises as typed AgentError after exhausting retries

    Usage:
        class BaseAgent:
            @handle_llm_errors(retries=3)
            def _invoke(self, messages):
                ...
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            label = fn.__qualname__
            last_error: AgentError | None = None

            for attempt in range(1, retries + 1):
                try:
                    return fn(*args, **kwargs)

                except AgentError:
                    raise   # already classified, don't double-wrap

                except Exception as raw_exc:
                    typed = classify_llm_error(raw_exc)
                    last_error = typed

                    logger.warning(
                        f"[{label}] attempt {attempt}/{retries} "
                        f"→ {type(typed).__name__}: {typed.message}"
                    )

                    # Log failed_generation for debugging ToolCallError
                    if isinstance(typed, ToolCallError) and typed.failed_generation:
                        logger.debug(
                            f"[{label}] failed_generation preview: "
                            f"{typed.failed_generation[:300]}"
                        )

                    if isinstance(typed, AuthenticationError):
                        # No point retrying auth errors
                        logger.error(f"[{label}] Auth error — not retrying")
                        raise typed

                    if not isinstance(typed, RETRYABLE_ERRORS):
                        logger.error(f"[{label}] Non-retryable error — raising")
                        raise typed

                    if attempt < retries:
                        delay = RETRY_DELAYS.get(type(typed), 3.0)
                        logger.info(f"[{label}] retrying in {delay}s …")
                        time.sleep(delay)

            if reraise and last_error:
                raise MaxRetriesExceeded(
                    operation=label,
                    attempts=retries,
                    original=last_error,
                )
        return wrapper  # type: ignore
    return decorator


def handle_tool_errors(tool_name: str) -> Callable[[F], F]:
    """
    Decorator for individual tool functions (get_income_stmt, etc.)

    - Wraps any exception as ToolExecutionError with the tool name
    - Logs the full traceback for debugging
    - Does NOT retry — retry is handled at the data fetch level
      by retry_utils.with_retry

    Usage:
        @handle_tool_errors("get_balance_sheet")
        def get_balance_sheet(symbol: str) -> dict:
            ...
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except (ToolExecutionError, DataFetchError, AgentError):
                raise   # already typed, pass through
            except Exception as exc:
                tb = traceback.format_exc()
                logger.error(
                    f"[tool:{tool_name}] execution failed\n"
                    f"args={args} kwargs={kwargs}\n{tb}"
                )
                raise ToolExecutionError(
                    tool_name=tool_name,
                    message=f"Tool '{tool_name}' failed: {exc}",
                    original=exc,
                )
        return wrapper  # type: ignore
    return decorator


def handle_node_errors(node_name: str) -> Callable[[F], F]:
    """
    Decorator for LangGraph node functions in graph/nodes.py

    - Catches everything that escapes agent/tool layers
    - Wraps as NodeExecutionError with the node name
    - Logs state snapshot for debugging
    - LangGraph will surface this cleanly instead of a raw traceback

    Usage:
        @handle_node_errors("fundamental_analyst")
        def run_fundamental_analyst(state: dict) -> dict:
            ...
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(state: dict, *args, **kwargs):
            try:
                # Validate required state keys before running
                return fn(state, *args, **kwargs)

            except NodeExecutionError:
                raise
            except (AgentError, ToolExecutionError) as typed:
                logger.error(
                    f"[node:{node_name}] typed error: "
                    f"{type(typed).__name__}: {typed}"
                )
                raise NodeExecutionError(
                    node_name=node_name,
                    message=str(typed),
                    original=typed,
                )
            except Exception as exc:
                tb = traceback.format_exc()
                logger.error(
                    f"[node:{node_name}] unhandled exception\n"
                    f"state_keys={list(state.keys())}\n{tb}"
                )
                raise NodeExecutionError(
                    node_name=node_name,
                    message=f"Node '{node_name}' crashed: {exc}",
                    original=exc,
                )
        return wrapper  # type: ignore
    return decorator


#  5. STATE VALIDATOR

def validate_state(state: dict, *required_keys: str) -> None:
    """
    Assert that all required keys exist in the LangGraph state
    and are not None/empty.

    Raises StateError immediately with the missing key name
    instead of a cryptic KeyError deep in the stack.

    Usage:
        def run_fundamental_analyst(state):
            validate_state(state, "ticker_of_company", "messages")
            ...
    """
    for key in required_keys:
        if key not in state or state[key] is None or state[key] == "":
            raise StateError(key=key)