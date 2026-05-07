import json

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnableBranch

from agents.base_agent import BaseAgent, load_structured_prompt
from core.constants import get_sector_catalog
from core.logging import get_logger
from tools.sector_tools import fetch_sector_payload, get_company_sector
from tools.utils.sector_tool_helper import (
    parse_sector_resolver_output,
)

logger = get_logger(__name__)


def _build_sector_resolver_message(data: dict) -> dict:
    """
    Format the input for the Sector Resolver stage.
    Uses Markdown headers to help the LLM distinguish between raw ticker data, 
    yfinance metadata, and the target sector catalog.
    """
    content = f"""
Ticker
{data.get("ticker")}

Company Sector Data (Source: yfinance)
{json.dumps(data.get("company_sector", ""), indent=2)}

Supported Sector Catalog
{json.dumps(data.get("sector_catalog", ""), indent=2)}
"""

    return {"resolver_input": content}


def _build_sector_report_message(data: dict) -> dict:
    """
    Format the final input for the Sector Analysis report.
    Combines the resolved sector identification with the fetched PDF/API data.
    """
    content = f"""
Analysis Request
Analyze the sector report data for ticker: {data.get("ticker", "N/A")}.

Resolved Catalog Sector
{json.dumps(data.get("resolved_sector", {}), indent=2)}

Sector API Data (PDF Content)
{json.dumps(data.get("sector_data", {}), indent=2)}
"""

    return {"messages": [HumanMessage(content=content)]}


class SectorAnalyst(BaseAgent):
    """
    Agent responsible for identifying a company's sector and analyzing 
    the corresponding industry report.
    """
    prompt_path = "prompts/sector_analyst_prompt.yaml"

    def __init__(self):
        super().__init__()

        # Load the specialized prompt for sector resolution
        sector_resolver_prompt_yaml = load_structured_prompt(
            "prompts/sector_resolver_prompt.yaml"
        )

        self.prompt_sector_resolver = ChatPromptTemplate.from_messages([
            ("system", sector_resolver_prompt_yaml),
            ("user", "{resolver_input}"),
        ])

        # Step 1: Define the LLM-based sector resolver chain
        self.sector_resolver_llm_chain = (
            RunnableLambda(lambda x: _build_sector_resolver_message(x))
            | self.prompt_sector_resolver
            | self.llm
            | StrOutputParser()
            | RunnableLambda(parse_sector_resolver_output)
        )

        # Step 2: Define the Parallel Resolver stage
        # This keeps the original data (ticker, sector) while adding the 'resolved_sector' result
        sector_resolver = RunnableParallel({
            "ticker": RunnableLambda(lambda x: x["ticker"]),
            "company_sector": RunnableLambda(lambda x: x["company_sector"]),
            "resolved_sector": self.sector_resolver_llm_chain,
        })

        # Step 3: Define the Data Fetching stage
        # Loads rough sector info from yfinance and the supported catalog constants
        sector_fetcher = RunnableParallel({
            "ticker": RunnableLambda(lambda x: x["ticker"]),
            "company_sector": RunnableLambda(lambda x: get_company_sector(x["ticker"])),
            "sector_catalog": RunnableLambda(lambda _: get_sector_catalog()),
        })

        # Step 4: Define the Final Report Generation stage
        # Fetches the actual PDF payload and runs the final sector analysis prompt
        report_generator = (
            RunnableLambda(fetch_sector_payload)
            | RunnableLambda(_build_sector_report_message)
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

        # Main Pipeline: Fetch -> Resolve -> Analyze
        # If yfinance metadata fetch fails, we short-circuit the chain and return an error.
        
        self.chain = sector_fetcher | RunnableBranch(
            (
                lambda x: x["company_sector"]["status"] == "failed",
                RunnableLambda(lambda x: f"Sector analysis aborted: Ticker '{x['ticker']}' not found or metadata unavailable. Error: {x['company_sector'].get('error', 'Unknown error')}")
            ),
            sector_resolver | report_generator
        )

    def run(self, ticker: str) -> str:
        """Execute the full sector analysis pipeline for a given ticker."""
        logger.info(f"Running sector analyst pipeline | ticker={ticker}")
        return self.chain.invoke({
            "ticker": ticker,
        })
