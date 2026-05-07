import json

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnableParallel

from agents.base_agent import BaseAgent, load_structured_prompt
from core.constants import get_sector_catalog
from core.logging import get_logger
from tools.sector_tools import fetch_sector_payload, get_company_sector
from tools.utils.sector_tool_helper import (
    build_company_sector_input,
    format_sector_catalog,
    parse_sector_resolver_output,
)

logger = get_logger(__name__)


def _build_sector_resolver_message(data: dict) -> dict:
    content = f"""
ticker:
{data.get("ticker")}

company_sector_data_from_yfinance:
{json.dumps(data.get("company_sector_input", ""), indent=2)}

supported_sector_catalog:
{json.dumps(data.get("formatted_catalog", ""), indent=2)}
"""

    return {"resolver_input": content}


def _build_sector_report_message(data: dict) -> dict:
    content = f"""
Analyze the sector report data for ticker: {data.get("ticker", "N/A")}.

resolved_catalog_sector:
{json.dumps(data.get("resolved_sector", {}), indent=2)}

sector_api_data:
{json.dumps(data.get("sector_data", {}), indent=2)}
"""

    return {"messages": [HumanMessage(content=content)]}


class SectorAnalyst(BaseAgent):
    prompt_path = "prompts/sector_analyst_prompt.yaml"

    def __init__(self):
        super().__init__()

        sector_resolver_prompt_yaml = load_structured_prompt(
            "prompts/sector_resolver_prompt.yaml"
        )

        self.prompt_sector_resolver = ChatPromptTemplate.from_messages([
            ("system", sector_resolver_prompt_yaml),
            ("user", "{resolver_input}"),
        ])

        pre_resolver_preparer = RunnableParallel({
            "ticker": lambda x: x["ticker"],
            "company_sector_input": lambda x: build_company_sector_input(x["ticker"], x["company_sector"]),
            "formatted_catalog": lambda x: format_sector_catalog(x["sector_catalog"])
        })

        self.sector_resolver_llm_chain = (
            pre_resolver_preparer
            | RunnableLambda(_build_sector_resolver_message)
            | self.prompt_sector_resolver
            | self.llm
            | StrOutputParser()
            | RunnableLambda(parse_sector_resolver_output)
        )

        sector_fetcher = RunnableParallel({
            "ticker": RunnableLambda(lambda x: x["ticker"]),
            "company_sector": RunnableLambda(
                lambda x: get_company_sector(x["ticker"])
            ),
            "sector_catalog": RunnableLambda(
                lambda _: get_sector_catalog()
            ),
        })

        sector_resolver = RunnableParallel({
            "ticker": RunnableLambda(lambda x: x["ticker"]),
            "company_sector": RunnableLambda(lambda x: x["company_sector"]),
            "resolved_sector": self.sector_resolver_llm_chain,
        })

        prepare_sector_payload = RunnableLambda(
            lambda x: {
                "ticker": x["ticker"],
                "company_sector": x["company_sector"],
                "resolved_sector": x["resolved_sector"],
            }
        )

        self.resolve_sector_chain = (
            sector_fetcher
            | sector_resolver
            | prepare_sector_payload
        )

        self.chain = (
            self.resolve_sector_chain
            | RunnableLambda(fetch_sector_payload)
            | RunnableLambda(_build_sector_report_message)
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def run(self, ticker: str) -> str:
        logger.info(f"Running sector analyst | ticker={ticker}")
        return self.chain.invoke({
            "ticker": ticker,
        })
