import json
import warnings
from typing import Any

from utils.fundamental_tool_helper import (
    fetch_income_stmt,
    fetch_balance_sheet,
    fetch_cash_flow,
    fetch_fundamentals,
    fetch_eps_trend,
    fetch_valuation,
    fetch_growth,
)

warnings.filterwarnings("ignore")

"""
Functions:
    get_income_stmt(symbol)   → Profitability / P&L metrics
    get_balance_sheet(symbol) → Asset, liability, equity metrics
    get_cash_flow(symbol)     → OCF, CapEx, FCF, financing flows
    get_fundamentals(symbol)  → Derived profitability, liquidity, leverage, efficiency ratios
    get_eps_trend(symbol)     → EPS history, growth, analyst estimates
    get_valuation(symbol)     → Valuation ratios, market metrics, dividends, holdings
    get_growth(symbol)        → YoY and CAGR growth for revenue, profit, EPS

"""

def get_income_stmt(ticker: str) -> dict[str, Any]:
    """
    Fetch annual income statement for a given equity ticker.

    Args:
        ticker (str): Yahoo Finance ticker (e.g. 'RELIANCE.NS', 'TCS.NS', 'AAPL').

    Returns:
        dict[str, Any]:
            {
                "ticker": str,
                "income_statement": {
                    "revenue":           {"2025-03-31": float, ...},
                    "gross_profit":      {"2025-03-31": float, ...},
                    "operating_expense": {"2025-03-31": float, ...},
                    "operating_income":  {"2025-03-31": float, ...},
                    "ebitda":            {"2025-03-31": float, ...},
                    "net_income":        {"2025-03-31": float, ...},
                    "eps_basic":         {"2025-03-31": float, ...},
                    "eps_diluted":       {"2025-03-31": float, ...},
                }
            }

    Agent Use:
        Core profitability assessment — revenue growth, margin trends,
        EPS trajectory, earnings quality.

    Raises:
        ValueError: If no data is returned for the symbol.
    """
    data = fetch_income_stmt(ticker)
    if "error" in data:
        raise ValueError(data["error"])
    return {"ticker": ticker, "income_statement": data}


def get_balance_sheet(ticker: str) -> dict[str, Any]:
    """
    Fetch annual balance sheet for a given equity ticker.

    Args:
        ticker (str): Yahoo Finance ticker.

    Returns:
        dict[str, Any]:
            {
                "ticker": str,
                "balance_sheet": {
                    "cash":                 {"2025-03-31": float, ...},
                    "total_liabilities":    {"2025-03-31": float, ...},
                    "total_debt":           {"2025-03-31": float, ...},
                    "shareholders_equity":  {"2025-03-31": float, ...},
                }
            }

    Agent Use:
        Debt load, liquidity buffers, equity growth, working capital health.
    """
    data = fetch_balance_sheet(ticker)
    if "error" in data:
        raise ValueError(data["error"])
    return {"ticker": ticker, "balance_sheet": data}


def get_cash_flow(ticker: str) -> dict[str, Any]:
    """
    Fetch annual cash flow statement for a given equity ticker.

    Args:
        ticker (str): Yahoo Finance ticker.

    Returns:
        dict[str, Any]:
            {
                "ticker": str,
                "cash_flow": {
                    "operating_cash_flow":       {"2025-03-31": float, ...},
                    "free_cash_flow":             {"2025-03-31": float, ...},
                }
            }

    Agent Use:
        FCF generation, capex intensity vs competitors, dividend sustainability,
        earnings vs cash flow reconciliation (earnings quality check).
    """
    data = fetch_cash_flow(ticker)
    if "error" in data:
        raise ValueError(data["error"])
    return {"ticker": ticker, "cash_flow": data}


def get_fundamentals(ticker: str) -> dict[str, Any]:
    """
    Compute derived fundamental ratios from income statement + balance sheet.

    Args:
        ticker (str): Yahoo Finance ticker.

    Returns:
        dict[str, Any]:
            {
                "ticker": str,
                "fundamentals": {
                    # Profitability
                    "roe_pct":              {"2025-03-31": float, ...},
                    "roce_pct":             {"2025-03-31": float, ...},
                    # Leverage
                    "debt_to_equity":       {"2025-03-31": float, ...},
                    "interest_coverage":    {"2025-03-31": float, ...},
                }
            }

    Agent Use:
        Margin expansion/compression trends, leverage risk, capital efficiency,
        ROE vs ROCE spread (signals debt-funded growth vs organic growth).
    """
    data = fetch_fundamentals(ticker)
    if "error" in data:
        raise ValueError(data["error"])
    return {"ticker": ticker, "fundamentals": data}


def get_eps_trend(ticker: str) -> dict[str, Any]:
    """
    Fetch EPS history, growth rates, and analyst forward estimates.

    Args:
        ticker (str): Yahoo Finance ticker.

    Returns:
        dict[str, Any]:
            {
                "ticker": str,
                "eps_trend": {
                    "eps_diluted":            {"2025-03-31": float, ...},
                    "eps_cagr_pct":           float,
                }
            }

    Agent Use:
        EPS trajectory, analyst beat/miss history, forward earnings growth,
        PEG ratio context, estimate revision momentum.
    """
    data = fetch_eps_trend(ticker)
    return {"ticker": ticker, "eps_trend": data}


def get_valuation(ticker: str) -> dict[str, Any]:
    """
    Fetch current valuation ratios, market metrics, dividend data, and holdings.

    Args:
        ticker (str): Yahoo Finance ticker.

    Returns:
        dict[str, Any]:
            {
                "ticker": str,
                "valuation": {
                    "market_cap":         float,
                    "valuation_ratios": {
                        "pe_ratio":       float | None,
                        "ev_ebitda":      float | None,
                        "peg_ratio":      float | None,
                    },
                    "dividend_yield_pct":  float | None,
                    "promoter_holding_pct":      float | None,
                }
            }

    Agent Use:
        Cheap vs expensive vs fair value judgment, dividend income viability,
        promoter confidence signal, institutional accumulation/distribution.
    """
    data = fetch_valuation(ticker)
    return {"ticker": ticker, "valuation": data}


def get_growth(ticker: str) -> dict[str, Any]:
    """
    Compute YoY growth rates and multi-year CAGR for revenue, profit, and EPS.

    Args:
        ticker (str): Yahoo Finance ticker.

    Returns:
        dict[str, Any]:
            {
                "ticker": str,
                "growth": {
                    "revenue_yoy_pct":     {"2024-03-31": float, ...},
                    "revenue_cagr_pct":    float,
                    "net_income_cagr_pct": float,
                }
            }

    Agent Use:
        Identify compounders vs one-time growers. CAGR cross-check with
        valuation multiples to validate PEG ratio. Profit growth vs revenue
        growth spread reveals operating leverage.
    """
    data = fetch_growth(ticker)
    if "error" in data:
        raise ValueError(data["error"])
    return {"ticker": ticker, "growth": data}



# if __name__ == "__main__":
#     SYMBOL = "RELIANCE.NS"
#     print(f"Running fundamental snapshot for {SYMBOL}\n")

#     results = {
#         "income_stmt":  get_income_stmt(SYMBOL),
#         "balance_sheet": get_balance_sheet(SYMBOL),
#         "cash_flow":    get_cash_flow(SYMBOL),
#         "fundamentals": get_fundamentals(SYMBOL),
#         "eps_trend":    get_eps_trend(SYMBOL),
#         "valuation":    get_valuation(SYMBOL),
#         "growth":       get_growth(SYMBOL),
#     }

#     output = json.dumps(results, indent=2)
#     print(output)

#     with open("fundamental_snapshot2.json", "w") as f:
#         f.write(output)
#     print("\nSaved → fundamental_snapshot2.json")