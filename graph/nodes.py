from graph.state import AgentState
from agents.analysis.market_analyst import MarketAnalyst
from agents.analysis.news_analyst import NewsAnalyst
from agents.analysis.technical_analyst import TechnicalAnalyst
from agents.analysis.fundamental_analyst import FundamenetalAnalyst
from agents.research.bull_researcher import BullReseacher

market_analyst = MarketAnalyst() 
fundamental_analyst = FundamenetalAnalyst()
technical_analyst = TechnicalAnalyst()      
news_analyst = NewsAnalyst()

bull_researcher=BullReseacher()


def run_market_analyst(state: AgentState) -> dict:
    result = market_analyst.run()
    return {"market_analyst_report": result}

def run_fundamental_analyst(state : AgentState) -> dict:
    result = fundamental_analyst.run(ticker=state["ticker_of_company"])
    return {"fundamental_analyst_report" : result}

def run_technical_analyst(state : AgentState) -> dict:
    result = technical_analyst.run(ticker=state["ticker_of_company"])
    return {"technical_analyst_report" : result} 

def run_news_analyst(state: AgentState) -> dict:
    result = news_analyst.run(ticker=state["ticker_of_company"])
    return {"news_analyst_report": result}

def run_bull_researcher(state: AgentState) -> dict:
    investment_debate=state["investment_debate"]
    debate_history=investment_debate.get("debate_history","")
    bear_thesis=investment_debate.get("bear_thesis","")
    bull_thesis=investment_debate.get("bull_thesis" , "")
    debate_rounds=investment_debate.get("debate_rounds", "")
    market_analysis_report=state["market_analyst_report"]
    fundamental_analysis_report=state["fundamental_analyst_report"]
    technical_analysis_report=state["technical_analyst_report"]
    news_analysis_report=state["news_analyst_report"]

    result = bull_researcher.run(market_analysis_report,fundamental_analysis_report,technical_analysis_report,
                                 news_analysis_report, debate_history,bear_thesis)
    
    updated_investment_debate={
        "debate_history" : debate_history + "\n" + result,
        "bull_thesis" : bull_thesis + "\n" + result,
        "bear_thesis" : bear_thesis,
        "current_response" : result,
        "debate_rounds" : debate_rounds +1
    }
    
    return { "investment_debate" : updated_investment_debate}


