"""Web search tool backed by Tavily."""
import time

from google.genai import types
from tavily import TavilyClient

from market_research.config import TAVILY_API_KEY


def tavily_search_tool(query: str, max_results: int = 5, include_images: bool = False) -> list[dict]:
    """Perform a web search for fashion trends using Tavily, with retry/backoff."""
    if not TAVILY_API_KEY:
        raise ValueError("TAVILY_API_KEY not found in environment variables.")

    client = TavilyClient(api_key=TAVILY_API_KEY)

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            response = client.search(
                query=query,
                max_results=max_results,
                include_images=include_images,
            )

            results = []
            for r in response.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "url": r.get("url", ""),
                })

            if include_images:
                for img_url in response.get("images", []):
                    results.append({"image_url": img_url})

            return results

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(1.5 * (attempt + 1))  # backoff: 1.5s, 3s
                continue

    return [{"error": str(last_error)}]


SEARCH_TOOL_DECLARATION = types.FunctionDeclaration(
    name="tavily_search_tool",
    description="Perform a web search for sunglasses/fashion trends.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "max_results": {"type": "integer", "description": "Maximum number of results."},
        },
        "required": ["query"],
    },
)
