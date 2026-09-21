"""Full campaign pipeline: Market Research -> Graphic Designer -> Copywriter -> Packaging."""
from typing import cast

from langgraph.graph import END, START, StateGraph

from market_research.agents.copywriter import copywriter_node
from market_research.agents.graphic_designer import graphic_designer_node
from market_research.agents.market_research import build_graph as build_market_research_graph
from market_research.agents.packaging import packaging_node
from market_research.state import PipelineState


def build_pipeline():
    """Wire the 4 agents into one end-to-end StateGraph."""
    graph = StateGraph(PipelineState)
    graph.add_node("market_research", build_market_research_graph())
    graph.add_node("graphic_designer", graphic_designer_node)
    graph.add_node("copywriter", copywriter_node)
    graph.add_node("packaging", packaging_node)

    graph.add_edge(START, "market_research")
    graph.add_edge("market_research", "graphic_designer")
    graph.add_edge("graphic_designer", "copywriter")
    graph.add_edge("copywriter", "packaging")
    graph.add_edge("packaging", END)

    return graph.compile()


def run_campaign_pipeline(skip_image: bool = False) -> PipelineState:
    """Build and run the full campaign pipeline, returning the final state."""
    return cast(PipelineState, build_pipeline().invoke({"messages": [], "skip_image": skip_image}))
