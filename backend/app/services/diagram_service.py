"""Diagram Service — Gemini image generation + local media upload.

Generates educational diagrams (flowcharts, comparisons, formulas, etc.)
via `gemini-2.5-flash-image` and stores the result in local media at:
  diagrams/{artifactId}/{uuid}.png

Per agent-prompts.md §local media paths.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from google.genai import types as genai_types

from app.config import settings
from app.core.gemini import IMAGE_MODEL, get_genai_client
from app.core.local_media import save_media

logger = logging.getLogger(__name__)

# Default 3D position for generated diagrams in the palace view
_DEFAULT_POSITION = {"x": 2.5, "y": 1.8, "z": -2.0}


@dataclass
class DiagramResult:
    url: str
    caption: str
    position: dict = field(default_factory=lambda: dict(_DEFAULT_POSITION))


async def generate_diagram(
    description: str,
    caption: str,
    artifact_id: str,
    position: Optional[dict] = None,
    api_key: str | None = None,
) -> DiagramResult:
    """Generate a diagram image and upload it to local media."""
    prompt = _build_prompt(description, caption)
    image_bytes = await _generate_image(prompt, api_key=api_key)

    diagram_id = uuid.uuid4().hex
    blob_path = f"diagrams/{artifact_id}/{diagram_id}.png"
    url = await _upload_to_storage(image_bytes, blob_path)

    result = DiagramResult(
        url=url,
        caption=caption,
        position=position or dict(_DEFAULT_POSITION),
    )
    logger.info(
        "Diagram generated: artifactId=%s url=%s captionLen=%d",
        artifact_id, url, len(caption),
    )
    return result


# ── Private helpers ────────────────────────────────────────────────────────────

def _build_prompt(description: str, caption: str) -> str:
    return (
        f"Create a clear, clean educational diagram titled '{caption}'. "
        f"{description}. "
        "Use a white background. "
        "Make it visually professional with clear labels. "
        "Keep it concise and easy to understand at a glance."
    )


async def _generate_image(prompt: str, api_key: str | None = None) -> bytes:
    """Call Gemini image generation and return PNG bytes."""
    client = get_genai_client(api_key)
    response = await client.aio.models.generate_content(
        model=IMAGE_MODEL,
        contents=[prompt],
        config=genai_types.GenerateContentConfig(
            response_modalities=["Text", "Image"],
        ),
    )
    for part in response.parts:
        if part.inline_data is not None:
            return part.inline_data.data
    raise ValueError("No image returned from Gemini image model")


async def _upload_to_storage(image_bytes: bytes, blob_path: str) -> str:
    """Upload PNG bytes to local media and return the public URL."""
    return await save_media(image_bytes, blob_path)
