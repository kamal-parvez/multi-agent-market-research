# CONTEXT.md — Claude session-restart memory

Scratchpad for an AI picking this project back up cold. Terse, not prose. Update
this file whenever a decision changes, progress is made, or an issue surfaces —
don't let it go stale.

## Current state: working, clean, committed

Last commit: `358e3a1` on `main`. Working tree clean as of that commit. 3 commits
total (`26b9096` initial → `19166a6` type-fixes + first real-data catalog →
`358e3a1` generalized-to-any-category + on-demand catalog). No remote configured
(never pushed).

Run it: `market-research` (console script) or `python -m market_research.cli`.
`--product/-p <category>` or interactive prompt. `--skip-image` for fast/cheap
dev iteration (skips HF image gen + that agent's LLM call).

## Architecture (bottom-up dependency order)

```
config.py            env vars (.env via dotenv), model constants, PROJECT_ROOT, DEFAULT_CATALOG_PATH
state.py             PipelineState — TypedDict(total=False), all pipeline data flows through this
llm.py               ALL Gemini calls go through here: generate() / generate_text() / generate_json()
catalog_builder.py   on-demand catalog build from raw Amazon data (see below) -- NOT under tools/
tools/
  catalog.py         product_catalog_tool (LLM-callable) + load_catalog + available_categories (DEAD CODE, see Known issues)
  search.py          tavily_search_tool (LLM-callable)
  __init__.py        TOOL_FUNCTIONS registry, get_tools(), call_tool() dispatch
image_gen/hf_image.py   HF InferenceClient, FLUX.1-schnell
agents/
  market_research.py   LangGraph SUBGRAPH: call_model <-> call_tools ReAct loop. System prompt built
                        per-request from state["product_category"] via _system_instruction().
  graphic_designer.py   trend_summary -> (prompt, caption) via Gemini JSON -> image via HF. Honors skip_image.
  copywriter.py         (image + trend_summary) -> (quote, justification), multimodal Gemini call.
  packaging.py          -> markdown report. CATEGORY_EMOJI dict picks header emoji per category.
graph.py              wires the 4 agents into one StateGraph; run_campaign_pipeline(product_category, skip_image)
cli.py                typer entrypoint. Shows top-30 categories, prompts, calls
                       catalog_builder.ensure_category_in_catalog() before running the pipeline.
```

`data/catalog.csv` — committed to git, 6,200 rows / 31 real categories (seeded).
`data/raw/` — gitignored, NOT portable. 24GB total: `meta_Clothing_Shoes_and_Jewelry.jsonl`
(18GB, the actual Amazon dataset) + `by_category/` (6.8GB of per-category filtered pools + `.meta.json`
fingerprint files, one pair per cached category).
`data/category_index.json` — gitignored, cache of {category: count} + raw-file fingerprint.
`data/catalog.*.csv.bak` — 3 historical snapshots from iterating on the catalog approach
(original 5-row hand-written, sunglasses-only-45-row, old-regex-based-1000-row). Gitignored,
safe to delete, kept only in case of "wait go back" requests.
`study/` — original DeepLearning.AI notebook prototype, reference only, unused by `src/`.

## Key architectural decisions (why, not just what)

1. **`google-genai` SDK directly, not `aisuite`.** `aisuite`'s `google:` provider needs Vertex AI
   (GCP service account), not a plain Gemini Developer API key (what's available). Its pinned
   `httpx<0.28` also blocked the SDK version needed for `thought_signature` (multi-turn
   function-calling requires it; omitting → `400 INVALID_ARGUMENT`).
2. **Image gen via Hugging Face (`black-forest-labs/FLUX.1-schnell`), not Gemini.** Gemini image
   models returned `429 RESOURCE_EXHAUSTED` on the free tier regardless of client — needs GCP
   billing enabled, deliberately not done.
3. **`TEXT_MODEL` defaults to `gemini-flash-lite-latest`**, not `-latest` (which resolves to
   `gemini-3.8-flash`, 20 req/day free-tier cap — exhausted mid-dev). Override via
   `MARKET_RESEARCH_TEXT_MODEL`. Always use `-latest` aliases, never dated model names (they rot —
   `gemini-2.5-flash` already retired).
4. **`llm.generate()` retries on `ServerError` (503)** — Gemini genuinely returns intermittent
   "high demand" 503s, including back-to-back identical requests. 4 attempts, linear backoff.
5. **`automatic_function_calling` disabled** in `llm.py`'s config — the ReAct loop in
   `agents/market_research.py` executes tool calls itself; the SDK's auto-calling would conflict.
6. **Catalog categories come from the raw data's `categories[-1]` breadcrumb leaf**, not
   hand-written regex/keyword rules. First attempt (session 2) used regex per category
   (`\bshoe\b|\bsneaker\b|...`) — worked but had false positives (a *sock* matched "shoes" via
   "Heel Tab" in its title) and only covered 5 hand-picked categories. Switching to the real
   `categories` breadcrumb's last element gave a clean, exact, zero-maintenance taxonomy with
   638 real categories, for free, straight from the data.
7. **On-demand + cached, not "build everything upfront."** Category index built once (full scan,
   ~1-2 min locally), top 30 pre-seeded, everything else builds on first request (~1-2 min, one
   scan of the raw file) and is cached from then on (<1s). This is the whole point of "any
   product category" without needing to know categories in advance.
8. **Fingerprint-based staleness (size+mtime per raw file), not TTL or manual invalidation.**
   Cheap to check every run (just `stat()`), auto-rebuilds only what's actually stale. Verified
   live: added a fake raw file with a new category → correctly detected + rebuilt; removed it →
   correctly purged.
9. **Multi-file: scans `data/raw/*.jsonl` (glob), not one hardcoded filename.** Dropping a new
   raw file into that folder is picked up automatically next time the index/a pool goes stale.
10. **Brand cap (max 5/category) + quality filters (rating_count≥25, rating≥3.5, desc≥40 chars,
    price present)** when curating a category — avoids one brand flooding results, verified via
    a live test with fake single-brand data.
11. **Noise blocklist for leaf categories**: `westlake`, `women`, `men`, `girls`, `boys`,
    `unisex`, `casual`, `sets`, `clothing`, `costumes`, `novelty`, `other`, `accessories`,
    `fashion` — these are miscategorized/incomplete breadcrumbs (e.g. `["Clothing, Shoes &
    Jewelry", "Westlake"]` on completely unrelated products — some kind of catch-all seller
    bucket, not a real product type), not genuine categories. Found by manually inspecting the
    top-60 raw counts; there may be more lurking further down the list — not exhaustively swept.

## Known issues / gotchas

- **pyright gives false `reportMissingImports` unless run with
  `pyright --pythonpath .venv/bin/python <file>`.** Without that flag it doesn't resolve the
  venv and flags `typer`/`rich`/`google.genai`/etc. as unresolved. Always use the explicit flag
  when checking this project. (No `pyrightconfig.json` exists to fix this permanently — could add
  one, not done.)
- **`PipelineState` is `TypedDict(total=False)`** — every key is optional to the type checker.
  Always use `.get(key, default)`, never `state[key]`, or pyright raises
  `reportTypedDictNotRequiredAccess`. Exception: literal dict construction assigned to a
  `PipelineState`-annotated variable (e.g. in `graph.py`) is fine structurally.
- **`google-genai`'s `FunctionDeclaration.parameters` needs `types.Schema` objects with the
  `types.Type` enum** (`types.Type.STRING`, not `"string"`), NOT raw dicts with string literals.
  This is different from `generate()`/`generate_json()`'s `response_schema` param, which DOES
  accept a plain dict (different validation path in the SDK) — don't conflate the two.
- **`data/raw/` is gitignored and 24GB — not portable.** A fresh clone has the 31 categories
  already in `catalog.csv` (committed) but can't build any *new* category on-demand without
  first downloading `meta_Clothing_Shoes_and_Jewelry.jsonl` from
  `McAuley-Lab/Amazon-Reviews-2023` on Hugging Face and placing it at `data/raw/`. This isn't
  documented anywhere yet as a setup step for on-demand expansion — README should mention it.
- **`tools/catalog.py`'s `available_categories()` is dead code** — was used by an earlier CLI
  iteration, superseded by `catalog_builder.top_categories()`. Never called now. Safe to delete,
  not done yet (low priority).
- **No automated tests exist** — deliberate scope decision from v1, carried forward. Verification
  = pyright + manual real-API runs, checked by hand.
- **A `ScheduleWakeup` prompt kept re-arriving verbatim as user messages** many times during the
  session-2 build (after the referenced background job had long finished, with no active
  cron/loop per `CronList`/`ScheduleWakeup(stop)`). Filed as product feedback (drafted, not a
  codebase issue) — mentioned here only so a future session isn't confused if it recurs.
- **Only 3 raw source categories have been spot-checked for noise** (top 60 by frequency) — if a
  newly on-demand-built category returns weird/junk products, check whether its leaf name is
  actually a real product type or another miscategorized bucket like `Westlake`.

## Conventions

- All Gemini calls go through `llm.py` — never call `google.genai` directly from an agent module.
- Comments: WHY only, never WHAT (identifiers should make WHAT obvious). No narrative/teaching
  comments — that's for chat, not the codebase. One-line docstrings on public functions.
- Category names: matched case-insensitively everywhere, but stored/displayed in their real-world
  casing exactly as Amazon's data has them (`"T-Shirts"`, `"Wrist Watches"`), never lowercased for
  display.
- Backup/snapshot files: `data/*.csv.bak` suffix, gitignored, never deleted automatically.
- `.env` needs `GOOGLE_API_KEY` (plain Gemini Developer key, not Vertex), `TAVILY_API_KEY`,
  `HF_TOKEN`. All confirmed live/working as of last real run.
- Dependency management: `uv pip install -e .`. Python 3.14, `.venv` at project root.

## Next steps (nothing currently broken or mid-implementation)

- Not started, no commitment made: deleting dead `available_categories()`; adding a
  `pyrightconfig.json` to fix the interpreter-resolution gotcha permanently; documenting the
  raw-data download step for fresh clones; broader noise-blocklist sweep beyond top-60;
  deciding whether to commit or push to a remote.
- If asked to add a new product-adjacent data domain (e.g. Electronics) beyond what
  `meta_Clothing_Shoes_and_Jewelry.jsonl` covers: just drop the new raw `.jsonl` into `data/raw/`
  — multi-file support means it's picked up automatically, no code changes needed.
