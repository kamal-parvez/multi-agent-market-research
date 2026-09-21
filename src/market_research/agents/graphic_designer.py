"""Graphic Designer agent: turns trend insights into an image prompt, a
caption, and a generated campaign image."""
from datetime import datetime

from market_research import llm
from market_research.config import DEFAULT_OUTPUT_DIR
from market_research.image_gen.hf_image import generate_image
from market_research.state import PipelineState

SYSTEM_INSTRUCTION = (
    "You are a visual marketing assistant. Based on the input trend insights, "
    "write a creative and visual prompt for an AI image generation model, and also a short caption."
)

PROMPT_CAPTION_SCHEMA = {
    "type": "object",
    "properties": {
        "prompt": {"type": "string", "description": "Vivid, descriptive prompt for an image generation model."},
        "caption": {"type": "string", "description": "Short, punchy marketing caption."},
    },
    "required": ["prompt", "caption"],
}


def graphic_designer_agent(trend_insights: str, caption_style: str = "short punchy") -> dict:
    """Turn trend insights into an image prompt, caption, and generated image."""
    user_prompt = f"""
Trend insights:
{trend_insights}

Please output a vivid, descriptive prompt to guide image generation, and a
marketing caption in style: {caption_style}.
"""
    parsed = llm.generate_json(user_prompt, PROMPT_CAPTION_SCHEMA, system_instruction=SYSTEM_INSTRUCTION)
    prompt, caption = parsed["prompt"], parsed["caption"]

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = DEFAULT_OUTPUT_DIR / f"campaign_image_{timestamp}.png"
    generate_image(prompt, output_path)

    return {"image_path": str(output_path), "prompt": prompt, "caption": caption}


def graphic_designer_node(state: PipelineState) -> dict:
    """LangGraph node wrapper for graphic_designer_agent, honoring skip_image."""
    if state.get("skip_image"):
        return {"image_path": "", "image_prompt": "(skipped)", "caption": "(skipped)"}
    result = graphic_designer_agent(state.get("trend_summary", ""))
    return {"image_path": result["image_path"], "image_prompt": result["prompt"], "caption": result["caption"]}
