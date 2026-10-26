"""The only module that talks to Gemini. Everything else calls these functions."""
import time
from collections.abc import Callable
from typing import TypeVar

from google import genai
from google.genai import errors, types

from app.core.config import settings

_client = genai.Client(api_key=settings.gemini_api_key)

EMBED_BATCH_SIZE = 50
RETRYABLE_CODES = {429, 500, 503}
MAX_ATTEMPTS = 5

T = TypeVar("T")


def _with_retries(call: Callable[[], T]) -> T:
    """Run an API call, retrying politely when the free tier rate-limits us."""
    for attempt in range(MAX_ATTEMPTS):
        try:
            return call()
        except errors.APIError as exc:
            if exc.code not in RETRYABLE_CODES or attempt == MAX_ATTEMPTS - 1:
                raise
            wait = 5 * 2**attempt  # 5s, 10s, 20s, 40s
            print(f"  Gemini returned {exc.code}; retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def _embed_batch(texts: list[str], task_type: str) -> list[list[float]]:
    result = _with_retries(
        lambda: _client.models.embed_content(
            model=settings.gemini_embed_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=settings.embed_dim,
            ),
        )
    )
    return [e.values for e in result.embeddings]


def embed_many(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Embed many texts (used when ingesting documents)."""
    vectors: list[list[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        vectors.extend(_embed_batch(texts[start : start + EMBED_BATCH_SIZE], task_type))
    return vectors


def embed(text: str, task_type: str = "RETRIEVAL_QUERY") -> list[float]:
    """Embed one text. Defaults to 'query' mode, which is what a search question needs."""
    return _embed_batch([text], task_type)[0]


def chat(prompt: str) -> str:
    """Send a prompt to the chat model and return its text answer."""
    result = _with_retries(
        lambda: _client.models.generate_content(
            model=settings.gemini_chat_model,
            contents=prompt,
        )
    )
    return result.text or ""
