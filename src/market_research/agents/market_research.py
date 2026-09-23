"""Market Research agent: a small ReAct-style LangGraph subgraph.

Loops between calling Gemini and executing any tool/function calls it
requests, until the model responds with plain text (the trend summary).
"""
from datetime import datetime

from google.genai import types
from langgraph.graph import END, START, StateGraph

from market_research import llm
from market_research.state import PipelineState
from market_research.tools import call_tool, get_tools

def _system_instruction(product_category: str) -> str:
    """Build the Gemini system prompt for the given product category."""
    return f"""
You are a fashion market research agent preparing a trend analysis for a
{product_category} campaign.

Your goal:
1. Explore current fashion trends related to {product_category} using web search.
2. Review the internal product catalog (category="{product_category}") to identify
   items that align with those trends.
3. Recommend one or more products from the catalog that best match
   emerging trends.

Once your analysis is complete, respond with plain text (no more tool
calls) summarizing:
- The top 2-3 trends you found.
- The product(s) from the catalog that fit these trends.
- A justification of why they are a good fit for the campaign.
""".strip()


def _initial_messages(product_category: str) -> list[types.Content]:
    """Build the first user message that kicks off the research loop."""
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"Today's date is {today}. Begin your research on {product_category}."
    return [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]


def call_model(state: PipelineState) -> dict:
    """Call Gemini with the running message history and append its reply."""
    product_category = state.get("product_category", "sunglasses")
    messages = state.get("messages") or _initial_messages(product_category)
    response = llm.generate(
        contents=messages, tools=get_tools(), system_instruction=_system_instruction(product_category)
    )
    if not response.candidates:
        raise RuntimeError("Gemini returned no candidates (response may have been blocked)")
    model_content = response.candidates[0].content
    messages = messages + [model_content]

    if response.function_calls:
        return {"messages": messages}
    return {"messages": messages, "trend_summary": response.text or ""}


def route_after_model(state: PipelineState) -> str:
    """Route to call_tools if the last model reply requested a function call, else end."""
    last = state.get("messages", [])[-1]
    has_call = any(getattr(part, "function_call", None) for part in (last.parts or []))
    return "call_tools" if has_call else END


def call_tools(state: PipelineState) -> dict:
    """Execute every function call in the last model reply and append the results."""
    messages = state.get("messages", [])
    last = messages[-1]
    response_parts = []
    for part in last.parts:
        fc = getattr(part, "function_call", None)
        if not fc:
            continue
        try:
            result = call_tool(fc.name, dict(fc.args or {}))
            response_parts.append(types.Part.from_function_response(name=fc.name, response={"result": result}))
        except Exception as e:
            response_parts.append(types.Part.from_function_response(name=fc.name, response={"error": str(e)}))
    messages = messages + [types.Content(role="user", parts=response_parts)]
    return {"messages": messages}


def build_graph():
    """Compile the call_model <-> call_tools ReAct subgraph."""
    graph = StateGraph(PipelineState)
    graph.add_node("call_model", call_model)
    graph.add_node("call_tools", call_tools)
    graph.add_edge(START, "call_model")
    graph.add_conditional_edges("call_model", route_after_model, {"call_tools": "call_tools", END: END})
    graph.add_edge("call_tools", "call_model")
    return graph.compile()


def market_research_agent(product_category: str = "sunglasses") -> str:
    """Run the market research subgraph standalone and return the trend summary."""
    result = build_graph().invoke({"messages": [], "product_category": product_category})
    return result["trend_summary"]
