from langchain_core.messages import HumanMessage
from agents.base_agent import BaseAgent

class BullReseacher(BaseAgent):

    prompt_path="prompts/bull_researcher_prompt.yaml"
    tools=[]

    def run(self, market_analysis_report, fundamental_analysis_report, technical_analysis_report,
             news_analysis_report, debate_history, bear_thesis):

        messages = [HumanMessage(content="Perform research as a Bullish Researcher")]
        return self._invoke(
            messages,
            market_analysis_report=market_analysis_report,
            fundamental_analysis_report=fundamental_analysis_report,
            technical_analysis_report=technical_analysis_report,
            news_analysis_report=news_analysis_report,
            debate_history=debate_history,
            last_bear_argument=bear_thesis,
        ) 