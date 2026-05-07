from langgraph.graph import END,START,StateGraph
from graph.state import AgentState
import graph.nodes as nodes
import graph.conditional_edges as conditional_edges
from core.logging import get_logger
logger = get_logger(__name__)


def build_graph():

    work_flow=StateGraph(AgentState)

    work_flow.add_node("market_analyst", nodes.run_market_analyst)
    work_flow.add_node("technical_analyst", nodes.run_technical_analyst)
    work_flow.add_node("news_analyst", nodes.run_news_analyst)
    work_flow.add_node("fundamental_analyst", nodes.run_fundamental_analyst)
    work_flow.add_node("sector_analyst", nodes.run_sector_analyst)
    work_flow.add_node("bull_researcher", nodes.run_bull_researcher)
    work_flow.add_node("aggregator", nodes.run_aggregator)

    work_flow.add_edge(START,"market_analyst")
    work_flow.add_edge(START,"fundamental_analyst")
    work_flow.add_edge(START,"technical_analyst")
    work_flow.add_edge(START,"news_analyst")
    work_flow.add_edge(START,"sector_analyst")
    
    work_flow.add_edge("market_analyst", "aggregator")
    work_flow.add_edge("fundamental_analyst", "aggregator")
    work_flow.add_edge("technical_analyst", "aggregator")
    work_flow.add_edge("news_analyst", "aggregator")
    work_flow.add_edge("sector_analyst", "aggregator")

    work_flow.add_edge("aggregator", END)


    return work_flow.compile()

def build_graph_seq():

    work_flow = StateGraph(AgentState)

    # --- Adding Nodes ---
    work_flow.add_node("market_analyst", nodes.run_market_analyst)
    work_flow.add_node("technical_analyst", nodes.run_technical_analyst)
    work_flow.add_node("news_analyst", nodes.run_news_analyst)
    work_flow.add_node("fundamental_analyst", nodes.run_fundamental_analyst)
    work_flow.add_node("sector_analyst", nodes.run_sector_analyst)
    work_flow.add_node("bull_researcher", nodes.run_bull_researcher)

    # # --- Sequential Edges ---
    # # Flow: Start -> Market -> Fundamental -> Technical -> News -> Sector -> Bull -> End
    work_flow.add_edge(START, "market_analyst")
    work_flow.add_edge("market_analyst", "fundamental_analyst")
    work_flow.add_edge("fundamental_analyst", "technical_analyst")
    work_flow.add_edge("technical_analyst", "news_analyst")
    work_flow.add_edge("news_analyst", "sector_analyst")
    work_flow.add_edge("sector_analyst", "bull_researcher")
    work_flow.add_edge("bull_researcher", END)

    return work_flow.compile()

try:
    app = build_graph()

except Exception as e:

    raise RuntimeError(f"Graph validation failed: {e}")


