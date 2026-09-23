"""Builds and refreshes the local product catalog on demand from the raw
Amazon dataset files (any *.jsonl directly under data/raw/).

Two layers:
- `build_category_index` / `load_category_index`: a scan that tallies how
  many real products exist per category, using the leaf of each product's
  `categories` breadcrumb (e.g. "Sunglasses", "T-Shirts") as the category
  name -- no hand-written keyword rules needed. Cached to disk, keyed to a
  fingerprint (size + mtime) of the raw files, so it auto-rebuilds whenever
  the raw data changes (files added, removed, or replaced).
- `ensure_category_in_catalog`: given a category the user picked, makes sure
  data/catalog.csv has curated rows for it, building them from the raw
  dataset (and caching that per-category pool, also fingerprint-checked) if
  this is the first request or the raw data has since changed.
"""
import json
import re
import random
from collections import Counter
from pathlib import Path
from typing import Iterator

import pandas as pd

from market_research.config import PROJECT_ROOT, DEFAULT_CATALOG_PATH

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
CATEGORY_INDEX_PATH = PROJECT_ROOT / "data" / "category_index.json"
RAW_CATEGORY_POOL_DIR = RAW_DATA_DIR / "by_category"

MIN_CATEGORY_COUNT = 200
NOISE_LEAF_BLOCKLIST = {
    "casual", "sets", "clothing", "costumes", "novelty", "other", "accessories", "fashion",
    "westlake", "women", "men", "girls", "boys", "unisex",
}

TARGET_PER_CATEGORY = 200
MAX_PER_BRAND = 5
MIN_RATING_COUNT = 25
MIN_RATING = 3.5
MIN_DESC_LEN = 40

CATALOG_FIELDS = [
    "name", "item_id", "description", "quantity_in_stock", "price",
    "brand", "rating", "rating_count", "image_url", "category",
]


def _raw_files() -> list[Path]:
    """Every raw dataset file to scan -- any .jsonl directly under data/raw/
    (not its by_category/ subdirectory, which holds derived pools)."""
    if not RAW_DATA_DIR.exists():
        return []
    return sorted(p for p in RAW_DATA_DIR.glob("*.jsonl") if p.is_file())


def _fingerprint(paths: list[Path]) -> dict[str, dict[str, float]]:
    """{filename: {size, mtime}} for the given files -- cheap to compute
    (just stat calls), used to detect when the raw data has changed."""
    return {p.name: {"size": p.stat().st_size, "mtime": p.stat().st_mtime} for p in paths}


def _iter_raw_lines(paths: list[Path]) -> Iterator[str]:
    """Stream raw lines across multiple files in order."""
    for path in paths:
        with open(path) as f:
            yield from f


def _leaf_category(rec: dict) -> str | None:
    """The last element of a product's category breadcrumb, e.g. 'Sunglasses'."""
    cats = rec.get("categories") or []
    if not cats:
        return None
    leaf = cats[-1].strip()
    if not leaf or leaf.lower() in NOISE_LEAF_BLOCKLIST:
        return None
    return leaf


def _slug(category: str) -> str:
    """Filesystem-safe slug for a category name."""
    return re.sub(r"[^a-z0-9]+", "_", category.strip().lower()).strip("_")


def _pool_path(category: str) -> Path:
    """Path to a category's cached raw pool file."""
    return RAW_CATEGORY_POOL_DIR / f"{_slug(category)}.jsonl"


def _pool_meta_path(category: str) -> Path:
    """Path to a category's pool fingerprint metadata file."""
    return RAW_CATEGORY_POOL_DIR / f"{_slug(category)}.meta.json"


def _pool_is_fresh(category: str) -> bool:
    """Whether `category`'s cached raw pool was built from the current raw
    files (same set, same size+mtime for each)."""
    pool_path, meta_path = _pool_path(category), _pool_meta_path(category)
    if not pool_path.exists() or not meta_path.exists():
        return False
    meta = json.loads(meta_path.read_text())
    return meta.get("raw_fingerprint") == _fingerprint(_raw_files())


def _write_pool_meta(category: str) -> None:
    """Save the current raw-file fingerprint for a category's pool."""
    _pool_meta_path(category).write_text(json.dumps({"raw_fingerprint": _fingerprint(_raw_files())}, indent=2))


def build_category_index() -> dict[str, int]:
    """One streaming pass over all raw dataset files, tallying products per
    leaf category. Cached to disk alongside the raw-file fingerprint used to
    build it, so `load_category_index` knows when to rebuild."""
    paths = _raw_files()
    counts = Counter()
    for line in _iter_raw_lines(paths):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        leaf = _leaf_category(rec)
        if leaf:
            counts[leaf] += 1

    index = {name: n for name, n in counts.items() if n >= MIN_CATEGORY_COUNT}
    CATEGORY_INDEX_PATH.write_text(json.dumps({
        "raw_fingerprint": _fingerprint(paths),
        "categories": index,
    }, indent=2))
    return index


def load_category_index() -> dict[str, int]:
    """Load the cached category index, rebuilding it if it's missing or if
    the raw dataset files have changed (added, removed, or replaced) since
    it was last built."""
    paths = _raw_files()
    if CATEGORY_INDEX_PATH.exists():
        cached = json.loads(CATEGORY_INDEX_PATH.read_text())
        if cached.get("raw_fingerprint") == _fingerprint(paths):
            return cached["categories"]
    return build_category_index()


def top_categories(n: int = 30) -> list[tuple[str, int]]:
    """The n most common real product categories, by raw dataset frequency."""
    index = load_category_index()
    return sorted(index.items(), key=lambda kv: kv[1], reverse=True)[:n]


def match_category(category: str) -> str | None:
    """Resolve user input to the exact-cased category name in the index,
    case-insensitively, or None if it isn't a recognized category."""
    index = load_category_index()
    category = category.strip().lower()
    return next((name for name in index if name.lower() == category), None)


def seed_category_pools(categories: list[str]) -> None:
    """One streaming pass across all raw files that writes matching records
    for each of `categories` into per-category jsonl pools, for fast
    curation later."""
    RAW_CATEGORY_POOL_DIR.mkdir(parents=True, exist_ok=True)
    wanted_lower = {c.lower() for c in categories}
    handles = {c.lower(): open(_pool_path(c), "w") for c in categories}

    for line in _iter_raw_lines(_raw_files()):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        leaf = _leaf_category(rec)
        if leaf and leaf.lower() in wanted_lower:
            handles[leaf.lower()].write(line)

    for h in handles.values():
        h.close()
    for c in categories:
        _write_pool_meta(c)


def _build_pool_for_category(category: str) -> None:
    """On-demand single-category pass, used when a category wasn't
    pre-seeded or its cached pool has gone stale."""
    RAW_CATEGORY_POOL_DIR.mkdir(parents=True, exist_ok=True)
    target_lower = category.strip().lower()
    with open(_pool_path(category), "w") as out:
        for line in _iter_raw_lines(_raw_files()):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            leaf = _leaf_category(rec)
            if leaf and leaf.lower() == target_lower:
                out.write(line)
    _write_pool_meta(category)


def curate_category(category: str) -> list[dict]:
    """Build a quality-filtered, ranked, brand-diverse product list for
    `category`, using a cached raw pool if it's still fresh or rebuilding
    it (from the current raw files) if not."""
    if not _pool_is_fresh(category):
        _build_pool_for_category(category)

    candidates = []
    seen_titles = set()
    with open(_pool_path(category)) as f:
        for line in f:
            rec = json.loads(line)
            title = (rec.get("title") or "").strip()
            price = rec.get("price")
            if price in (None, ""):
                continue
            try:
                price = float(price)
            except (TypeError, ValueError):
                continue
            rating_n = rec.get("rating_number") or 0
            if rating_n < MIN_RATING_COUNT:
                continue
            avg_rating = rec.get("average_rating")
            if not avg_rating or avg_rating < MIN_RATING:
                continue
            desc_list = [d for d in (rec.get("description") or []) if d and d.strip()]
            features = [d for d in (rec.get("features") or []) if d and d.strip()]
            description = " ".join(desc_list) if desc_list else " ".join(features)
            description = re.sub(r"\s+", " ", description).strip()
            if len(description) < MIN_DESC_LEN:
                continue
            key = title.lower()[:50]
            if key in seen_titles:
                continue
            seen_titles.add(key)
            images = rec.get("images") or []
            image_url = ""
            for im in images:
                if im.get("variant") == "MAIN" and im.get("large"):
                    image_url = im["large"]
                    break
            candidates.append({
                "name": title[:100].rstrip(),
                "item_id": rec.get("parent_asin"),
                "description": description[:350],
                "price": round(price, 2),
                "brand": (rec.get("store") or "").strip()[:40],
                "rating": avg_rating,
                "rating_count": rating_n,
                "image_url": image_url,
                "category": category,
            })

    candidates.sort(key=lambda r: r["rating_count"], reverse=True)
    brand_counts: dict[str, int] = {}
    selected = []
    for r in candidates:
        b = r["brand"].lower()
        if brand_counts.get(b, 0) >= MAX_PER_BRAND:
            continue
        brand_counts[b] = brand_counts.get(b, 0) + 1
        selected.append(r)
        if len(selected) >= TARGET_PER_CATEGORY:
            break

    for r in selected:
        r["quantity_in_stock"] = random.randint(2, 60)
    return selected


def ensure_category_in_catalog(category: str, catalog_path: Path = DEFAULT_CATALOG_PATH) -> bool:
    """Make sure `category` has curated rows in the catalog CSV, building
    (or rebuilding, if the raw data has changed) and caching them on demand
    if needed. Returns False if `category` isn't a recognized product
    category in the raw dataset."""
    matched_name = match_category(category)
    if matched_name is None:
        return False

    df = pd.read_csv(catalog_path) if catalog_path.exists() else pd.DataFrame()
    has_rows = not df.empty and "category" in df.columns and (df["category"].str.lower() == matched_name.lower()).any()

    if has_rows and _pool_is_fresh(matched_name):
        return True  # already cached and up to date

    rows = curate_category(matched_name)  # rebuilds the pool internally if it was stale
    if not rows:
        return False

    if has_rows:
        df = df[df["category"].str.lower() != matched_name.lower()]  # drop stale rows before replacing

    new_df = pd.DataFrame(rows)[CATALOG_FIELDS]
    combined = new_df if df.empty else pd.concat([df, new_df], ignore_index=True)
    combined.to_csv(catalog_path, index=False)
    return True
