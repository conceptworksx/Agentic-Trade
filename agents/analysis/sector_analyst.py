from langchain_core.messages import HumanMessage
from agents.base_agent import BaseAgent
from core.logging import get_logger

logger = get_logger(__name__)
from tools.sector_tools import get_sector_snapshot

class SectorAnalyst(BaseAgent):
    prompt_path = "prompts/sector_analyst_prompt.yaml"
    tools = [get_sector_snapshot]

    def run(self, sector: str):

        messages = [HumanMessage(content=f"Analyze the sector of : {sector}")]
        return self._invoke(messages)
