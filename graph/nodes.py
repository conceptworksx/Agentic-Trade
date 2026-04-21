from graph.state import AgentState
from agents.analysis.market_analyst import MarketAnalyst

market_analyst = MarketAnalyst()       

def run_market_analyst(state: AgentState) -> dict:
    result = market_analyst.run()
    return {"market_analyst_report": result}