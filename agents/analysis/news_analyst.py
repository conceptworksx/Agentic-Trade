from langchain_core.messages import HumanMessage
from agents.base_agent import BaseAgent
from tools.news_tools import get_company_news

class NewsAnalyst(BaseAgent):
    prompt_path = "prompts/news_analyst_prompt.yaml"
    tools       = [get_company_news]

    def run(self) -> str:
        messages = [HumanMessage(content=f"Get the news")]
        return self._invoke(messages)