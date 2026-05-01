import json
import yfinance as yf
import pandas as pd
from tools.utils.retry_utils import with_retry
from core.error import (
    handle_tool_errors,
    DataFetchError,
    DataParseError,
    MaxRetriesExceeded,
    AgentError,
)
from core.logging import get_logger
logger = get_logger(__name__)


@with_retry(retries=3, delay=2.0, backoff=2.0)
def _fetch_df(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical market data for a given ticker symbol.
    """
    try:
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=True, progress=False)
    except Exception as exc:
        raise DataFetchError(source="yfinance.download", symbol=symbol, original=exc)

    if df is None or df.empty:
        raise DataFetchError(source="yfinance.download", symbol=symbol)

    try:
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df.sort_index(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
    except Exception as exc:
        raise DataParseError(
            f"Failed to normalize DataFrame for {symbol}: {exc}", original=exc
        )

    return df


def _10d_pct_change(close: pd.Series) -> float | None:
    """
    Compute most recent 10-trading-day percentage change.
    """
    if len(close) < 11:
        return None
    return round((close.iloc[-1] - close.iloc[-11]) / close.iloc[-11] * 100, 4)


def _monthly_10d_pct_change(df: pd.DataFrame) -> list[float]:
    """
    Compute 10-day chunked returns over the most recent 30 trading days.
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

    Returns:
        list[float]: [Q1, Q2, Q3, Q4]
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
    """
    avg_close = df["Close"].mean()
    max_high = df["High"].max()
    min_low = df["Low"].min()

    return (
        round((max_high - avg_close) / avg_close * 100, 4),
        round((avg_close - min_low) / avg_close * 100, 4),
    )
