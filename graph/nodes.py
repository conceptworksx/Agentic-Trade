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
    return {"technical_analyst_report" : result} 

def run_news_analyst(state: AgentState) -> dict:
    result = news_analyst.run(ticker=state["ticker_of_company"])
    return {"news_analyst_report": result}

def run_aggregator(state: AgentState) -> dict:
  
    market_data = state.get("market_data")
    technical_data = state.get("technical_data")
    news_data = state.get("news_data")
    
    final_report = f"""
    ### FINAL SUMMARY
    - Market Status: {market_data}
    - Technical Analysis: {technical_data}
    - News Sentiment: {news_data}
    
    """
    return {"final_report": final_report}
