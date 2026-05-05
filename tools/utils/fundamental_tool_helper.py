import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Any
import logging
from core.error import DataFetchError, DataParseError
from core.logging import get_logger
logger = get_logger(__name__)
warnings.filterwarnings("ignore")


def _series_to_dict(series: pd.Series) -> dict[str, Any]:
    """Convert a pandas Series with DatetimeIndex into a date-keyed dict."""
    logger.debug("Converting pandas Series to dict")
    result = {}
    for idx, val in series.items():
        key = pd.Timestamp(idx).strftime("%Y-%m-%d")
        result[key] = None if pd.isna(val) else round(float(val), 2)
    return result


def _df_row(df: pd.DataFrame, *candidates: str) -> dict[str, Any]:
    """Return first matching row from df as date-keyed dict. Empty dict if none found."""
    for name in candidates:
        if name in df.index:
            return _series_to_dict(df.loc[name])
    logger.warning(f"No matching rows found for candidates: {candidates}")
    return {}


def _safe_divide(a: float | None, b: float | None) -> float | None:
    """Return a/b rounded to 4dp, or None on zero/None."""
    if a is None or b is None or b == 0:
        return None
    return round(a / b, 4)


def _yoy_growth(d: dict) -> dict[str, Any]:
    logger.debug("Calculating YoY growth")

    dates = sorted(d.keys(), reverse=True)  # latest → oldest
    values = [d[k] for k in dates]

    result = {}
    for i in range(len(dates) - 1):
        cur, prv = values[i], values[i + 1]
        if cur is None or prv is None or prv == 0:
            result[dates[i]] = None
        else:
            result[dates[i]] = round((cur - prv) / abs(prv) * 100, 2)

    return result


def _cagr(d: dict) -> float | None:
    """Compute CAGR across all available years. Requires at least 2 data points."""
    logger.debug("Calculating CAGR")

    items = [(k, v) for k, v in d.items() if v is not None and v > 0]
    if len(items) < 2:
        return None

    items = sorted(items, key=lambda x: x[0], reverse=True)  # latest → oldest

    start = items[-1][1]
    end = items[0][1]
    n = len(items) - 1

    return round(((end / start) ** (1 / n) - 1) * 100, 2)

def _ratio_dict(num_d, den_d):
    keys = set(num_d.keys()) | set(den_d.keys())
    return {d: _safe_divide(num_d.get(d), den_d.get(d)) for d in keys}


def _margin(num_d, den_d):
    result = {}
    for d in den_d:
        val = _safe_divide(num_d.get(d), den_d.get(d))
        result[d] = round(val * 100, 2) if val is not None else None
    return result


def _safe_get(info:dict, key: str) -> float | None:
        v = info.get(key)
        if v is None:
            return None
        if isinstance(v, float) and np.isnan(v):
            return None
        return v


