from graph.state import AgentState
from agents.analysis.market_analyst import MarketAnalyst
from agents.analysis.news_analyst import NewsAnalyst
from agents.analysis.sector_analyst import SectorAnalyst
from agents.analysis.technical_analyst import TechnicalAnalyst
from agents.analysis.fundamental_analyst import FundamentalAnalyst
from core.error import handle_node_errors, validate_state
from core.logging import get_logger
import time

logger = get_logger(__name__)


market_analyst = MarketAnalyst()
fundamental_analyst = FundamentalAnalyst()
technical_analyst = TechnicalAnalyst()
news_analyst = NewsAnalyst()
sector_analyst = SectorAnalyst()


@handle_node_errors("market_analyst")
def run_market_analyst(state: AgentState) -> dict:
    result = market_analyst.run()
    return {"market_analyst_report": result}


@handle_node_errors("fundamental_analyst")
def run_fundamental_analyst(state: AgentState) -> dict:
    time.sleep(
        1.5
    )  # intentional delay to reduce likelihood of yfinance.info 401 errors
    result = fundamental_analyst.run(state)
    return {"fundamental_analyst_report": result}


@handle_node_errors("technical_analyst")
def run_technical_analyst(state: AgentState) -> dict:
    result = technical_analyst.run(state)
    return {"technical_analyst_report": result}


@handle_node_errors("news_analyst")
def run_news_analyst(state: AgentState) -> dict:
    result = news_analyst.run(state)
    return {"news_analyst_report": result}


@handle_node_errors("sector_analyst")
def run_sector_analyst(state: AgentState) -> dict:
    result = sector_analyst.run(state)
    return {"sector_analyst_report": result}


@handle_node_errors("aggregator")
def run_aggregator(state: AgentState) -> dict:

    validate_state(
        state,
        "market_analyst_report",
        "fundamental_analyst_report",
        "technical_analyst_report",
        "news_analyst_report",
        "sector_analyst_report",
    )

    final_report = {
        "input": {
            "ticker": state.get("ticker_of_company"),
        },
        "analysis": {
            "market": state.get("market_analyst_report"),
            "fundamental": state.get("fundamental_analyst_report"),
            "technical": state.get("technical_analyst_report"),
            "news": state.get("news_analyst_report"),
            "sector": state.get("sector_analyst_report"),
        },
    }

    return {"final_report": final_report}
