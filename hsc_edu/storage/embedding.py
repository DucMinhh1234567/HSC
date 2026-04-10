"""Gemini embedding client with batching and retry."""

from __future__ import annotations

import logging
import os
import time

from google import genai
from google.genai import types

from hsc_edu.config.settings import settings

logger = logging.getLogger(__name__)

_CLIENT: genai.Client | None = None


def _get_client() -> genai.Client:
    global _CLIENT  # noqa: PLW0603
    if _CLIENT is None:
        api_key = os.environ.get(settings.embedding.api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"Environment variable {settings.embedding.api_key_env!r} is not set. "
                "Please add your Gemini API key to .env"
            )
        _CLIENT = genai.Client(api_key=api_key)
    return _CLIENT


def embed_texts(
    texts: list[str],
    *,
    task_type: str = "RETRIEVAL_DOCUMENT",
    max_retries: int = 3,
) -> list[list[float]]:
    """Embed a list of texts using the Gemini embedding model.

    Parameters
    ----------
    texts:
        Texts to embed.
    task_type:
        ``"RETRIEVAL_DOCUMENT"`` for indexing chunks, or
        ``"RETRIEVAL_QUERY"`` for query embedding.
    max_retries:
        Number of retries on transient errors (rate-limit, timeout).

    Returns
    -------
    list[list[float]]
        One embedding vector per input text.
    """
    if not texts:
        return []

    cfg = settings.embedding
    client = _get_client()
    batch_size = cfg.batch_size
    inter_batch_delay = cfg.embed_batch_delay_sec
    all_vectors: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]

        for attempt in range(1, max_retries + 1):
            try:
                result = client.models.embed_content(
                    model=cfg.model_name,
                    contents=batch,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=cfg.dimensions,
                    ),
                )
                all_vectors.extend(e.values for e in result.embeddings)
                break
            except Exception as exc:
                if attempt == max_retries:
                    raise
                exc_l = str(exc).lower()
                is_rate = (
                    "429" in str(exc)
                    or "resource_exhausted" in exc_l
                    or "quota" in exc_l
                    or "rate" in exc_l
                )
                # Free tier often needs longer backoff than 2s/4s for 429.
                if is_rate:
                    wait = min(120, 15 * (2 ** (attempt - 1)))
                else:
                    wait = min(60, 2 ** attempt)
                logger.warning(
                    "Embedding batch %d–%d failed (attempt %d/%d): %s. "
                    "Retrying in %ds…",
                    start, start + len(batch), attempt, max_retries,
                    exc, wait,
                )
                time.sleep(wait)

        if start + batch_size < len(texts):
            time.sleep(inter_batch_delay)

    logger.info(
        "Embedded %d texts → %d vectors (dim=%d, model=%s)",
        len(texts), len(all_vectors), cfg.dimensions, cfg.model_name,
    )
    return all_vectors


def embed_query(query: str) -> list[float]:
    """Embed a single query string for retrieval search."""
    vectors = embed_texts([query], task_type="RETRIEVAL_QUERY")
    return vectors[0]
