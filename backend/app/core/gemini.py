from google import genai

from app.config import settings
from app.core.tracked_gemini import TrackedClient

LIVE_MODEL = settings.gemini_live_model
STANDARD_MODEL = settings.gemini_standard_model
IMAGE_MODEL = settings.gemini_image_model
EMBEDDING_MODEL = settings.gemini_embedding_model

_client_cache: dict[str, genai.Client] = {}


def get_genai_client(api_key: str | None = None) -> TrackedClient:
    """Return a cached GenAI client using the provided API key.

    Raises ValueError if no key is provided — all callers must supply a
    user-owned key; there is no fallback to shared project credentials.
    """
    if not api_key:
        raise ValueError("A Gemini API key is required. Add one in Settings.")
    if api_key not in _client_cache:
        client = genai.Client(api_key=api_key)
        _client_cache[api_key] = client
    return TrackedClient(_client_cache[api_key])
