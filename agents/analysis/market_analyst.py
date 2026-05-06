import json
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableParallel, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from agents.base_agent import BaseAgent
from tools.market_tools import (fetch_df, extract_metrics, TICKERS)


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

    return {
        "messages": [
            HumanMessage(content=content.strip())
        ]
    }

class MarketAnalyst(BaseAgent):
    prompt_path = "prompts/market_analyst_prompt.yaml"

    def __init__(self):
        super().__init__()


        market_fetcher = RunnableParallel({
            name : RunnableLambda(lambda _, t=ticker: fetch_df(t))
            for name, ticker in TICKERS.items()
        })
        
        process_market_data = RunnableLambda(
                lambda x: {
                    name: extract_metrics(name, v["status"], v["data"])
                    for name, v in x.items()
                }
        )

        self.chain=(
            market_fetcher
            | process_market_data
            | RunnableLambda(_build_messages)
            | self.prompt
            | self.llm
            | StrOutputParser()
        )


    def run(self) -> str:
        return self.chain.invoke({})