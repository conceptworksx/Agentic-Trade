import json

from langchain_core.messages import HumanMessage
from langchain_core.runnables import (
    RunnableLambda,
    RunnableBranch,
)
from langchain_core.output_parsers import StrOutputParser

from agents.base_agent import BaseAgent

from tools.technical_tools import process_technical_data


def _build_messages(data: dict) -> dict:
    content = f"""
Analyze the technical data for the company {data.get('ticker')}:

Relative Strength Index:
{json.dumps(data.get('rsi', {}), indent=2)}

Moving Average Convergence Divergence:
{json.dumps(data.get('macd', {}), indent=2)}

Average True Range:
{json.dumps(data.get('atr', {}), indent=2)}

Volume Weighted Moving Average:
{json.dumps(data.get('vwma', {}), indent=2)}

Money Flow Index:
{json.dumps(data.get('mfi', {}), indent=2)}

Bollinger Bands:
{json.dumps(data.get('bollinger', {}), indent=2)}

Moving Averages:
{json.dumps(data.get('moving_averages', {}), indent=2)}

Trading Volume:
{json.dumps(data.get('volume', {}), indent=2)}

Support and Resistance Levels:
{json.dumps(data.get('price_levels', {}), indent=2)}
"""

    return {"messages": [HumanMessage(content=content)]}


class TechnicalAnalyst(BaseAgent):

    prompt_path = "prompts/technical_analyst_prompt.yaml"

    def __init__(self):

        super().__init__()

        success_chain = (
            RunnableLambda(_build_messages) | self.prompt | self.llm | StrOutputParser()
        )

        error_chain = RunnableLambda(
            lambda x: f"Failed to fetch technical data for {x['ticker']}: {x['error']}"
        )

        branch = RunnableBranch(
            (
                lambda x: x["status"] == "success",
                success_chain,
            ),
            error_chain,
        )

        self.chain = RunnableLambda(process_technical_data) | branch

    def run(self, state):

        return self.chain.invoke({"ticker": state["ticker_of_company"]})
