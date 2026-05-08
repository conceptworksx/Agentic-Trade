from langchain_core.messages import HumanMessage
from langchain_core.runnables import (
    RunnableLambda,
    RunnableBranch,
)
from langchain_core.output_parsers import StrOutputParser

from agents.base_agent import BaseAgent

from tools.fundamental_tools import process_fundamental_data


def _build_messages(data: dict) -> dict:

    content = f"""
Analyze the financial fundamentals of the company {data['ticker']}:

INCOME STATEMENT:
{data['income_stmt']}

BALANCE SHEET:
{data['balance_sheet']}

CASH FLOW:
{data['cash_flow']}

FUNDAMENTALS:
{data['fundamentals']}

EPS TREND:
{data['eps_trend']}

VALUATION:
{data['valuation']}

GROWTH:
{data['growth']}
"""

    return {"messages": [HumanMessage(content=content)]}


class FundamentalAnalyst(BaseAgent):

    prompt_path = "prompts/fundamental_analyst_prompt.yaml"

    def __init__(self):

        super().__init__()

        success_chain = (
            RunnableLambda(_build_messages) | self.prompt | self.llm | StrOutputParser()
        )

        error_chain = RunnableLambda(
            lambda x: f"Failed to fetch fundamental data for "
            f"{x['ticker']}: {x['error']}"
        )

        branch = RunnableBranch(
            (
                lambda x: x["status"] == "success",
                success_chain,
            ),
            error_chain,
        )

        self.chain = RunnableLambda(process_fundamental_data) | branch

    def run(self, state):

        return self.chain.invoke({"ticker": state["ticker_of_company"]})
