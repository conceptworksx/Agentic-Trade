from langchain_core.messages import HumanMessage
from agents.base_agent import BaseAgent
from core.logging import get_logger
logger = get_logger(__name__)
from tools.news_tools import get_news_snapshot

class NewsAnalyst(BaseAgent):
    prompt_path = "prompts/news_analyst_prompt.yaml"
    tools       = [get_news_snapshot]

    def run(self , ticker : str):

        messages = [HumanMessage(content=f"Analysize the news for : {ticker}")]
        return self._invoke(messages)
