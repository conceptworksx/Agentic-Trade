import warnings
import numpy as np
import pandas as pd
import yfinance as yf
from typing import Any

warnings.filterwarnings("ignore")


def _ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol)


def _series_to_dict(series: pd.Series) -> dict[str, Any]:
    """
    Convert a pandas Series with DatetimeIndex into a date-keyed dict.

    Output format:
        {"2025-03-31": 1234567.0, "2024-03-31": 9876543.0, ...}

    None/NaN values are stored as null (None) for JSON compatibility.
    """
    result = {}
    for idx, val in series.items():
        key = pd.Timestamp(idx).strftime("%Y-%m-%d")
        result[key] = None if pd.isna(val) else round(float(val), 2)
    return result


def _df_row(df: pd.DataFrame, *candidates: str) -> dict[str, Any]:
    """
    Try each candidate row label in order; return first match as a date-keyed dict.
    Returns empty dict {} if none found.
    """
    for name in candidates:
        if name in df.index:
            return _series_to_dict(df.loc[name])
    return {}


def _safe_divide(a: float | None, b: float | None) -> float | None:
    """Return a/b rounded to 4dp, or None on zero/None."""
    if a is None or b is None or b == 0:
        return None
    return round(a / b, 4)


def _yoy_growth(d: dict) -> dict[str, Any]:
    """
    Compute year-over-year growth % for each year in a date-keyed dict.
    Returns {"2025-03-31": 12.34, "2024-03-31": -3.21, ...}
    """
    dates  = list(d.keys())
    values = list(d.values())
    result = {}
    for i in range(len(dates) - 1):
        cur = values[i]
        prv = values[i + 1]
        if cur is None or prv is None or prv == 0:
            result[dates[i]] = None
        else:
            result[dates[i]] = round((cur - prv) / abs(prv) * 100, 2)
    return result


def _cagr(d: dict) -> float | None:
    """
    Compute CAGR across all available years in a date-keyed dict.
    Requires at least 2 data points.
    """
    values = [v for v in d.values() if v is not None and v > 0]
    if len(values) < 2:
        return None
    n    = len(values) - 1
    cagr = (values[0] / values[-1]) ** (1 / n) - 1
    return round(cagr * 100, 2)


def fetch_income_stmt(symbol: str) -> dict[str, Any]:
    """
    Fetch annual income statement and extract core profitability metrics.

    Covers:
        revenue, cogs, gross_profit, operating_expense, operating_income (EBIT),
        ebitda, net_income, eps_basic, eps_diluted, interest_expense,
        tax_provision, pretax_income

    Each metric is a date-keyed dict:
        {"2025-03-31": 1234567.0, "2024-03-31": ...}

    Agent Use:
        Profitability trend, margin compression/expansion, earnings quality.
    """
    t  = _ticker(symbol)
    df = t.financials         

    if df is None or df.empty:
        return {"error": f"No income statement data for {symbol}"}

    return {
        "revenue":            _df_row(df, "Total Revenue"),
        "gross_profit":       _df_row(df, "Gross Profit"),
        "operating_expense":  _df_row(df, "Total Expenses", "Operating Expense"),
        "operating_income":   _df_row(df, "Operating Income", "EBIT"),
        "ebitda":             _df_row(df, "EBITDA", "Normalized EBITDA"),
        "net_income":         _df_row(df, "Net Income", "Net Income Common Stockholders"),
        "eps_basic":          _df_row(df, "Basic EPS"),
        "eps_diluted":        _df_row(df, "Diluted EPS"),
    }


def fetch_balance_sheet(symbol: str) -> dict[str, Any]:
    """
    Fetch annual balance sheet and extract assets, liabilities, equity metrics.

    Covers:
        total_assets, current_assets, cash, inventory, accounts_receivable,
        total_liabilities, current_liabilities, long_term_debt, total_debt,
        shareholders_equity, retained_earnings, working_capital,
        book_value_per_share (derived)

    Agent Use:
        Balance sheet strength, debt health, liquidity, net worth trajectory.
    """
    t  = _ticker(symbol)
    df = t.balance_sheet

    if df is None or df.empty:
        return {"error": f"No balance sheet data for {symbol}"}

    total_assets     = _df_row(df, "Total Assets")
    current_assets   = _df_row(df, "Current Assets")
    current_liab     = _df_row(df, "Current Liabilities")
    equity           = _df_row(df, "Stockholders Equity", "Common Stock Equity")

    # Working Capital = Current Assets - Current Liabilities (derived per date)
    working_capital = {}
    for date in total_assets:
        ca = (current_assets or {}).get(date)
        cl = (current_liab or {}).get(date)
        working_capital[date] = round(ca - cl, 2) if (ca and cl) else None

    # Book Value Per Share (requires shares outstanding from info)
    shares_info  = t.info.get("sharesOutstanding")
    bvps         = {}
    for date, eq in (equity or {}).items():
        if eq and shares_info and shares_info > 0:
            bvps[date] = round(eq / shares_info, 2)
        else:
            bvps[date] = None

    return {
        "cash":                _df_row(df, "Cash And Cash Equivalents",
                                          "Cash Cash Equivalents And Short Term Investments"),
        "total_liabilities":   _df_row(df, "Total Liabilities Net Minority Interest",
                                          "Total Liabilities"),
        "total_debt":          _df_row(df, "Total Debt"),
        "shareholders_equity": equity,

    }


def fetch_cash_flow(symbol: str) -> dict[str, Any]:
    """
    Fetch annual cash flow statement and compute Free Cash Flow.

    Covers:
        operating_cash_flow (OCF), capital_expenditure (CapEx),
        free_cash_flow (FCF = OCF - CapEx), investing_cash_flow,
        financing_cash_flow, dividends_paid, net_change_in_cash,
        depreciation_amortization

    Agent Use:
        FCF quality check, capex intensity, dividend sustainability,
        cash generation vs reported earnings verification.
    """
    t  = _ticker(symbol)
    df = t.cashflow

    if df is None or df.empty:
        return {"error": f"No cash flow data for {symbol}"}

    ocf   = _df_row(df, "Operating Cash Flow", "Cash Flow From Continuing Operating Activities")
    capex = _df_row(df, "Capital Expenditure", "Purchase Of PPE")

    # FCF = OCF - |CapEx|  (CapEx is negative in yfinance)
    free_cash_flow = {}
    for date in ocf:
        o = ocf.get(date)
        c = capex.get(date)
        if o is not None and c is not None:
            free_cash_flow[date] = round(o + c, 2)   # capex already negative
        else:
            free_cash_flow[date] = None

    return {
        "operating_cash_flow":      ocf,
        "free_cash_flow":           free_cash_flow,
    }


def fetch_fundamentals(symbol: str) -> dict[str, Any]:
    """
    Compute derived profitability, liquidity, leverage, and efficiency ratios
    from income statement + balance sheet data.

    Covers:
        Profitability : gross_margin, operating_margin, net_margin, roe, roce
        Liquidity     : current_ratio, quick_ratio
        Leverage      : debt_to_equity, interest_coverage
        Efficiency    : asset_turnover, inventory_turnover, receivables_turnover

    Each ratio is a date-keyed dict for trend analysis.

    Agent Use:
        Multi-year ratio trends reveal quality of business improvement or decline.
    """
    t      = _ticker(symbol)
    inc    = t.financials
    bal    = t.balance_sheet

    if inc is None or inc.empty or bal is None or bal.empty:
        return {"error": f"Insufficient data for {symbol}"}

    def row_i(df, *names): return _df_row(df, *names)

    # ── Raw series ───────────────────────────────────────────
    revenue      = row_i(inc, "Total Revenue")
    net_income   = row_i(inc, "Net Income", "Net Income Common Stockholders")
    int_expense  = row_i(inc, "Interest Expense", "Interest Expense Non Operating")
    ebit         = row_i(inc, "Operating Income", "EBIT")
    total_assets  = row_i(bal, "Total Assets")
    current_assets= row_i(bal, "Current Assets")
    inventory     = row_i(bal, "Inventory")
    current_liab  = row_i(bal, "Current Liabilities")
    total_debt    = row_i(bal, "Total Debt")
    equity        = row_i(bal, "Stockholders Equity", "Common Stock Equity")


    # ── Compute per-date ratios ───────────────────────────────
    def ratio_dict(num_d, den_d):
        result = {}
        for date in num_d:
            result[date] = _safe_divide(num_d.get(date), den_d.get(date))
        return result

    # ROCE = EBIT / (Total Assets - Current Liabilities)
    capital_employed = {}
    for date in total_assets:
        ta = total_assets.get(date)
        cl = current_liab.get(date)
        capital_employed[date] = round(ta - cl, 2) if (ta and cl) else None

    # Quick Ratio = (Current Assets - Inventory) / Current Liabilities
    quick_assets = {}
    for date in current_assets:
        ca  = current_assets.get(date)
        inv = inventory.get(date) or 0
        quick_assets[date] = round(ca - inv, 2) if ca else None

    # Interest Coverage = EBIT / Interest Expense
    int_coverage = {}
    for date in ebit:
        e = ebit.get(date)
        i = int_expense.get(date)
        if e and i and i != 0:
            int_coverage[date] = round(e / abs(i), 2)
        else:
            int_coverage[date] = None

    return {
        
        "net_margin_pct":        {d: round(_safe_divide(net_income.get(d), revenue.get(d)) * 100, 2)
                                   if _safe_divide(net_income.get(d), revenue.get(d)) else None
                                   for d in revenue},
        "roe_pct":               {d: round(_safe_divide(net_income.get(d), equity.get(d)) * 100, 2)
                                   if _safe_divide(net_income.get(d), equity.get(d)) else None
                                   for d in net_income},
        "roce_pct":              {d: round(_safe_divide(ebit.get(d), capital_employed.get(d)) * 100, 2)
                                   if capital_employed.get(d) and _safe_divide(ebit.get(d), capital_employed.get(d)) else None
                                   for d in ebit},
        # Leverage
        "debt_to_equity":        ratio_dict(total_debt, equity),
        "interest_coverage":     int_coverage,

    }


def fetch_eps_trend(symbol: str) -> dict[str, Any]:
    """
    Fetch EPS trend data — analyst estimates vs actuals — from yfinance.

    Covers:
        eps_actual     : reported EPS per period
        eps_estimate   : analyst consensus estimate
        eps_surprise   : actual - estimate
        eps_surprise_pct : percentage surprise
        revenue_estimate : forward revenue estimates
        growth_estimate  : forward growth estimates (from earnings_trend)

    Agent Use:
        Earnings beats/misses, estimate revisions, forward guidance signals.
    """
    t = _ticker(symbol)

    # ── Historical EPS from income statement ─────────────────
    inc     = t.financials
    eps_diluted = _df_row(inc, "Diluted EPS") if inc is not None and not inc.empty else {}

    # ── Analyst estimates ────────────────────────────────────
    try:
        trend = t.earnings_trend          # DataFrame with estimate data
        trend_data = {}
        if trend is not None and not trend.empty:
            for col in trend.columns:
                row = trend[col].to_dict()
                trend_data[str(col)] = {k: (None if pd.isna(v) else v)
                                        for k, v in row.items()}
    except Exception:
        trend_data = {}

    # ── EPS estimates (current year / next year) ─────────────
    try:
        estimates = t.earnings_estimate
        est_data  = {}
        if estimates is not None and not estimates.empty:
            for col in estimates.columns:
                est_data[str(col)] = estimates[col].to_dict()
    except Exception:
        est_data = {}

    # ── YoY EPS growth ───────────────────────────────────────
    eps_cagr   = _cagr(eps_diluted)

    return {
        "eps_diluted":        eps_diluted,
        "eps_cagr_pct":       eps_cagr,

    }


def fetch_valuation(symbol: str) -> dict[str, Any]:
    """
    Fetch and compute valuation ratios from market data + fundamentals.

    Covers:
        Market : market_cap, enterprise_value
        Ratios : pe_ratio, pb_ratio, ps_ratio, ev_ebitda, peg_ratio,
                 price_to_fcf, ev_to_revenue
        Dividend : dividend_yield, payout_ratio, dividend_per_share
        Holding : promoter_holding, institutional_holding (where available)

    Note:
        Most valuation ratios use current market price (point-in-time snapshot).
        Historical valuation (TTM) derived where possible.

    Agent Use:
        Overvalued/undervalued assessment, dividend income, ownership quality.
    """
    t    = _ticker(symbol)
    info = t.info

    def safe_get(key: str) -> float | None:
        v = info.get(key)
        return None if v is None or (isinstance(v, float) and np.isnan(v)) else v

    # ── Market metrics ────────────────────────────────────────
    market_cap       = safe_get("marketCap")

    # ── Ratios directly from yfinance info ────────────────────
    pe_ratio   = safe_get("trailingPE")
    ev_ebitda  = safe_get("enterpriseToEbitda")
    peg_ratio  = safe_get("pegRatio")

    # ── Dividend ──────────────────────────────────────────────
    div_yield  = safe_get("dividendYield")

    try:
        major_holders = t.major_holders
        promoter_pct  = None
        if major_holders is not None and not major_holders.empty:
            # Row 0 = insiders; Row 1 = institutions (varies by yfinance version)
            promoter_pct = round(float(major_holders.iloc[0, 0]) * 100, 2)
    except Exception:
        promoter_pct = None

    return {
        "market_cap":       market_cap,
        "valuation_ratios": {
            "pe_ratio":         round(pe_ratio, 2)  if pe_ratio  else None,
 
            "ev_ebitda":        round(ev_ebitda, 2) if ev_ebitda else None,
            "peg_ratio":        round(peg_ratio, 2) if peg_ratio  else None,

        },
        "dividend_yield_pct":  round(div_yield * 100, 4) if div_yield else None,
        "promoter_holding_pct":      promoter_pct,
    }



def fetch_growth(symbol: str) -> dict[str, Any]:
    """
    Compute YoY growth rates and CAGR for revenue, net income, and EPS.

    Returns:
        revenue_yoy_pct      : dict[date, float]
        net_income_yoy_pct   : dict[date, float]
        eps_yoy_pct          : dict[date, float]
        revenue_cagr_pct     : float
        net_income_cagr_pct  : float
        eps_cagr_pct         : float

    Agent Use:
        Sustained double-digit growth = high-quality compounder signal.
        Declining growth = fundamental deterioration warning.
    """
    t   = _ticker(symbol)
    inc = t.financials

    if inc is None or inc.empty:
        return {"error": f"No income data for {symbol}"}

    revenue    = _df_row(inc, "Total Revenue")
    net_income = _df_row(inc, "Net Income", "Net Income Common Stockholders")

    return {
        "revenue_yoy_pct":     _yoy_growth(revenue),
        "revenue_cagr_pct":    _cagr(revenue),
        "net_income_cagr_pct": _cagr(net_income),
        
    }