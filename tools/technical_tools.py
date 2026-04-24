import json
import warnings
from typing import Any

from utils.technical_tool_helper import (
    fetch_df,
    compute_moving_averages,
    compute_rsi,
    compute_macd,
    compute_bollinger,
    compute_atr,
    compute_vwma,
    compute_mfi,
    compute_volume,
    compute_price_levels,
)

warnings.filterwarnings("ignore")

"""
Technical Analysis Tool (Agentic AI Utility)

Entry point for the technical analysis tool.
Import get_technical_snapshot() and register it in your agent's tool dispatcher.

Intended Use:
    - Equity technical analysis agents
    - Buy/Hold/Sell signal generation pipelines
    - Stock screening and research workflows

Output:
    JSON-serialisable dict with all technical signals for a given ticker.
"""


def get_technical_snapshot(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
) -> dict[str, Any]:
    """
    Generate a full technical analysis snapshot for a single equity ticker.

    This is the primary entry point for agentic systems.

    Process:
        1. Fetch OHLCV data via yfinance
        2. Compute all technical indicators
        3. Aggregate into a single structured dictionary

    Args:
        symbol   (str): Yahoo Finance ticker (e.g. 'RELIANCE.NS', 'TCS.NS', 'AAPL').
        period   (str): Lookback window — '6mo', '1y', '2y' (default '1y').
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
        ValueError: If symbol returns empty data from yfinance.
    """
    df = fetch_df(symbol, period=period, interval=interval)

    if df.empty:
        raise ValueError(f"No data returned for symbol: {symbol!r}")

    return {
        "ticker":          symbol,
        "price_levels":    compute_price_levels(df),
        "moving_averages": compute_moving_averages(df),
        "rsi":             compute_rsi(df),
        "macd":            compute_macd(df),
        "bollinger":       compute_bollinger(df),
        "atr":             compute_atr(df),
        "vwma":            compute_vwma(df),
        "mfi":             compute_mfi(df),
        "volume":          compute_volume(df),
    }


# if __name__ == "__main__":
#     print("Fetching technical snapshot …\n")
#     snapshot = get_technical_snapshot("RELIANCE.NS")
#     output = json.dumps(snapshot, indent=2)
#     print(output)

#     with open("technical_snapshot.json", "w") as f:
#         f.write(output)

#     print("\nSaved → technical_snapshot.json")