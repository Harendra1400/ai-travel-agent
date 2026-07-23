"""LangGraph definition for the travel-planning workflow."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.planner import plan_itinerary, validate_plan
from app.agents.state import TravelGraphState


def build_travel_graph(
    checkpointer: BaseCheckpointSaver[str] | None = None,
) -> CompiledStateGraph[TravelGraphState, None, TravelGraphState]:
    """Compile a small, explicit graph with deterministic validation."""
    graph = StateGraph(TravelGraphState)
    graph.add_node("planner", plan_itinerary)
    graph.add_node("validator", validate_plan)
    graph.add_edge(START, "planner")
    graph.add_edge("planner", "validator")
    graph.add_edge("validator", END)
    return graph.compile(checkpointer=checkpointer)
