from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser

from agents.base_agent import BaseAgent
from tools.fundamental_tools import (
    ticker_data,
    fetch_income_stmt,
    fetch_balance_sheet,
    fetch_cash_flow,
    fetch_fundamentals,
    fetch_eps_trend,
    fetch_valuation,
    fetch_growth,
)



def _build_messages(data: dict) -> dict:
    """
    Convert structured tool output into LLM input message.
    """
    content = f"""
Analyze the financial fundamentals of the company based on the following data:

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

        # fetch raw data once
        fetch_node = RunnableLambda(lambda x: ticker_data(x["ticker"]))
     
        # parallel extraction
        extractors = RunnableParallel({
            "income_stmt": RunnableLambda(
                lambda x: fetch_income_stmt(x["financials"])
            ),
            "balance_sheet": RunnableLambda(
                lambda x: fetch_balance_sheet(x["balance_sheet"], x["info"])
            ),
            "cash_flow": RunnableLambda(
                lambda x: fetch_cash_flow(x["cash_flow"])
            ),
            "fundamentals": RunnableLambda(
                lambda x: fetch_fundamentals(x["financials"], x["balance_sheet"])
            ),
            "eps_trend": RunnableLambda(
                lambda x: fetch_eps_trend(x["financials"])
            ),
            "valuation": RunnableLambda(
                lambda x: fetch_valuation(x["info"], x["major_holders"])
            ),
            "growth": RunnableLambda(
                lambda x: fetch_growth(x["financials"])
            ),
        })

        # Full chain
        self.chain = (
            fetch_node
            | extractors
            | RunnableLambda(_build_messages)
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def run(self, ticker: str) -> str:
        return self.chain.invoke({
            "ticker": ticker
        })