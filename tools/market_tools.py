import json
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

"""
Market Metrics Tool (Agentic AI Utility)

This module is designed to be used as a structured data tool for an AI agent.
It fetches market data for major indices and computes standardized financial
features such as returns, volatility proxies, and range-based metrics.

Intended Use:
- Financial market analysis agents
- Macro trend monitoring systems
- Automated trading or research pipelines

Output:
A structured JSON-like dictionary containing metrics per ticker.
"""

TICKERS: dict[str, str] = {
    "GSPC":  "^GSPC",
    "VIX":   "^VIX",
    "NSEI":  "^NSEI",
    "BSESN": "^BSESN",
    "IXIC":  "^IXIC",
}


def fetch_df(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical market data for a given ticker symbol.

    Args:
        symbol (str): Yahoo Finance ticker symbol.
        period (str): Data range (default: '1y').
        interval (str): Data granularity (default: '1d').

    Returns:
        pd.DataFrame: Cleaned OHLCV time series with timezone removed.

    Notes for Agents:
        - Output is time-sorted and normalized.
        - Used as the base dataset for all downstream metric calculations.
    """
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df.sort_index(inplace=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def _10d_pct_change(close: pd.Series) -> float | None:
    """
    Compute most recent 10-trading-day percentage change.

    Definition:
        (latest_close - close_10_days_ago) / close_10_days_ago * 100

    Returns:
        float | None: Percentage change or None if insufficient data.

    Agent Use:
        Captures short-term momentum signal.
    """
    if len(close) < 11:
        return None
    return round((close.iloc[-1] - close.iloc[-11]) / close.iloc[-11] * 100, 4)


def _monthly_10d_pct_change(df: pd.DataFrame) -> list[float]:
    """
    Compute 10-day chunked returns over the most recent 30 trading days.

    Logic:
        - Split last 30 trading days into 3 equal windows (10 days each)
        - Compute return for each window:
            (last_close - first_close) / first_close * 100

    Returns:
        list[float]: [oldest_chunk, middle_chunk, newest_chunk]

    Agent Use:
        Captures short-term regime shifts within ~1 month.
    """
    last_30 = df["Close"].iloc[-30:]

    results = []
    for i in range(3):
        chunk = last_30.iloc[i*10 : (i+1)*10]
        if len(chunk) < 2:
            results.append(None)
            continue
        pct = round((chunk.iloc[-1] - chunk.iloc[0]) / chunk.iloc[0] * 100, 4)
        results.append(pct)

    return results


def _quarterly_pct_change(df: pd.DataFrame) -> list[float]:
    """
    Compute approximate quarterly returns over the last 1 year of data.

    Logic:
        - Split dataset into 4 equal segments (by row count)
        - Compute return per segment:
            (last_close - first_close) / first_close * 100

    Returns:
        list[float]: [Q1, Q2, Q3, Q4]

    Agent Use:
        Provides medium-term trend structure across a year.
    """
    n = len(df)
    q_size = n // 4

    results = []
    for i in range(4):
        start = i * q_size
        end = (i + 1) * q_size if i < 3 else n
        chunk = df["Close"].iloc[start:end]

        if len(chunk) < 2:
            results.append(None)
            continue

        pct = round((chunk.iloc[-1] - chunk.iloc[0]) / chunk.iloc[0] * 100, 4)
        results.append(pct)

    return results


def _high_low_vs_avg(df: pd.DataFrame) -> tuple[float, float]:
    """
    Compute range deviation metrics relative to average closing price.

    Returns:
        high_to_avg_pct: (max_high - avg_close) / avg_close * 100
        low_to_avg_pct : (avg_close - min_low) / avg_close * 100

    Agent Use:
        Measures dispersion / volatility asymmetry over the period.
    """
    avg_close = df["Close"].mean()
    max_high = df["High"].max()
    min_low = df["Low"].min()

    return (
        round((max_high - avg_close) / avg_close * 100, 4),
        round((avg_close - min_low) / avg_close * 100, 4),
    )


def extract_metrics(name: str, symbol: str) -> tuple[str, dict[str, Any]]:
    """
    Extract full metric set for a single market index.

    Args:
        name (str): Human-readable ticker label.
        symbol (str): Yahoo Finance ticker symbol.

    Returns:
        tuple:
            - name (str)
            - metrics (dict): Structured financial feature set

    Output Schema:
        {
            "10d_pct_change": float | None,
            "monthly_10d_pct_change": list[float],
            "quarterly_pct_change": list[float],
            "high_to_avg_change_pct": float,
            "low_to_avg_change_pct": float
        }

    Agent Use:
        Core feature generator for a single asset.
    """
    df = fetch_df(symbol)

    high_pct, low_pct = _high_low_vs_avg(df)

    metrics = {
        "10d_pct_change": _10d_pct_change(df["Close"]),
        "monthly_10d_pct_change": _monthly_10d_pct_change(df),
        "quarterly_pct_change": _quarterly_pct_change(df),
        "high_to_avg_change_pct": high_pct,
        "low_to_avg_change_pct": low_pct,
    }
    return name, metrics


def get_market_snapshot(
    tickers: dict[str, str] = TICKERS,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """
    Build a full multi-asset market snapshot.

    This is the main entry point for agentic systems.

    Process:
        1. Fetch historical data for each ticker in parallel
        2. Compute standardized feature set per asset
        3. Aggregate results into a single structured dictionary

    Args:
        tickers (dict[str, str]): Mapping of asset names to Yahoo Finance symbols.
        max_workers (int | None): Thread pool size for parallel execution.

    Returns:
        dict[str, Any]:
            {
                "<ticker_name>": {metrics...},
                "_errors": {failed_tickers: error_messages}  # optional
            }

    Agent Use:
        - Primary tool function for market-wide state representation
        - Designed for downstream LLM reasoning, ranking, or signal generation
    """
    n_workers = max_workers or len(tickers)
    results: dict[str, Any] = {}
    errors: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = {
            pool.submit(extract_metrics, name, sym): name
            for name, sym in tickers.items()
        }

        for fut in as_completed(futures):
            name = futures[fut]
            try:
                key, metrics = fut.result()
                results[key] = metrics
                print(f"  ✓  {key}")
            except Exception as exc:
                errors[name] = str(exc)
                print(f"  ✗  {name}: {exc}")

    if errors:
        results["_errors"] = errors

    return results



# if __name__ == "__main__":
#     print("Fetching market data …\n")
#     snapshot = get_market_snapshot()
#     output = json.dumps(snapshot, indent=2)
#     print(output)

#     with open("market_snapshot.json", "w") as f:
#         f.write(output)

#     print("\nSaved → market_snapshot.json")