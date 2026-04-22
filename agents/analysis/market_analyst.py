from langchain_core.messages import HumanMessage
from agents.base_agent import BaseAgent
from tools.market_tools import get_market_snapshot

class MarketAnalyst(BaseAgent):
    prompt_path = "prompts/market_analyst_prompt.yaml"
    tools       = [get_market_snapshot]

    def run(self) -> str:
        messages = [HumanMessage(content=f"Analyse the market")]
        return self._invoke(messages)