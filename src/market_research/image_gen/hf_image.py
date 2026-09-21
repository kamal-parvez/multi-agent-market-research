"""Image generation via the Hugging Face Inference API."""
from pathlib import Path

from huggingface_hub import InferenceClient

from market_research.config import HF_TOKEN, IMAGE_MODEL, require_keys

_client: InferenceClient | None = None


def get_client() -> InferenceClient:
    """Lazily construct and cache the Hugging Face Inference client."""
    global _client
    if _client is None:
        require_keys("HF_TOKEN")
        _client = InferenceClient(api_key=HF_TOKEN)
    return _client


def generate_image(prompt: str, output_path: Path, model: str = IMAGE_MODEL) -> Path:
    """Generate an image from `prompt` and save it to `output_path`."""
    image = get_client().text_to_image(prompt, model=model)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path
