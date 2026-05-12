import time
import logging
import functools
import traceback
from typing import Any, Callable, TypeVar
from core.error import MaxRetriesExceeded, DataFetchError
from core.logging import get_logger

logger = get_logger(__name__)


F = TypeVar("F", bound=Callable[..., Any])


def _is_empty(result: Any) -> bool:
    """
    Return True if yfinance gave us nothing useful.

    Covers:
        - None
        - Empty DataFrame (df.empty)
        - Empty dict {}
        - Empty list []
        - Dict with only an "error" key
    """
    if result is None:
        return True

    # pandas DataFrame / Series
    try:
        import pandas as pd

        if isinstance(result, pd.DataFrame):
            return result.empty
        if isinstance(result, pd.Series):
            return result.empty
    except ImportError:
        pass

    # dict — empty or only has error key
    if isinstance(result, dict):
        if len(result) == 0:
            return True
        if list(result.keys()) == ["error"]:
            return True

    # list / tuple
    if isinstance(result, (list, tuple)):
        return len(result) == 0

    return False


def retry_fetch(
    fn: Callable[[], Any],
    retries: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    label: str = "",
    caller: str = "",
) -> Any:
    """
    Call fn() and retry if the result is empty or an exception is raised.

    Returns:
        The first non-empty result.

    """
    current_delay = delay
    last_exc: Exception | None = None

    # Build a consistent origin tag shown in every log line for this retry chain
    origin = f"{caller}-{label}" if caller else label

    for attempt in range(1, retries + 1):
        attempt_tag = f"[{origin}] attempt {attempt}/{retries}"

        try:
            result = fn()

            if not _is_empty(result):
                if attempt > 1:
                    logger.info(f"{attempt_tag} succeeded")
                return result

            # yfinance returned something but it was empty — treat as failure
            last_exc = DataFetchError(source=label, symbol=origin)
            logger.warning(f"{attempt_tag} - empty result (no data returned)")

        except Exception as exc:
            last_exc = exc
            logger.warning(f"{attempt_tag} - {type(exc).__name__}: {exc}")

        if attempt < retries:
            logger.info(f"{attempt_tag} - retrying in {current_delay:.1f}s …")
            time.sleep(current_delay)
            current_delay *= backoff

    # All attempts exhausted — always raise, never return None silently
    logger.error(
        f"[{origin}] all {retries} attempts failed — raising MaxRetriesExceeded"
    )
    raise MaxRetriesExceeded(
        operation=origin,
        attempts=retries,
        original=last_exc,
    )


def with_retry(
    retries: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
) -> Callable[[F], F]:
    """
    Decorator — wraps any fetch function with retry logic.

    The decorated function's qualname + first argument (symbol) are used
    automatically as the log label. The call site (module + caller frame)
    is captured automatically and shown in every log line for this retry chain.
    """

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # provides more specific information than __name__, a dotted path from the global scope
            label = fn.__qualname__
            if args:
                label = f"{fn.__qualname__} [{args[0]}]"
            elif "symbol" in kwargs:
                label = f"{fn.__qualname__} [{kwargs['symbol']}]"

            # Caller: identify where this function was invoked from
            # We inspect the current call stack to capture the *external call site*
            # (i.e., the function/line that called the decorated function).
            #
            # This helps make logs self-contained:
            # instead of just "fetch failed", we get
            # "main.py:42 in update_prices → fetch failed"
            try:
                # Get the current call stack as a list of frames
                # The stack is ordered from oldest call → newest call (current line)
                frame = traceback.extract_stack()
                call_frame = frame[-2]  # -1 is this wrapper, -2 is the caller
                caller = f"{call_frame.filename.split('/')[-1]}:{call_frame.lineno} in {call_frame.name}"
            except Exception:
                caller = "unknown"

            return retry_fetch(
                fn=lambda: fn(*args, **kwargs),
                retries=retries,
                delay=delay,
                backoff=backoff,
                label=label,
                caller=caller,
            )

        return wrapper  # type: ignore

    return decorator
