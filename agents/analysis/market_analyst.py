import json

from langchain_core.messages import HumanMessage
from langchain_core.runnables import (
    RunnableLambda,
    RunnableBranch,
)
from langchain_core.output_parsers import StrOutputParser

from agents.base_agent import BaseAgent

from tools.market_tools import process_market_data


def _build_messages(data: dict) -> dict:

    content = f"""
Analyze the Indian and Global market metrics:

S&P 500 Index:
{json.dumps(data.get('GSPC', {}), indent=2)}

NASDAQ Composite Index:
{json.dumps(data.get('IXIC', {}), indent=2)}

Volatility Index:
{json.dumps(data.get('VIX', {}), indent=2)}

NIFTY 50 Index:
{json.dumps(data.get('NSEI', {}), indent=2)}

SENSEX:
{json.dumps(data.get('BSESN', {}), indent=2)}
"""

    return {"messages": [HumanMessage(content=content.strip())]}


class MarketAnalyst(BaseAgent):

    prompt_path = "prompts/market_analyst_prompt.yaml"

    def __init__(self):

        super().__init__()

        success_chain = (
            RunnableLambda(_build_messages) | self.prompt | self.llm | StrOutputParser()
        )

        error_chain = RunnableLambda(
            lambda x: f"Failed to fetch market data:\n{x['error']}"
        )

        branch = RunnableBranch(
            (
                lambda x: x["status"] == "success",
                success_chain,
            ),
            error_chain,
        )

        self.chain = RunnableLambda(process_market_data) | branch

    def run(self) -> str:

        return self.chain.invoke({})
