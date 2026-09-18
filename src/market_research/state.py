"""Shared state passed between LangGraph nodes in the campaign pipeline."""
from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    # Market Research agent (internal ReAct loop). Holds google.genai.types.Content
    # objects, not plain dicts -- typed Any here since TypedDict can't express that.
    messages: list[Any]
    trend_summary: str

    # Graphic Designer agent
    image_prompt: str
    caption: str
    image_path: str

    # Copywriter agent
    quote: str
    justification: str

    # Packaging agent
    report_path: str

    # Run options
    skip_image: bool
