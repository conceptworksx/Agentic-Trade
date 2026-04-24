from graph.state import AgentState
from agents.analysis.market_analyst import MarketAnalyst
from agents.analysis.news_analyst import NewsAnalyst
from agents.analysis.technical_analyst import TechnicalAnalyst

market_analyst = MarketAnalyst() 
technical_analyst = TechnicalAnalyst()      
news_analyst = NewsAnalyst()


def run_market_analyst(state: AgentState) -> dict:
    result = market_analyst.run()
    return {"market_analyst_report": result}

def run_technical_analyst(state : AgentState) -> dict:
    result = technical_analyst.run(ticker=state["ticker_of_company"])
    return {"technical_analysis_report" : result} 

def run_news_analyst(state: AgentState) -> dict:
    result = news_analyst.run()
    return {"news_analyst_report": result}