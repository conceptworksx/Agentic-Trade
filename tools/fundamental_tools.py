import json
import warnings
from typing import Any
import pandas as pd
from tools.utils.fundamental_tool_helper import (
    _fetch_income_stmt,
    _fetch_balance_sheet,
    _fetch_cash_flow,
    _fetch_fundamentals,
    _fetch_eps_trend,
    _fetch_valuation,
    _fetch_growth,
    _ticker_data,
)
from core.error import (
    handle_tool_errors,
    DataFetchError,
    DataParseError,
    ToolExecutionError,
    AgentError,
)
from core.logging import get_logger
logger = get_logger(__name__)

warnings.filterwarnings("ignore")


@handle_tool_errors("get_fundamental_snapshot")
def get_fundamental_snapshot(ticker: str) -> dict[str, Any]:
    """
    Generate a complete fundamental analysis dataset for a single equity ticker.

    This is the PRIMARY and ONLY tool required for fundamental analysis.
    It aggregates all financial data into one structured response.

    Process:
        1. Fetch income statement (profitability metrics)
        2. Fetch balance sheet (financial position)
        3. Fetch cash flow statement (cash generation)
        4. Compute key financial ratios (ROE, ROCE, leverage)
        5. Fetch EPS trends and growth rates
        6. Fetch valuation metrics and ownership data
        7. Compute revenue and profit growth metrics
        8. Aggregate everything into a single structured dictionary

    Args:
        ticker (str): Yahoo Finance ticker
                      (e.g. 'RELIANCE.NS', 'TCS.NS', 'AAPL').

    Returns:
        dict[str, Any]:
            {
                "ticker": str,

                "income_stmt": {
                    "income_statement": {
                        "revenue": {...},
                        "ebitda": {...},
                        "net_income": {...},
                        ...
                    }
                },

                "balance_sheet": {
                    "balance_sheet": {
                        "cash": {...},
                        "total_debt": {...},
                        "total_liabilities": {...},
                        "shareholders_equity": {...}
                    }
                },

                "cash_flow": {
                    "cash_flow": {
                        "operating_cash_flow": {...},
                        "free_cash_flow": {...}
                    }
                },

                "fundamentals": {
                    "fundamentals": {
                        "net_margin_pct": {...},
                        "roe_pct": {...},
                        "roce_pct": {...},
                        "debt_to_equity": {...},
                        "interest_coverage": {...}
                    }
                },

                "eps_trend": {
                    "eps_trend": {
                        "eps_diluted": {...},
                        "eps_cagr_pct": float
                    }
                },

                "valuation": {
                    "valuation": {
                        "valuation_ratios": {
                            "pe_ratio": float,
                            "ev_ebitda": float,
                            "peg_ratio": float
                        },
                        "market_cap": float,
                        "dividend_yield_pct": float,
                        "promoter_holding_pct": float
                    }
                },

                "growth": {
                    "growth": {
                        "revenue_yoy_pct": {...},
                        "revenue_cagr_pct": float,
                        "net_income_cagr_pct": float
                    }
                }
            }

    Agent Use:
        - MUST be called before performing any fundamental analysis
        - Provides ALL required financial data in a single response
        - Do NOT call individual financial tools separately
        - Use this output as the ONLY data source for analysis
        - All values are JSON-serializable (float, int, bool, str, None)

    Execution Rules for Agent:
        1. First call get_fundamental_snapshot with the given ticker
        2. Wait for the tool response
        3. Perform full analysis using the returned data
        4. Do NOT call any other tool
        5. Return final output as plain text (no tool calls)

    Raises:
        DataFetchError: If yfinance returns empty/None data for the ticker.
        DataParseError: If fetched data is malformed or missing expected fields.
        ToolExecutionError: Raised by @handle_tool_errors for any unhandled exception.
    """
    # ticker_data() raises DataFetchError on instantiation failure
    t = _ticker_data(ticker)

    # Wrap yfinance property access in a try-except. 
    # Accessing these properties triggers the actual network requests.
    try:
        logger.info(f"Fetching financial datasets for {ticker} from yfinance...")
        financials     = t.financials
        balance_sheet  = t.balance_sheet
        cash_flow      = t.cash_flow
        info           = t.info if isinstance(t.info, dict) else {}
        major_holders  = t.major_holders
    except Exception as exc:
        logger.exception(f"Network error while fetching data for {ticker}")
        raise DataFetchError(source="yfinance", symbol=ticker, original=exc)

    return {
        "ticker":        ticker,
        "income_stmt":   _fetch_income_stmt(financials),
        "balance_sheet": _fetch_balance_sheet(balance_sheet, info),
        "cash_flow":     _fetch_cash_flow(cash_flow),
        "fundamentals":  _fetch_fundamentals(financials, balance_sheet),
        "eps_trend":     _fetch_eps_trend(financials),
        "valuation":     _fetch_valuation(info, major_holders),
        "growth":        _fetch_growth(financials),
    }

if __name__ == "__main__":
    from core.logging import bootstrap_standalone
    bootstrap_standalone(__file__)
    
    TICKER = "RELIANCE.NS"
    logger.info(f"Running fundamental snapshot for {TICKER}\n")

    results = get_fundamental_snapshot(ticker=TICKER)
    output = json.dumps(results, indent=2)
    print(output)

    with open("fundamental_snapshot.json", "w") as f:
        f.write(output)
    logger.info("\nSaved → fundamental_snapshot.json")