**Multi Agent Market Research**

This project is a four agent pipeline that researches fashion trends for any product category, not only sunglasses, and turns that research into a marketing campaign ready for review. A single run produces a trend analysis, a generated campaign image, a marketing quote, and an executive summary report.

The pipeline is built with LangGraph (https://github.com/langchain-ai/langgraph) as a real state graph orchestrator rather than a script of chained function calls. It uses Google Gemini for text reasoning, Hugging Face for image generation, and Tavily for live web search. Product data comes from a real Amazon product dataset rather than a small set of sample rows written by hand.

**How it works**

Four agents run in sequence, and each one reads from and writes to a shared pipeline state.

1. Market Research. This agent repeatedly calls Gemini and lets it request tool calls, such as a web search through Tavily or a lookup against the internal product catalog, until it produces a trend summary for whatever product category was requested. This loop is often called the ReAct pattern, meaning the model alternates between reasoning about what to do next and acting on that decision through a tool.
2. Graphic Designer. This agent turns the trend summary into an image generation prompt and a caption, then generates a campaign image using Hugging Face and the FLUX.1 schnell model.
3. Copywriter. This agent looks at both the generated image and the trend summary together, a technique known as multimodal input, and writes a short campaign quote along with a justification for why that quote fits.
4. Packaging. This agent rewrites the trend summary for an executive audience and assembles everything produced so far into a markdown report.

**Setup**

This project requires Python 3.11 or newer and API keys for Google Gemini, Tavily, and Hugging Face.

Dependencies are managed with uv. If uv is not already installed, follow the instructions at https://docs.astral.sh/uv/getting-started/installation/, or use a standard virtual environment with pip instead by substituting pip install for uv pip install in the steps below.

First, create and activate a virtual environment from the project root.

```bash
uv venv
source .venv/bin/activate
```

Then install the project in editable mode.

```bash
uv pip install -e .
```

Once installed, the market-research command described in the Usage section becomes available inside this virtual environment.

Next, create a file named .env in the project root with the following three keys.

```env
GOOGLE_API_KEY=your-gemini-developer-api-key
TAVILY_API_KEY=your-tavily-api-key
HF_TOKEN=your-huggingface-token
```

The Gemini key should be a plain Gemini Developer API key from Google AI Studio at https://aistudio.google.com/, not a Vertex AI service account credential. The Tavily key can be obtained from https://tavily.com/. The Hugging Face token can be created at https://huggingface.co/settings/tokens and needs Inference API access enabled.

**Usage**

Running the command with no arguments shows the most common available product categories and then prompts for one.

```bash
market-research
```

The category can also be given directly on the command line.

```bash
market-research --product "Sunglasses"
market-research -p "T-Shirts"
```

Image generation is the slowest step and the one most likely to run into API quota limits, so it can be skipped for faster iteration during development.

```bash
market-research --skip-image
```

Here is an example run.

```
$ market-research --product "Watches" --skip-image
Popular categories: T-Shirts, Shoes, Fashion Sneakers, Wrist Watches, Flats, ...

Running market research on 'Watches'...

Pipeline complete.
Quote: Timeless retro design meets everyday versatility for the modern era.
Report: output/campaign_summary_2026-09-21_00-54-51.md
```

The "Popular categories" list shown at startup and in this example comes from the product catalog described below. Every run writes a markdown report to the output folder, and also writes a generated campaign image there unless the skip image flag was used.

**The product catalog**

Product data is real. It is sourced from McAuley-Lab/Amazon-Reviews-2023 on Hugging Face (https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023), a public academic dataset built from real Amazon product listings. Categories are taken directly from each product's own category information rather than from keyword rules written for this project. Products are then filtered for quality. Each one must have a real price, a meaningful description, at least 25 ratings, and a rating of 3.5 or higher, and no more than five items from the same brand are kept per category, so the results stay varied.

The file data/catalog.csv ships with the project and already contains 31 of the most common categories in the dataset, including T-Shirts, Shoes, Sunglasses, Wrist Watches, and Dresses, along with 200 curated products in each. The application is not limited to these 31 categories. Typing any other product category name at the prompt works as well, as long as it is a real category found in the underlying dataset. The first time a new category is requested, the application builds and caches a curated product list for it, which typically takes one to two minutes. Every request after that for the same category is instant. If the category entered is not recognized at all, the pipeline still runs. It simply skips the catalog matching step and relies on web research alone.

To let the application build categories beyond the 31 that ship by default, download the raw dataset file and place it at data/raw/meta_Clothing_Shoes_and_Jewelry.jsonl. This file is large, currently about 18 gigabytes.

```bash
curl -L -o data/raw/meta_Clothing_Shoes_and_Jewelry.jsonl \
  "https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023/resolve/main/raw/meta_categories/meta_Clothing_Shoes_and_Jewelry.jsonl"
```

Without this file, the application still works fully for the 31 categories that already ship in data/catalog.csv. It simply cannot expand beyond them.

**Project structure**

```
src/market_research/
├── config.py              environment variables, model constants, and paths
├── state.py               PipelineState, the shared state passed between graph nodes
├── llm.py                 every Gemini call in the project goes through this module
├── catalog_builder.py     builds and caches the product catalog on demand from raw data
├── tools/
│   ├── catalog.py         the product catalog tool available to the research agent
│   ├── search.py          the Tavily web search tool available to the research agent
│   └── __init__.py        registry of available tools
├── image_gen/
│   └── hf_image.py        Hugging Face image generation
├── agents/
│   ├── market_research.py    the ReAct style tool calling research agent
│   ├── graphic_designer.py   produces an image prompt and caption, then the image itself
│   ├── copywriter.py         produces the campaign quote from the image and trend summary
│   └── packaging.py          produces the final markdown executive report
├── graph.py               wires the four agents together into one LangGraph pipeline
└── cli.py                 the command line entry point

data/
├── catalog.csv            the curated product catalog, committed to the repository (6,200 rows across 31 categories)
├── category_index.json    a generated cache of available categories, not committed
└── raw/                   the raw Amazon dataset and per category derived pools, not committed and roughly 24 gigabytes

study/                     the original prototype notebook, kept only as reference and not used by src/
```

The project root also contains pyproject.toml, which defines the package and its dependencies, and a .env file that each user creates locally as described in Setup. The output folder mentioned in Usage is created automatically the first time the pipeline runs.

**Troubleshooting**

If a run fails immediately with a message about a missing environment variable, the .env file described in Setup is either missing or missing one of the three required keys.

Gemini occasionally returns a temporary server error under high demand. The project already retries these automatically, so an occasional delay before a response is expected behavior rather than a bug.

Anyone using an editor with Pyright or Pylance for type checking should point it at the project's own virtual environment interpreter. Running Pyright against this project without doing so will report missing imports for packages such as typer, rich, and google.genai even though they are installed, because it is resolving against the wrong Python environment rather than the project's own.

**Notes**

There are no automated tests in this project. Verification has been done through real end to end runs against the live Gemini, Tavily, and Hugging Face APIs, checked by hand.

**License**

There is no license file in this repository yet. Until one is added, the project should be treated as all rights reserved.
