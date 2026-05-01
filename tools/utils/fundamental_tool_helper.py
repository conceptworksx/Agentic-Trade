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


def _ticker_data(ticker: str) -> yf.Ticker:
    """Instantiate yf.Ticker. No network call happens here."""
    logger.info(f"Initializing ticker object for {ticker}")
    try:
        return yf.Ticker(ticker)
    except Exception as exc:
        logger.exception(f"Failed to initialize ticker: {ticker}")
        raise DataFetchError(
            source="yfinance.Ticker",
            symbol=ticker,
            original=exc,
        )

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
    """Compute YoY growth % for each year in a date-keyed dict."""
    dates = list(d.keys())
    values = list(d.values())
    result = {}
    logger.debug("Calculating YoY growth")
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
    values = [v for v in d.values() if v is not None and v > 0]
    if len(values) < 2:
        return None
    n = len(values) - 1
    return round(((values[0] / values[-1]) ** (1 / n) - 1) * 100, 2)

def _fetch_income_stmt(df: pd.DataFrame) -> dict[str, Any]:
    """Extract income statement metrics from a pre-fetched financials DataFrame."""
    logger.info("Processing income statement")
    if df is None or df.empty:
        logger.error("Income statement data is empty")
        raise DataFetchError(source="yfinance.financials", symbol="unknown")

    try:
        result = {
            "income_statement": {
                "revenue": _df_row(df, "Total Revenue"),
                "ebitda": _df_row(df, "EBITDA", "Normalized EBITDA"),
                "net_income": _df_row(df, "Net Income", "Net Income Common Stockholders"),
                "eps_diluted": _df_row(df, "Diluted EPS"),
            }
        }
        logger.info("Income statement processed successfully")
        return result
    except Exception as exc:
        logger.exception("Failed to parse income statement")
        raise DataParseError(f"Failed to parse income statement: {exc}", original=exc)

def _fetch_balance_sheet(df: pd.DataFrame, info: dict) -> dict[str, Any]:
    """Extract balance sheet metrics from a pre-fetched balance_sheet DataFrame."""
    logger.info("Processing balance sheet")
    if df is None or df.empty:
        logger.error("Balance Sheet is empty.")
        raise DataFetchError(source="yfinance.balance_sheet", symbol="unknown")

    try:
        equity = _df_row(df, "Stockholders Equity", "Common Stock Equity")
        result = {
            "balance_sheet": {
                "cash": _df_row(
                    df,
                    "Cash And Cash Equivalents",
                    "Cash Cash Equivalents And Short Term Investments",
                ),
                "total_liabilities": _df_row(
                    df,
                    "Total Liabilities Net Minority Interest",
                    "Total Liabilities",
                ),
                "total_debt": _df_row(df, "Total Debt"),
                "shareholders_equity": equity,
            }
        }
        logger.info("Balance sheet processed successfully")
        return result
    except Exception as exc:
        logger.exception("Failed to parse balance sheet")
        raise DataParseError(f"Failed to parse balance sheet: {exc}", original=exc)

def _fetch_cash_flow(df: pd.DataFrame) -> dict[str, Any]:
    """Extract cash flow metrics and derive FCF from a pre-fetched cashflow DataFrame."""
    logger.info("Processing Cash Flow")
    if df is None or df.empty:
        logger.error("Cash Flow is empty")
        raise DataFetchError(source="yfinance.cashflow", symbol="unknown")

    try:
        ocf = _df_row(df, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
        capex = _df_row(df, "Capital Expenditure", "Purchase Of PPE")

        free_cash_flow = {
            date: round(ocf[date] + capex[date], 2)
            if ocf.get(date) is not None and capex.get(date) is not None
            else None
            for date in ocf
        }

        result = {
            "cash_flow": {
                "operating_cash_flow": ocf,
                "free_cash_flow": free_cash_flow,
            }
        }
        logger.info("Cash Flow processed successfully")
        return result
    except Exception as exc:
        logger.exception("Failed to parse cash flow")
        raise DataParseError(f"Failed to parse cash flow: {exc}", original=exc)

def _fetch_fundamentals(inc: pd.DataFrame, bal: pd.DataFrame) -> dict[str, Any]:
    """Compute derived ratios from pre-fetched income + balance sheet DataFrames."""
    logger.info("Computing fundamental ratios")
    if inc is None or inc.empty:
        logger.error("Income data missing for fundamentals")
        raise DataFetchError(source="yfinance.financials", symbol="unknown")
    if bal is None or bal.empty:
        logger.error("Balance sheet data missing for fundamentals")
        raise DataFetchError(source="yfinance.balance_sheet", symbol="unknown")

    try:
        revenue = _df_row(inc, "Total Revenue")
        net_income = _df_row(inc, "Net Income", "Net Income Common Stockholders")
        int_expense = _df_row(inc, "Interest Expense", "Interest Expense Non Operating")
        ebit = _df_row(inc, "Operating Income", "EBIT")
        total_assets = _df_row(bal, "Total Assets")
        current_liab = _df_row(bal, "Current Liabilities")
        total_debt = _df_row(bal, "Total Debt")
        equity = _df_row(bal, "Stockholders Equity", "Common Stock Equity")

        capital_employed = {
            d: round(total_assets[d] - current_liab[d], 2)
            if total_assets.get(d) is not None and current_liab.get(d) is not None else None
            for d in total_assets
        }

        int_coverage = {
            d: round(ebit[d] / abs(int_expense[d]), 2)
            if ebit.get(d) is not None and int_expense.get(d) and int_expense[d] != 0
            else None
            for d in ebit
        }

        def ratio_dict(num_d, den_d):
            return {d: _safe_divide(num_d.get(d), den_d.get(d)) for d in num_d}

        def margin(num_d, den_d):
            return {
                d: round(_safe_divide(num_d.get(d), den_d.get(d)) * 100, 2)
                if _safe_divide(num_d.get(d), den_d.get(d)) is not None else None
                for d in den_d
            }

        result = {
            "fundamentals": {
                "net_margin_pct": margin(net_income, revenue),
                "roe_pct": margin(net_income, equity),
                "roce_pct": {
                    d: round(_safe_divide(ebit.get(d), capital_employed.get(d)) * 100, 2)
                    if capital_employed.get(d) and _safe_divide(ebit.get(d), capital_employed.get(d)) is not None
                    else None
                    for d in ebit
                },
                "debt_to_equity": ratio_dict(total_debt, equity),
                "interest_coverage": int_coverage,
            }
        }
        logger.info("Fundamental ratios computed successfully")
        return result
    except Exception as exc:
        logger.exception("Failed to compute fundamentals")
        raise DataParseError(f"Failed to compute ratios: {exc}", original=exc)

def _fetch_eps_trend(inc: pd.DataFrame) -> dict[str, Any]:
    """Extract EPS and compute CAGR from a pre-fetched financials DataFrame."""
    logger.info("Computing EPS trend")
    if inc is None or inc.empty:
        logger.error("Income data missing for EPS trend computation")
        return {"eps_trend": {"eps_diluted": {}, "eps_cagr_pct": None}}

    try:
        eps_diluted = _df_row(inc, "Diluted EPS")
        result = {
            "eps_trend": {
                "eps_diluted": eps_diluted,
                "eps_cagr_pct": _cagr(eps_diluted),
            }
        }
        logger.info("EPS trend computed successfully")
        return result
    except Exception as exc:
        logger.exception("Failed to parse EPS trend")
        raise DataParseError(f"Failed to parse EPS: {exc}", original=exc)

def _fetch_valuation(info: dict, major_holders: pd.DataFrame | None) -> dict[str, Any]:
    """Extract valuation ratios from pre-fetched info dict and major_holders DataFrame."""
    logger.info("Computing valuation metrics")

    def safe_get(key: str) -> float | None:
        v = info.get(key)
        if v is None:
            return None
        if isinstance(v, float) and np.isnan(v):
            return None
        return v

    try:
        promoter_pct = None
        if major_holders is not None and not major_holders.empty:
            # Added a nested try-except specifically for pandas iloc extraction
            try:
                promoter_pct = round(float(major_holders.iloc[0, 0]) * 100, 2)
            except (IndexError, ValueError):
                promoter_pct = None

        pe = safe_get("trailingPE")
        ev_ebitda = safe_get("enterpriseToEbitda")
        peg = safe_get("pegRatio")
        div_yield = safe_get("dividendYield")

        result = {
            "valuation": {
                "market_cap": safe_get("marketCap"),
                "valuation_ratios": {
                    "pe_ratio": round(pe, 2) if pe is not None else None,
                    "ev_ebitda": round(ev_ebitda, 2) if ev_ebitda is not None else None,
                    "peg_ratio": round(peg, 2) if peg is not None else None,
                },
                "dividend_yield_pct": round(div_yield * 100, 4) if div_yield is not None else None,
                "promoter_holding_pct": promoter_pct,
            }
        }
        logger.info("Valuation metrics computed successfully")
        return result

    except Exception as exc:
        logger.exception("Failed to parse valuation metrics")
        raise DataParseError(f"Failed to parse valuation metrics: {exc}", original=exc)

def _fetch_growth(inc: pd.DataFrame) -> dict[str, Any]:
    """Compute YoY and CAGR growth from a pre-fetched financials DataFrame."""
    logger.info("Computing growth metrics")

    if inc is None or inc.empty:
        logger.error("Income data missing for growth computation")
        raise DataFetchError(source="yfinance.financials", symbol="unknown")

    try:
        revenue = _df_row(inc, "Total Revenue")
        net_income = _df_row(inc, "Net Income", "Net Income Common Stockholders")
        result = {
            "growth": {
                "revenue_yoy_pct": _yoy_growth(revenue),
                "revenue_cagr_pct": _cagr(revenue),
                "net_income_cagr_pct": _cagr(net_income),
            }
        }
        logger.info("Growth metrics computed successfully")
        return result
    except Exception as exc:
        logger.exception("Failed to compute growth metrics")
        raise DataParseError(f"Failed to compute growth: {exc}", original=exc)