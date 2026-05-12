from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from agents.base_agent import BaseAgent
from tools.news_tools import (
    get_company_news,
    get_indian_market_news,
    get_global_market_news,
)
import json


def _build_messages(data: dict) -> dict:
    content = f"""
Analyze the news sentiment for {data['ticker']}.

COMPANY NEWS:
{json.dumps(data['company_news'], indent=2)}

INDIAN MARKET NEWS:
{json.dumps(data['indian_news'], indent=2)}

GLOBAL MARKET NEWS:
{json.dumps(data['global_news'], indent=2)}
"""
    return {"messages": [HumanMessage(content=content)]}


class NewsAnalyst(BaseAgent):

    prompt_path = "prompts/news_analyst_prompt.yaml"

    def __init__(self):
        super().__init__()

        news_fetcher = RunnableParallel(
            {
                "ticker": RunnableLambda(lambda x: x["ticker"]),
                "company_news": RunnableLambda(lambda x: get_company_news(x["ticker"])),
                "indian_news": RunnableLambda(lambda _: get_indian_market_news()),
                "global_news": RunnableLambda(lambda _: get_global_market_news()),
            }
        )

        self.chain = (
            news_fetcher
            | RunnableLambda(_build_messages)
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def run(self, state) -> str:
        return self.chain.invoke(
            {
                "ticker": state["ticker_of_company"],
            }
        )
