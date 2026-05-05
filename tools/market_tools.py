import json
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from tools.utils.retry_utils import with_retry
from tools.utils.market_tool_helper import(
    _10d_pct_change,_monthly_10d_pct_change,
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

TICKERS: dict[str, str] = {
    "GSPC":  "^GSPC",
    "VIX":   "^VIX",
    "NSEI":  "^NSEI",
    "BSESN": "^BSESN",
    "IXIC":  "^IXIC",
}

@with_retry(retries=3, delay=2.0, backoff=2.0)
def fetch_df(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical market data for a given ticker ticker.
    """
    logger.debug(f"Downloading OHLCV data | ticker={ticker}")

    result = {
        "data": None,
        "status": "failed",
        "error": None,
        "ticker": ticker,
        "source": "yfinance",
    }
    
    try:
        df = yf.download(
            ticker, 
            period=period, 
            interval=interval, 
            auto_adjust=True, 
            progress=False
        )
    except Exception as exc:
        logger.exception(f"yfinance.download failed | ticker={ticker} | {exc}")
        result["error"] = f"download_failed: {exc}"
        return result
    
    if df is None or df.empty:
        logger.warning(f"Empty DataFrame | ticker={ticker}")
        result["error"] = "empty_dataframe"
        return result

    try:
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df.sort_index(inplace=True)

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

    except Exception as exc:
        logger.exception(f"Normalization failed | ticker={ticker} | {exc}")
        result["error"] = f"parse_error: {exc}"
        result["data"] = df 
        result["status"] = "partial"
        return result

    logger.info(f"Fetched {len(df)} bars | ticker={ticker}")

    result["data"] = df
    result["status"] = "success"
    return result

    
def extract_metrics(ticker: str, status: str, df: pd.DataFrame | None) -> tuple[str, dict[str, Any]]:
    """
    Extract full metric set for a single market index.
    Fully agent-safe: no external guards required.
    Always returns structured output.
    """

    logger.debug(f"Computing metrics | ticker={ticker}")

    metrics = {
        "10d_pct_change": None,
        "monthly_10d_pct_change": None,
        "quarterly_pct_change": None,
        "high_to_avg_change_pct": None,
        "low_to_avg_change_pct": None,
        "status": "failed",
        "error": None,
    }

    if status != "success":
        metrics["status"] = "skipped"
        metrics["error"] = f"fetch_status={status}"
        return ticker, metrics

    if df is None or df.empty:
        metrics["status"] = "failed"
        metrics["error"] = "empty_or_missing_dataframe"
        return ticker, metrics

    if "Close" not in df.columns:
        metrics["status"] = "failed"
        metrics["error"] = "missing_close_column"
        return ticker, metrics

    try:
        try:
            high_pct, low_pct = _high_low_vs_avg(df)
        except Exception as e:
            logger.warning(f"High/Low vs Avg failed | {ticker} | {e}")
            high_pct, low_pct = None, None

        def safe_call(fn, *args):
            try:
                return fn(*args)
            except Exception as e:
                logger.warning(f"{fn.__name__} failed | {ticker} | {e}")
                return None

        metrics.update({
            "10d_pct_change": safe_call(_10d_pct_change, df["Close"]),
            "monthly_10d_pct_change": safe_call(_monthly_10d_pct_change, df),
            "quarterly_pct_change": safe_call(_quarterly_pct_change, df),
            "high_to_avg_change_pct": high_pct,
            "low_to_avg_change_pct": low_pct,
            "status": "ok",
        })

        logger.info(f"Computed metrics successfully | ticker={ticker}")
        return ticker, metrics

    except Exception as exc:
        logger.exception(f"Unexpected metrics failure | ticker={ticker} | {exc}")
        metrics["status"] = "failed"
        metrics["error"] = str(exc)
        return ticker, metrics
    


if __name__ == "__main__":
    print("Starting market pipeline")

    results = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_name = {
            executor.submit(fetch_df, ticker_symbol): name
            for name, ticker_symbol in TICKERS.items()
        }

        for future in as_completed(future_to_name):
            name = future_to_name[future]

            try:
                fetch_result = future.result()
            except Exception as exc:
                print(f"Thread failed | ticker={name} | {exc}")
                results[name] = {
                    "fetch_status": "failed",
                    "metrics": {
                        "status": "failed",
                        "error": str(exc),
                    }
                }
                continue

            ticker = name
            status = fetch_result.get("status")
            df = fetch_result.get("data")

            _, metrics = extract_metrics(ticker, status, df)

            results[name] = {
                "fetch_status": status,
                "metrics": metrics
            }

    print("Market pipeline completed")

    with open("market_snapshot.json", "w") as f:
      f.write(json.dumps(results, indent=2))