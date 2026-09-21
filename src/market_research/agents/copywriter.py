"""Copywriter agent: reads the campaign image + trend summary and writes a
short marketing quote with justification (multimodal input)."""
import json
import mimetypes
from pathlib import Path

from google.genai import types

from market_research import llm
from market_research.state import PipelineState

SYSTEM_INSTRUCTION = (
    "You are a copywriter that creates elegant campaign quotes based on an "
    "image and a marketing trend summary."
)

QUOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "quote": {"type": "string", "description": "A short, elegant campaign phrase (max 12 words)."},
        "justification": {"type": "string", "description": "Why this quote matches the image and trend."},
    },
    "required": ["quote", "justification"],
}


def copywriter_agent(image_path: str, trend_summary: str) -> dict:
    """Write a campaign quote and justification from the campaign image and trend summary."""
    contents: list = []
    image_note = ""
    if image_path:
        path = Path(image_path)
        mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
        contents.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type))
    else:
        image_note = "(No campaign image is available -- base the quote on the trend summary alone.)"

    text_prompt = f"""
Here is a marketing trend analysis:
{image_note}

Trend summary:
\"\"\"{trend_summary}\"\"\"

Write a short, elegant campaign quote and explain why it matches the {'image and ' if image_path else ''}trend.
"""
    contents.append(text_prompt)

    response = llm.generate(
        contents=contents,
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=QUOTE_SCHEMA,
    )
    if response.text is None:
        raise RuntimeError("Gemini returned no text (response may have been blocked)")
    parsed = json.loads(response.text)
    parsed["image_path"] = image_path
    return parsed


def copywriter_node(state: PipelineState) -> dict:
    """LangGraph node wrapper for copywriter_agent."""
    result = copywriter_agent(state.get("image_path", ""), state.get("trend_summary", ""))
    return {"quote": result["quote"], "justification": result["justification"]}
