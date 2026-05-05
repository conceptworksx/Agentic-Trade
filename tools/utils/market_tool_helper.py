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


def _10d_pct_change(close: pd.Series) -> float | None:
    """Compute most recent 10-trading-day percentage change (safe)."""

    try:
        if close is None or len(close) < 11:
            return None

        prev = float(close.iloc[-11])
        curr = float(close.iloc[-1])

        if prev == 0:
            return None

        return round((curr - prev) / prev * 100, 4)

    except Exception:
        return None


def _monthly_10d_pct_change(df: pd.DataFrame) -> list[float | None]:
    """Compute 10-day chunked returns over last ~30 trading days (safe)."""

    try:
        if df is None or "Close" not in df:
            return [None, None, None]

        last_30 = df["Close"].dropna().iloc[-30:]

        results = []
        for i in range(3):
            chunk = last_30.iloc[i * 10 : (i + 1) * 10]

            if len(chunk) < 2:
                results.append(None)
                continue

            start = float(chunk.iloc[0])
            end = float(chunk.iloc[-1])

            if start == 0:
                results.append(None)
                continue

            pct = round((end - start) / start * 100, 4)
            results.append(pct)

        return results

    except Exception:
        return [None, None, None]


def _quarterly_pct_change(df: pd.DataFrame) -> list[float | None]:
    """Compute approximate quarterly returns over dataset (safe)."""

    try:
        if df is None or "Close" not in df:
            return [None, None, None, None]

        close = df["Close"].dropna()
        n = len(close)

        if n < 4:
            return [None, None, None, None]

        q_size = max(n // 4, 1)

        results = []
        for i in range(4):
            start = i * q_size
            end = (i + 1) * q_size if i < 3 else n

            chunk = close.iloc[start:end]

            if len(chunk) < 2:
                results.append(None)
                continue

            s = float(chunk.iloc[0])
            e = float(chunk.iloc[-1])

            if s == 0:
                results.append(None)
                continue

            pct = round((e - s) / s * 100, 4)
            results.append(pct)

        return results

    except Exception:
        return [None, None, None, None]


def _high_low_vs_avg(df: pd.DataFrame) -> tuple[float | None, float | None]:
    """Compute range deviation vs average close (safe)."""

    try:
        if df is None:
            return None, None

        required_cols = {"Close", "High", "Low"}
        if not required_cols.issubset(df.columns):
            return None, None

        close = df["Close"].dropna()

        if len(close) == 0:
            return None, None

        avg_close = float(close.mean())

        if avg_close == 0:
            return None, None

        max_high = float(df["High"].max())
        min_low = float(df["Low"].min())

        high_pct = (max_high - avg_close) / avg_close * 100
        low_pct = (avg_close - min_low) / avg_close * 100

        return round(high_pct, 4), round(low_pct, 4)

    except Exception:
        return None, None
