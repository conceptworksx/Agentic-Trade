from langgraph.graph import END,START,StateGraph
from graph.state import AgentState
import graph.nodes as nodes
import graph.conditional_edges as conditional_edges


def build_graph():

    work_flow=StateGraph(AgentState)

    work_flow.add_node("market_analyst", nodes.run_market_analyst)

    work_flow.set_entry_point("market_analyst")

    work_flow.add_edge("market_analyst", END)

    return work_flow.compile()

app=build_graph()

