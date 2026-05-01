import json
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from tools.utils.retry_utils import with_retry
from tools.utils.market_tool_helper import(
    _fetch_df,_10d_pct_change,_monthly_10d_pct_change,
    _quarterly_pct_change,_high_low_vs_avg
)
from core.error import (
    handle_tool_errors,
    DataFetchError,
    DataParseError,
    ToolExecutionError,
    MaxRetriesExceeded,
    AgentError,
)
from core.logging import get_logger
logger = get_logger(__name__)

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

    Raises:
        DataFetchError: If market data cannot be retrieved.
        DataParseError: If fetched data is malformed or missing expected columns.

    """
    df = _fetch_df(symbol)

    try:
        high_pct, low_pct = _high_low_vs_avg(df)

        metrics = {
            "10d_pct_change": _10d_pct_change(df["Close"]),
            "monthly_10d_pct_change": _monthly_10d_pct_change(df),
            "quarterly_pct_change": _quarterly_pct_change(df),
            "high_to_avg_change_pct": high_pct,
            "low_to_avg_change_pct": low_pct,
        }
        logger.info(f"Computed metrics for {name}")

    except (DataFetchError, DataParseError):
        logger.error(f"Data issue in {name}")
        raise   
    except Exception as exc:
        logger.exception(f"Unexpected error in {name}")
        raise DataParseError(
            f"Failed to compute metrics for {symbol}: {exc}", original=exc
        )

    return name, metrics

@handle_tool_errors("get_market_snapshot")
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
                "_errors": {failed_tickers: error_messages}  # only present on partial failures
            }

    Raises:
        ToolExecutionError: Raised by @handle_tool_errors on unhandled exceptions.

    Agent Use:
        - Primary tool function for market-wide state representation
        - Designed for downstream LLM reasoning, ranking, or signal generation
    """
    logger.info("Starting market snapshot generation")
    n_workers = max_workers or len(tickers)
    results: dict[str, Any] = {}
    errors: dict[str, str] = {}
    logger.info(f"Using {n_workers} workers")

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
                logger.info(f"Processed {key}")
            except (DataFetchError, DataParseError, AgentError) as exc:
               
                errors[name] = str(exc)
                logger.error(f"{name} failed: {exc}")
            except Exception as exc:
                errors[name] = f"[{type(exc).__name__}] {exc}"
                logger.exception(f"{name} crashed unexpectedly")

    if errors:
        results["_errors"] = errors

    return results


if __name__ == "__main__":
    from core.logging import bootstrap_standalone
    bootstrap_standalone(__file__)
    logger.info("Starting market snapshot generation...")

    try:
        snapshot = get_market_snapshot()
    except Exception:
        logger.exception("Market snapshot generation failed")
        raise  

    try:
        output = json.dumps(snapshot, indent=2)
        print(output)
    except Exception:
        logger.exception("JSON serialization failed even after fallback")
        raise

    with open("market_snapshot.json", "w") as f:
        f.write(output)
        logger.info("Saved → market_snapshot.json")


    logger.info("Market snapshot pipeline completed successfully")