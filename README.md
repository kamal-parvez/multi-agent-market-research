# Multi-Agent Market Research — Project Context

This file exists so a new chat session (or anyone else) can pick up this project
without re-deriving everything from scratch. If you're Claude starting fresh:
read this whole file before touching code.

## What this project is

A rebuild of the DeepLearning.AI lab notebook in `study/M5_UGL_2.ipynb` — a
4-agent pipeline that researches sunglasses fashion trends, generates a
campaign image, writes a marketing quote, and packages everything into an
executive markdown report — as a **from-scratch, plain-Python, CLI-driven
package**, replacing the notebook's hand-chained function calls with a real
**LangGraph** orchestrator (explicit state graph, conditional edges, a proper
tool-calling loop).

The full plan (with all the reasoning behind each decision) lives at:
`/Users/kamalparvez/.claude/plans/cuddly-drifting-honey.md` — read that too if
it still exists; it has more detail than this file.

## Status: v1 build complete and working

All 6 build steps done, tested end-to-end via real runs (not just unit
tests — actual Gemini/HF/Tavily API calls). Git repo initialized at project
root, `main` branch, one initial commit (`26b9096`) containing everything
except `.env`, `.venv/`, `output/`, `__pycache__/` (see `.gitignore`).

Run it: `market-research` (installed as a console script; or
`python -m market_research.cli`) — runs the full pipeline. `--skip-image`
flag skips image generation for cheap/fast dev iteration.

## Architecture

```
src/market_research/
├── config.py           # env vars (.env), model name constants, paths
├── state.py             # PipelineState TypedDict — shared state across graph nodes
├── llm.py                # ALL Gemini calls go through here (generate/generate_text/generate_json)
├── tools/
│   ├── catalog.py        # reads data/catalog.csv
│   ├── search.py         # Tavily web search
│   └── __init__.py       # tool registry: get_tools() + call_tool() dispatch
├── image_gen/
│   └── hf_image.py       # Hugging Face FLUX.1-schnell image generation
├── agents/
│   ├── market_research.py    # LangGraph SUBGRAPH: ReAct tool-calling loop (call_model <-> call_tools)
│   ├── graphic_designer.py   # prompt+caption (Gemini JSON) -> image (HF)
│   ├── copywriter.py         # multimodal (image+text) -> quote+justification
│   └── packaging.py          # -> markdown report
├── graph.py              # wires the 4 agents into one StateGraph, START->...->END
└── cli.py                # typer entrypoint

data/catalog.csv          # 5 hardcoded sunglasses SKUs (moved out of Python code)
study/                    # the ORIGINAL notebook + its helper .py files — reference only, not used by src/
```

Reading order for code review (bottom-up, dependency order): `config.py` →
`state.py` → `llm.py` → `tools/catalog.py` + `tools/search.py` →
`tools/__init__.py` → `agents/market_research.py` (the meaty one) →
`agents/graphic_designer.py` → `agents/copywriter.py` → `agents/packaging.py`
→ `graph.py` → `cli.py`.

## Key architectural decisions (and why — these were NOT the original plan)

The original plan was "use `aisuite` for multi-provider LLM flexibility,
Gemini for text, Gemini native image-gen." Both parts changed after hitting
real integration problems, verified against the user's actual API keys:

1. **Dropped `aisuite` entirely.** Its `google:` provider only supports
   Vertex AI (GCP project + service-account credentials), not a plain Gemini
   Developer API key, which is what the user has. Later, `aisuite`'s pinned
   `httpx<0.28` also blocked installing a `google-genai` SDK version new
   enough to support `thought_signature` (a field the current Gemini API
   requires for multi-turn function-calling — omitting it causes a
   `400 INVALID_ARGUMENT`). All Gemini calls now go through the raw
   `google-genai` SDK directly, wrapped in `llm.py`.
2. **Image generation uses Hugging Face (`black-forest-labs/FLUX.1-schnell`
   via `huggingface_hub.InferenceClient`), not Gemini.** Gemini's image
   models returned `429 RESOURCE_EXHAUSTED` (0 free-tier quota) regardless
   of client library — needs billing enabled on that Google Cloud project,
   which the user didn't want to do yet.
3. **`TEXT_MODEL` defaults to `gemini-flash-lite-latest`, not
   `gemini-flash-latest`.** The non-lite alias currently resolves to
   `gemini-3.8-flash`, whose free tier caps out at 20 requests/day —
   exhausted mid-development in a single session. Override via the
   `MARKET_RESEARCH_TEXT_MODEL` env var once billing is enabled.
4. **`llm.py`'s `generate()` retries on `ServerError` (503).** Gemini
   returned intermittent "high demand" 503s repeatedly during dev, including
   on identical back-to-back requests — genuinely observed, not
   hypothetical. 4 attempts, linear backoff.
5. **Model names need the `-latest` alias, not dated names.** Verified
   `gemini-2.5-flash` (a name from Claude's training data) is already
   retired for new callers; the API redirects you to whatever's current.
   Hardcoding dated model names will rot.
6. **`automatic_function_calling` is explicitly disabled** in `llm.py`'s
   config. We execute function/tool calls ourselves in
   `agents/market_research.py`'s ReAct loop; the SDK has its own
   auto-calling feature that would otherwise conflict/warn.

## `.env` keys needed

`.env.example` was removed from the repo (deliberate — kept out of the
GitHub publication). Required keys, set directly in a local `.env`:

- `GOOGLE_API_KEY` — plain Gemini Developer API key (not Vertex/GCP service account)
- `TAVILY_API_KEY` — web search
- `HF_TOKEN` — Hugging Face Inference API, for image generation

All three are confirmed working live as of this build (tested with real
calls, not just code review).

## Comment cleanup for GitHub publication — done

The user reviewed the code file-by-file before pushing to GitHub and asked
for comments to be trimmed to **concise, professional** style — not
narrative/teaching explanations (that's what chat is for). One-line
docstrings were added to previously-undocumented public functions across
`llm.py`, `image_gen/hf_image.py`, `tools/__init__.py`,
`agents/market_research.py`, `agents/graphic_designer.py`,
`agents/copywriter.py`, `agents/packaging.py`, and `graph.py`.

Note: `config.py`'s `require_keys` docstring and `state.py`'s comment on
`messages: list[Any]` (explaining why it's typed `Any`) were trimmed/removed
during the earlier manual pass and were left as-is by user decision — not
re-added.

## Known environment quirk (previously seen, since resolved)

Partway through the comment-cleanup pass in an earlier session, all file
access (Read tool, Edit tool, and even plain `cat`/`ls` via Bash — with
sandbox explicitly disabled too) to the project directory started failing
with `EPERM: operation not permitted`, eventually spreading from
`src/market_research/` to the project root itself. The user confirmed
*they* could read the same files fine in their own editor at the same
time — so it wasn't a real permissions/corruption issue on the files, it
was specific to whatever process executed that session's tool calls.
Leading theory: a security/EDR tool on the user's Mac flagged the bulk
file creation/editing earlier in the build (a dozen+ files written in
quick succession into a brand-new directory) as suspicious process
behavior and restricted that process's filesystem access.

Confirmed resolved as of the next session (file read/write/bash all work
normally again). **If it recurs:** tell the user plainly, ask them to
check their security software's logs/quarantine, and retry after some
time has passed — don't burn many turns re-diagnosing it, since it was
already investigated at length (ruled out: file-specific permissions/
ACLs/flags, sandbox-specific issue, content-pattern-based blocking like
filenames containing "config" or the string "API_KEY").

## Other things worth knowing

- Python 3.14 (`.venv` in project root), dependency management via `uv`
  (`uv pip install -e .`).
- `pyproject.toml` uses PEP 621 + hatchling, src-layout, console-script
  entry point `market-research`.
- No automated tests exist — this was a deliberate scope decision (v1
  verification = manual runs producing real output, checked by hand).
  Documented in the plan file's Verification section.
- `study/` directory is the original notebook/prototype — read-only
  reference, not imported by anything in `src/`.
