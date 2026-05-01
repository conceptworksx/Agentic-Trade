import logging
from core.error import (
    NodeExecutionError, RateLimitError, AuthenticationError,
    TokenLimitError, ToolCallError, MaxRetriesExceeded, AgentError
)
from core.logging import setup_logging
setup_logging()      

from graph.builder import app


def run_app(ticker: str):
    try:
        result = app.invoke({
                "ticker_of_company":ticker,
                "investment_debate": {
                "bull_thesis": "",
                "bear_thesis": "",
                "debate_history": "",
                "final_decision": "",
                "current_response": "",
                "debate_rounds": 0  
                 },
                "messages":[]
        })

        return result

    except AuthenticationError as e:
        # Hard stop — no point retrying, fix the API key
        logging.critical(f"Auth failed: {e}")
        raise SystemExit(1)

    except RateLimitError as e:
        # LangGraph already retried — this means retries exhausted
        logging.error(f"Rate limit exhausted after retries: {e}")
        raise

    except TokenLimitError as e:
        # Prompt too long — need to reduce data sent to LLM
        logging.error(f"Token limit hit: {e} — reduce prompt size")
        raise

    except ToolCallError as e:
        logging.error(
            f"Tool call failed: {e}\n"
            f"Failed generation: {e.failed_generation[:500]}"
        )
        raise

    except MaxRetriesExceeded as e:
        logging.error(f"Gave up after {e.attempts} attempts on: {e.operation}")
        raise

    except NodeExecutionError as e:
        logging.error(f"Node '{e.node_name}' crashed: {e}")
        raise

    except AgentError as e:
        # Catch-all for any typed error not handled above
        logging.error(f"Agent error [{type(e).__name__}]: {e}")
        raise

    except Exception as e:
        # True unknown — log full traceback
        logging.exception(f"Unhandled exception in app.invoke: {e}")
        raise


if __name__ == "__main__":
    run_app("RELIANCE.NS")