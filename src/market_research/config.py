"""Environment and model configuration for the market research pipeline."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

# "-latest" alias avoids hardcoded model names going stale
TEXT_MODEL = os.getenv("MARKET_RESEARCH_TEXT_MODEL", "gemini-flash-lite-latest")
IMAGE_MODEL = os.getenv("MARKET_RESEARCH_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")

DEFAULT_CATALOG_PATH = PROJECT_ROOT / "data" / "catalog.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"


def require_keys(*names: str) -> None:
    """Raise if any of the named environment variables are unset."""
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            f"Set them in {PROJECT_ROOT / '.env'}."
        )
