"""Tool registry: declarations + dispatch for the Market Research agent."""
from google.genai import types

from market_research.tools.catalog import CATALOG_TOOL_DECLARATION, product_catalog_tool
from market_research.tools.search import SEARCH_TOOL_DECLARATION, tavily_search_tool

TOOL_FUNCTIONS = {
    "tavily_search_tool": tavily_search_tool,
    "product_catalog_tool": product_catalog_tool,
}


def get_tools() -> list[types.Tool]:
    return [types.Tool(function_declarations=[SEARCH_TOOL_DECLARATION, CATALOG_TOOL_DECLARATION])]


def call_tool(name: str, args: dict) -> object:
    if name not in TOOL_FUNCTIONS:
        raise KeyError(f"Unknown tool: {name}")
    return TOOL_FUNCTIONS[name](**args)
