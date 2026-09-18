"""Thin wrapper around the google-genai SDK, shared by all agents."""
import json
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from market_research.config import GOOGLE_API_KEY, TEXT_MODEL, require_keys

_client: genai.Client | None = None

# The Gemini backend intermittently returns 503 "high demand" for otherwise
# valid requests (observed repeatedly during development, including on
# identical back-to-back requests) -- retry with backoff before giving up.
MAX_RETRIES = 4
RETRY_BACKOFF_SECONDS = 2.0


def get_client() -> genai.Client:
    global _client
    if _client is None:
        require_keys("GOOGLE_API_KEY")
        _client = genai.Client(api_key=GOOGLE_API_KEY)
    return _client


def generate(
    contents,
    *,
    tools: list[types.Tool] | None = None,
    system_instruction: str | None = None,
    model: str = TEXT_MODEL,
    response_mime_type: str | None = None,
    response_schema: dict | None = None,
) -> types.GenerateContentResponse:
    """Single call to Gemini, optionally with tools, a system instruction, and/or
    a structured JSON output schema.

    Retries on transient 503 ServerError responses (see MAX_RETRIES above).
    """
    config = types.GenerateContentConfig(
        tools=tools,
        system_instruction=system_instruction,
        response_mime_type=response_mime_type,
        response_schema=response_schema,
        # We execute function calls ourselves (see agents/market_research.py's
        # ReAct loop); disable the SDK's automatic function calling so it
        # doesn't try to intercept them itself.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    client = get_client()

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except genai_errors.ServerError as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise last_error


def generate_text(prompt: str, *, system_instruction: str | None = None, model: str = TEXT_MODEL) -> str:
    """Convenience wrapper for a single-turn text-only call."""
    return generate(prompt, system_instruction=system_instruction, model=model).text


def generate_json(
    prompt: str,
    schema: dict,
    *,
    system_instruction: str | None = None,
    model: str = TEXT_MODEL,
) -> dict:
    """Single-turn call constrained to return JSON matching `schema`."""
    response = generate(
        prompt,
        system_instruction=system_instruction,
        model=model,
        response_mime_type="application/json",
        response_schema=schema,
    )
    return json.loads(response.text)
