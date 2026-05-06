import json
from langchain_core.messages import HumanMessage 
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from agents.base_agent import BaseAgent
from tools.technical_tools import (
    fetch_df, compute_moving_averages, compute_rsi, compute_macd, compute_bollinger,
    compute_atr, compute_vwma, compute_mfi, compute_volume, compute_price_levels
)


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

        technical_fetcher = RunnableLambda(
            lambda x: {
                "ticker": x["ticker"],
                "fetch": fetch_df(x["ticker"])
            }
        )

        prep = RunnableLambda(
            lambda x: {
                "ticker": x["ticker"],
                "df": (
                    x["fetch"]["data"]
                    if x.get("fetch", {}).get("status") == "success"
                    else None
                ),
                "status": x.get("fetch", {}).get("status"),
                "error": x.get("fetch", {}).get("error"),
            }
        )


        process_technical_data = RunnableParallel(
            {
                "ticker": RunnableLambda(lambda x: x["ticker"]),

                "price_levels": RunnableLambda(lambda x: compute_price_levels(x["df"])),

                "moving_averages": RunnableLambda(lambda x: compute_moving_averages(x["df"])),

                "rsi": RunnableLambda(lambda x: compute_rsi(x["df"])),

                "macd": RunnableLambda(lambda x: compute_macd(x["df"])),

                "bollinger": RunnableLambda(lambda x: compute_bollinger(x["df"])),

                "atr": RunnableLambda(lambda x: compute_atr(x["df"])),

                "vwma": RunnableLambda(lambda x: compute_vwma(x["df"])),

                "mfi": RunnableLambda(lambda x: compute_mfi(x["df"])),

                "volume": RunnableLambda(lambda x: compute_volume(x["df"])),
            }
        )


        self.chain = (
            technical_fetcher
            | prep
            | process_technical_data
            | RunnableLambda(_build_messages)
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def run(self, ticker: str):
        return self.chain.invoke({"ticker": ticker})