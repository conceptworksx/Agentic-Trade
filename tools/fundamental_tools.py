import json
import warnings
from typing import Any
import pandas as pd
from tools.utils.fundamental_tool_helper import (
    _df_row,
    _cagr,
    _yoy_growth,
    _safe_divide,
    _series_to_dict,
    _ratio_dict,
    _safe_get,
    _margin
)
from core.logging import get_logger
logger = get_logger(__name__)

warnings.filterwarnings("ignore")


import yfinance as yf
from typing import Any, Dict
from concurrent.futures import ThreadPoolExecutor

def ticker_data(ticker: str) -> Dict[str, Any]:
    logger.info(f"Fetching all financial data for {ticker}")

    result = {
        "status": "success",
        "ticker": ticker,
        "financials": None,
        "balance_sheet": None,
        "cash_flow": None,
        "info": {},
        "major_holders": None,
        "error": None,
    }

    try:
        t = yf.Ticker(ticker)

        def get_financials():
            return t.financials

        def get_balance_sheet():
            return t.balance_sheet

        def get_cash_flow():
            return t.cash_flow

        def get_info():
            i = t.info
            return i if isinstance(i, dict) else {}

        def get_holders():
            return t.major_holders

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                "financials": executor.submit(get_financials),
                "balance_sheet": executor.submit(get_balance_sheet),
                "cash_flow": executor.submit(get_cash_flow),
                "info": executor.submit(get_info),
                "major_holders": executor.submit(get_holders),
            }

            for key, future in futures.items():
                try:
                    result[key] = future.result()
                except Exception as e:
                    logger.warning(f"{key} fetch failed: {e}")

        return result

    except Exception as exc:
        logger.exception(f"Failed to fetch data for {ticker}")
        result["status"] = "error"
        result["error"] = str(exc)
        return result

# def ticker_data(ticker: str) -> Dict[str, Any]:
#     """
#     Fetch all raw financial datasets for a ticker.

#     Always returns a structured response (never raises),
#     so it is safe to use inside Runnable chains.
#     """

#     logger.info(f"Fetching all financial data for {ticker}")

#     result = {
#         "status": "success",
#         "ticker": ticker,
#         "financials": None,
#         "balance_sheet": None,
#         "cash_flow": None,
#         "info": {},
#         "major_holders": None,
#         "error": None,
#     }

#     try:
#         # Object creation (can fail)
#         t = yf.Ticker(ticker)

#         # Data fetch (network-bound)
#         result["financials"] = t.financials
#         result["balance_sheet"] = t.balance_sheet
#         result["cash_flow"] = t.cash_flow

#         # info can sometimes break or be non-dict
#         info = t.info
#         result["info"] = info if isinstance(info, dict) else {}

#         result["major_holders"] = t.major_holders

#         return result

#     except Exception as exc:
#         logger.exception(f"Failed to fetch data for {ticker}")

#         result["status"] = "error"
#         result["error"] = str(exc)

#         return result

def fetch_income_stmt(df: pd.DataFrame) -> dict[str, Any]:
    """Extract income statement metrics from a pre-fetched financials DataFrame."""
    logger.info("Processing income statement")

    result = {
        "status": "success",
        "income_statement": {
            "revenue": None,
            "ebitda": None,
            "net_income": None,
            "eps_diluted": None,
        },
        "error": None,
    }

    # Handle empty input (no raise)
    if df is None or df.empty:
        logger.warning("Income statement data is empty")
        result["status"] = "no_data"
        result["error"] = "Income statement data is empty"
        return result

    try:
        result["income_statement"] = {
            "revenue": _df_row(df, "Total Revenue"),
            "ebitda": _df_row(df, "EBITDA", "Normalized EBITDA"),
            "net_income": _df_row(df, "Net Income", "Net Income Common Stockholders"),
            "eps_diluted": _df_row(df, "Diluted EPS"),
        }

        logger.info("Income statement processed successfully")
        return result

    except Exception as exc:
        logger.exception("Failed to parse income statement")

        result["status"] = "error"
        result["error"] = str(exc)
        return result 


def fetch_balance_sheet(df: pd.DataFrame, info: dict) -> dict[str, Any]:
    """Extract balance sheet metrics from a pre-fetched balance_sheet DataFrame."""
    logger.info("Processing balance sheet")

    result = {
        "status": "success",
        "balance_sheet": {
            "cash": None,
            "total_liabilities": None,
            "total_debt": None,
            "shareholders_equity": None,
        },
        "error": None,
    }

    # Handle empty input (no raise)
    if df is None or df.empty:
        logger.warning("Balance Sheet is empty.")
        result["status"] = "no_data"
        result["error"] = "Balance sheet data is empty"
        return result

    try:
        equity = _df_row(df, "Stockholders Equity", "Common Stock Equity")

        result["balance_sheet"] = {
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

        logger.info("Balance sheet processed successfully")
        return result

    except Exception as exc:
        logger.exception("Failed to parse balance sheet")

        result["status"] = "error"
        result["error"] = str(exc)
        return result


def fetch_cash_flow(df: pd.DataFrame) -> dict[str, Any]:
    """Extract cash flow metrics and derive FCF from a pre-fetched cashflow DataFrame."""
    logger.info("Processing Cash Flow")

    result = {
        "status": "success",
        "cash_flow": {
            "operating_cash_flow": None,
            "free_cash_flow": None,
        },
        "error": None,
    }

    # Handle empty input (no raise)
    if df is None or df.empty:
        logger.warning("Cash Flow is empty")
        result["status"] = "no_data"
        result["error"] = "Cash flow data is empty"
        return result

    try:
        ocf = _df_row(
            df,
            "Operating Cash Flow",
            "Cash Flow From Continuing Operating Activities",
        )
        capex = _df_row(
            df,
            "Capital Expenditure",
            "Purchase Of PPE",
        )

        free_cash_flow = {
            date: round(ocf[date] + capex[date], 2)
            if ocf.get(date) is not None and capex.get(date) is not None
            else None
            for date in ocf
        }

        result["cash_flow"] = {
            "operating_cash_flow": ocf,
            "free_cash_flow": free_cash_flow,
        }

        logger.info("Cash Flow processed successfully")
        return result

    except Exception as exc:
        logger.exception("Failed to parse cash flow")

        result["status"] = "error"
        result["error"] = str(exc)
        return result

        
def fetch_fundamentals(inc: pd.DataFrame, bal: pd.DataFrame) -> dict[str, Any]:
    """Compute derived ratios from pre-fetched income + balance sheet DataFrames."""
    logger.info("Computing fundamental ratios")

    result = {
        "status": "success",
        "fundamentals": {
            "net_margin_pct": None,
            "roe_pct": None,
            "roce_pct": None,
            "debt_to_equity": None,
            "interest_coverage": None,
        },
        "error": None,
    }

    # Handle missing inputs (no raise)
    if inc is None or inc.empty:
        logger.warning("Income data missing for fundamentals")
        result["status"] = "no_data"
        result["error"] = "Income statement data missing"
        return result

    if bal is None or bal.empty:
        logger.warning("Balance sheet data missing for fundamentals")
        result["status"] = "no_data"
        result["error"] = "Balance sheet data missing"
        return result

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

        result["fundamentals"] = {
            "net_margin_pct": _margin(net_income, revenue),
            "roe_pct": _margin(net_income, equity),
            "roce_pct": {
                d: round(_safe_divide(ebit.get(d), capital_employed.get(d)) * 100, 2)
                if capital_employed.get(d) and _safe_divide(ebit.get(d), capital_employed.get(d)) is not None
                else None
                for d in ebit
            },
            "debt_to_equity": _ratio_dict(total_debt, equity),
            "interest_coverage": int_coverage,
        }

        logger.info("Fundamental ratios computed successfully")
        return result

    except Exception as exc:
        logger.exception("Failed to compute fundamentals")

        result["status"] = "error"
        result["error"] = str(exc)
        return result

def fetch_eps_trend(inc: pd.DataFrame) -> dict[str, Any]:
    """Extract EPS and compute CAGR from a pre-fetched financials DataFrame."""
    logger.info("Computing EPS trend")

    result = {
        "status": "success",
        "eps_trend": {
            "eps_diluted": {},
            "eps_cagr_pct": None,
        },
        "error": None,
    }

    # Handle missing input
    if inc is None or inc.empty:
        logger.warning("Income data missing for EPS trend computation")
        result["status"] = "no_data"
        result["error"] = "Income statement data missing"
        return result

    try:
        eps_diluted = _df_row(inc, "Diluted EPS")

        result["eps_trend"] = {
            "eps_diluted": eps_diluted,
            "eps_cagr_pct": _cagr(eps_diluted),
        }

        logger.info("EPS trend computed successfully")
        return result

    except Exception as exc:
        logger.exception("Failed to parse EPS trend")

        result["status"] = "error"
        result["error"] = str(exc)
        return result

def fetch_valuation(info: dict, major_holders: pd.DataFrame | None) -> dict[str, Any]:
    """Extract valuation ratios from pre-fetched info dict and major_holders DataFrame."""
    logger.info("Computing valuation metrics")

    result = {
        "status": "success",
        "valuation": {
            "market_cap": None,
            "valuation_ratios": {
                "pe_ratio": None,
                "ev_ebitda": None,
                "peg_ratio": None,
            },
            "dividend_yield_pct": None,
            "promoter_holding_pct": None,
        },
        "error": None,
    }

    try:
        promoter_pct = None
        if major_holders is not None and not major_holders.empty:
            try:
                promoter_pct = round(float(major_holders.iloc[0, 0]) * 100, 2)
            except (IndexError, ValueError):
                promoter_pct = None

        pe = _safe_get(info, "trailingPE")
        ev_ebitda = _safe_get(info, "enterpriseToEbitda")
        peg = _safe_get(info, "pegRatio")
        div_yield = _safe_get(info, "dividendYield")

        result["valuation"] = {
            "market_cap": _safe_get(info, "marketCap"),
            "valuation_ratios": {
                "pe_ratio": round(pe, 2) if pe is not None else None,
                "ev_ebitda": round(ev_ebitda, 2) if ev_ebitda is not None else None,
                "peg_ratio": round(peg, 2) if peg is not None else None,
            },
            "dividend_yield_pct": round(div_yield * 100, 4) if div_yield is not None else None,
            "promoter_holding_pct": promoter_pct,
        }

        logger.info("Valuation metrics computed successfully")
        return result

    except Exception as exc:
        logger.exception("Failed to parse valuation metrics")
        result["status"] = "error"
        result["error"] = str(exc)
        return result

def fetch_growth(inc: pd.DataFrame) -> dict[str, Any]:
    """Compute YoY and CAGR growth from a pre-fetched financials DataFrame."""
    logger.info("Computing growth metrics")

    result = {
        "status": "success",
        "growth": {
            "revenue_yoy_pct": None,
            "revenue_cagr_pct": None,
            "net_income_cagr_pct": None,
        },
        "error": None,
    }

    # Handle missing input
    if inc is None or inc.empty:
        logger.warning("Income data missing for growth computation")
        result["status"] = "no_data"
        result["error"] = "Income statement data missing"
        return result

    try:
        revenue = _df_row(inc, "Total Revenue")
        net_income = _df_row(inc, "Net Income", "Net Income Common Stockholders")

        result["growth"] = {
            "revenue_yoy_pct": _yoy_growth(revenue),
            "revenue_cagr_pct": _cagr(revenue),
            "net_income_cagr_pct": _cagr(net_income),
        }

        logger.info("Growth metrics computed successfully")
        return result

    except Exception as exc:
        logger.exception("Failed to compute growth metrics")
        result["status"] = "error"
        result["error"] = str(exc)
        return result
    

if __name__ == "__main__":
    import json
    import pprint

    TEST_TICKER = "RELIANCE.NS"

    print(f"\n🔍 Testing fundamental data pipeline for: {TEST_TICKER}\n")

    data = ticker_data(TEST_TICKER)

    if data["status"] != "success":
        print("❌ Failed to fetch data:")
        pprint.pprint(data)
    else:
        print("✅ Data fetched successfully\n")

        # ✅ ONLY processed outputs (NO raw DataFrames)
        output = {
            "income_stmt": fetch_income_stmt(data["financials"]),
            "balance_sheet": fetch_balance_sheet(data["balance_sheet"], data["info"]),
            "cash_flow": fetch_cash_flow(data["cash_flow"]),
            "fundamentals": fetch_fundamentals(data["financials"], data["balance_sheet"]),
            "eps_trend": fetch_eps_trend(data["financials"]),
            "valuation": fetch_valuation(data["info"], data["major_holders"]),
            "growth": fetch_growth(data["financials"]),
        }

        print("\n📊 Processed Output:")
        pprint.pprint(output)

        # ✅ Save JSON safely (no need for special serializer now)
        file_name = f"fundamental_output_{TEST_TICKER.replace('.', '_')}.json"

        with open(file_name, "w") as f:
            json.dump(output, f, indent=2)

        print(f"\n💾 Output saved to {file_name}")