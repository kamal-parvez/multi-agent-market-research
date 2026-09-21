"""Shared state passed between LangGraph nodes in the campaign pipeline."""
from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    # Run options
    product_category: str
    skip_image: bool

    # Market Research agent
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
