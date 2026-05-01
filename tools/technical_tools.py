import json
import warnings
from typing import Any
from tools.utils.technical_tool_helper import (
    _fetch_df,
    _compute_moving_averages,
    _compute_rsi,
    _compute_macd,
    _compute_bollinger,
    _compute_atr,
    _compute_vwma,
    _compute_mfi,
    _compute_volume,
    _compute_price_levels,
)
from core.error import (
    handle_tool_errors,
    DataFetchError,
    DataParseError,
    MaxRetriesExceeded,
    AgentError,
)
from core.logging import get_logger
logger = get_logger(__name__)

warnings.filterwarnings("ignore")

@handle_tool_errors("get_technical_snapshot")
def get_technical_snapshot(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
) -> dict[str, Any]:
    """
    Generate a full technical analysis snapshot for a single equity ticker.

    This is the primary entry point for agentic systems.

    Process:
        1. Fetch OHLCV data via yfinance (retried, raises on failure)
        2. Compute all technical indicators (each raises DataParseError on failure)
        3. Aggregate into a single structured dictionary

    Args:
        symbol (str): Yahoo Finance ticker (e.g. 'RELIANCE.NS', 'TCS.NS', 'AAPL').
        period (str): Lookback window — '6mo', '1y', '2y' (default '1y').
        interval (str): Bar size — '1d' daily, '1h' hourly, '1wk' weekly (default '1d').

    Returns:
        dict[str, Any]:
            {
                "ticker":          str,
                "price_levels":    {...},
                "moving_averages": {...},
                "rsi":             {...},
                "macd":            {...},
                "bollinger":       {...},
                "atr":             {...},
                "vwma":            {...},
                "mfi":             {...},
                "volume":          {...},
            }

    Agent Use:
        - Primary tool function for single-stock technical state
        - All values are JSON-serialisable (float, int, bool, str, None)
        - Combine with get_market_snapshot() for macro-aware analysis

    Raises:
        DataFetchError: If yfinance returns empty/None data for the symbol.
        DataParseError: If any indicator computation fails on malformed data.
        MaxRetriesExceeded: If all fetch retries are exhausted.
        ToolExecutionError: Raised by @handle_tool_errors for any unhandled exception.
    """
    # fetch_df raises DataFetchError / DataParseError / MaxRetriesExceeded.
    # All are AgentError subclasses — @handle_tool_errors wraps anything
    # that escapes as ToolExecutionError, so no bare except needed here.
    df = _fetch_df(symbol, period=period, interval=interval)

    return {
        "ticker":          symbol,
        "price_levels":    _compute_price_levels(df),
        "moving_averages": _compute_moving_averages(df),
        "rsi":             _compute_rsi(df),
        "macd":            _compute_macd(df),
        "bollinger":       _compute_bollinger(df),
        "atr":             _compute_atr(df),
        "vwma":            _compute_vwma(df),
        "mfi":             _compute_mfi(df),
        "volume":          _compute_volume(df),
    }


if __name__ == "__main__":
    from core.logging import bootstrap_standalone
    bootstrap_standalone(__file__)
    
    logger.info("Fetching technical snapshot …\n")
    snapshot = get_technical_snapshot("RELIANCE.NS")
    output = json.dumps(snapshot, indent=2)
    print(output)

    with open("technical_snapshot.json", "w") as f:
        f.write(output)

    logger.info("\nSaved → technical_snapshot.json")