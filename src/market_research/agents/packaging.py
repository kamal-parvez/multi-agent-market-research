"""Packaging agent: rewrites the trend summary for an executive audience and
assembles all campaign assets into a markdown report."""
from datetime import datetime
from pathlib import Path

from market_research import llm
from market_research.config import DEFAULT_OUTPUT_DIR
from market_research.state import PipelineState

SYSTEM_INSTRUCTION = "You are a marketing communication expert writing elegant campaign summaries for executives."

CATEGORY_EMOJI = {
    "sunglasses": "🕶️",
    "shoes": "👟",
    "watches": "⌚",
    "bags": "👜",
    "hats": "🧢",
    "wrist watches": "⌚",
    "t-shirts": "👕",
    "fashion sneakers": "👟",
    "sneakers": "👟",
    "flats": "🥿",
    "slippers": "🥿",
    "blouses & button-down shirts": "👚",
    "tunics": "👚",
    "tanks & camis": "👚",
    "pumps": "👠",
    "platforms & wedges": "👠",
    "heeled sandals": "👡",
    "sandals": "👡",
    "dresses": "👗",
    "loafers & slip-ons": "👞",
    "road running": "🏃",
    "jeans": "👖",
    "leggings": "👖",
    "pendant necklaces": "📿",
    "necklaces": "📿",
    "rings": "💍",
    "drop & dangle": "💎",
    "stud": "💎",
    "pullovers": "🧥",
    "fashion hoodies & sweatshirts": "🧥",
    "wallets": "👛",
    "baseball caps": "🧢",
    "socks": "🧦",
    "ankle & bootie": "👢",
    "boots": "👢",
}


def packaging_agent(
    trend_summary: str,
    image_path: str,
    quote: str,
    justification: str,
    product_category: str = "sunglasses",
    output_path: Path | None = None,
) -> str:
    """Rewrite the trend summary for executives and assemble the markdown report."""
    beautified_summary = llm.generate_text(
        f'Please rewrite the following trend summary to be clear, professional, and engaging for a CEO audience:\n\n"""{trend_summary.strip()}"""',
        system_instruction=SYSTEM_INSTRUCTION,
    )

    emoji = CATEGORY_EMOJI.get(product_category.strip().lower(), "🛍️")
    markdown_content = f"""# {emoji} {product_category.title()} Campaign – Executive Summary

## 📊 Refined Trend Insights
{beautified_summary}

## 🎯 Campaign Visual
![Campaign visual]({image_path})

## ✍️ Campaign Quote
{quote.strip()}

## ✅ Why This Works
{justification.strip()}

---

*Report generated on {datetime.now().strftime('%Y-%m-%d')}*
"""

    if output_path is None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path = DEFAULT_OUTPUT_DIR / f"campaign_summary_{timestamp}.md"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown_content, encoding="utf-8")
    return str(output_path)


def packaging_node(state: PipelineState) -> dict:
    """LangGraph node wrapper for packaging_agent."""
    report_path = packaging_agent(
        trend_summary=state.get("trend_summary", ""),
        image_path=state.get("image_path", ""),
        quote=state.get("quote", ""),
        justification=state.get("justification", ""),
        product_category=state.get("product_category", "sunglasses"),
    )
    return {"report_path": report_path}
