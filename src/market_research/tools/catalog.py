"""Internal product catalog tool, backed by a local CSV file."""
from pathlib import Path

import pandas as pd
from google.genai import types

from market_research.config import DEFAULT_CATALOG_PATH


def load_catalog(path: Path = DEFAULT_CATALOG_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def available_categories(catalog_path: Path = DEFAULT_CATALOG_PATH) -> dict[str, int]:
    """Return {category: item_count} for every category present in the catalog."""
    df = load_catalog(catalog_path)
    if "category" not in df.columns:
        return {}
    return df["category"].str.lower().value_counts().sort_index().to_dict()


def product_catalog_tool(
    category: str = "",
    max_items: int = 10,
    catalog_path: Path = DEFAULT_CATALOG_PATH,
) -> list[dict]:
    """Return products from the internal inventory catalog, optionally filtered by category."""
    df = load_catalog(catalog_path)
    if category and "category" in df.columns:
        df = df.loc[df["category"].str.lower() == category.strip().lower()]
    return df.head(max_items).to_dict(orient="records")


CATALOG_TOOL_DECLARATION = types.FunctionDeclaration(
    name="product_catalog_tool",
    description="Get products from the internal inventory catalog, filtered by product category.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "category": types.Schema(
                type=types.Type.STRING,
                description="Product category to filter by, e.g. 'sunglasses', 'shoes', 'watches'.",
            ),
            "max_items": types.Schema(
                type=types.Type.INTEGER,
                description="Maximum number of catalog items to return.",
            ),
        },
    ),
)
