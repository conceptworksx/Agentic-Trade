from langchain_core.messages import HumanMessage 
from agents.base_agent import BaseAgent
from core.logging import get_logger
logger = get_logger(__name__)
from tools.technical_tools import get_technical_snapshot

class TechnicalAnalyst(BaseAgent) :
    prompt_path="prompts/technical_analyst_prompt.yaml"
    tools=[get_technical_snapshot]

    def run(self, ticker : str):
    
        message=[HumanMessage(content=f"Analysize the technical for : {ticker}")]
        return self._invoke(message)

