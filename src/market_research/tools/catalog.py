"""Internal product catalog tool, backed by a local CSV file."""
from pathlib import Path

import pandas as pd
from google.genai import types

from market_research.config import DEFAULT_CATALOG_PATH


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def product_catalog_tool(max_items: int = 10, catalog_path: Path = DEFAULT_CATALOG_PATH) -> list[dict]:
    """Return sunglasses products from the internal inventory catalog."""
    df = load_catalog(catalog_path)
    return df.head(max_items).to_dict(orient="records")


CATALOG_TOOL_DECLARATION = types.FunctionDeclaration(
    name="product_catalog_tool",
    description="Get sunglasses products from the internal inventory catalog.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "max_items": types.Schema(
                type=types.Type.INTEGER,
                description="Maximum number of catalog items to return.",
            )
        },
    ),
)
