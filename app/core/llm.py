from google import genai
from google.genai import types

from app.core.config import settings

_client = genai.Client(api_key=settings.gemini_api_key)


def embed(text: str) -> list[float]:
    """Turn text into a vector of numbers that captures its meaning."""
    result = _client.models.embed_content(
        model=settings.gemini_embed_model,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=settings.embed_dim),
    )
    return result.embeddings[0].values


def chat(prompt: str) -> str:
    """Send a prompt to the chat model and return its text answer."""
    result = _client.models.generate_content(
        model=settings.gemini_chat_model,
        contents=prompt,
    )
    return result.text