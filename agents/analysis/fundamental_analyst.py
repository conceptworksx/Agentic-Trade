from langchain_core.messages import HumanMessage
from agents.base_agent import BaseAgent
from tools.fundamental_tools import (
    get_balance_sheet,
    get_cash_flow,
    get_income_stmt,
    get_valuation,
    get_eps_trend,
    get_fundamentals,
    get_growth,
)

class FundamenetalAnalyst(BaseAgent):

    prompt_path="prompts/fundamental_analyst_prompt.yaml"
    tools=[get_balance_sheet,get_cash_flow,get_income_stmt,get_valuation,
           get_eps_trend,get_fundamentals,get_growth]
    
    def run(self, ticker : str):

        messages=[HumanMessage(content=f"Analyze the fundamentals of : {ticker}")]
        return self._invoke(messages)
        
    