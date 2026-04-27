from langgraph.graph import END,START,StateGraph
from graph.state import AgentState
import graph.nodes as nodes
import graph.conditional_edges as conditional_edges


def build_graph():

    work_flow=StateGraph(AgentState)

    work_flow.add_node("market_analyst", nodes.run_market_analyst)
    work_flow.add_node("technical_analyst", nodes.run_technical_analyst)
    work_flow.add_node("news_analyst", nodes.run_news_analyst)
    work_flow.add_node("aggregator", nodes.run_aggregator)

    # work_flow.set_entry_point(START)

    work_flow.add_edge(START,"market_analyst")
    work_flow.add_edge(START,"technical_analyst")
    work_flow.add_edge(START,"news_analyst")

    work_flow.add_edge("market_analyst", "aggregator")
    work_flow.add_edge("technical_analyst", "aggregator")
    work_flow.add_edge("news_analyst", "aggregator")

    work_flow.add_edge("aggregator", END)

    return work_flow.compile()

app=build_graph()

