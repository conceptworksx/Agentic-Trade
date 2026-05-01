from langchain_core.messages import HumanMessage
from agents.base_agent import BaseAgent
from core.logging import get_logger
logger = get_logger(__name__)
from tools.fundamental_tools import (
    get_fundamental_snapshot
)

class FundamenetalAnalyst(BaseAgent):

    prompt_path="prompts/fundamental_analyst_prompt.yaml"
    tools=[get_fundamental_snapshot]
    
    def run(self, ticker : str):

        messages=[HumanMessage(content=f"Analyze the fundamentals of : {ticker}")]
        return self._invoke(messages)
        
    