"""Gemini LLM client for text generation with retry."""

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
        api_key = os.environ.get(settings.llm.api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"Environment variable {settings.llm.api_key_env!r} is not set. "
                "Please add your Gemini API key to .env"
            )
        _CLIENT = genai.Client(api_key=api_key)
    return _CLIENT


def generate_text(
    system_prompt: str,
    user_prompt: str,
    *,
    json_output: bool = True,
    max_retries: int = 3,
) -> str:
    """Call the Gemini LLM and return the generated text.

    Parameters
    ----------
    system_prompt:
        System instruction for the model.
    user_prompt:
        User message / main prompt.
    json_output:
        If True, requests ``application/json`` response MIME type.
    max_retries:
        Number of retries on transient errors.

    Returns
    -------
    str
        Raw text from the model response.
    """
    cfg = settings.llm
    client = _get_client()

    gen_config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=cfg.temperature,
        max_output_tokens=cfg.max_output_tokens,
    )
    if json_output:
        gen_config.response_mime_type = "application/json"

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=cfg.model_name,
                contents=user_prompt,
                config=gen_config,
            )
            text = response.text or ""
            logger.info(
                "LLM generated %d chars (model=%s, attempt=%d)",
                len(text), cfg.model_name, attempt,
            )
            return text
        except Exception as exc:
            if attempt == max_retries:
                raise
            exc_s = str(exc).lower()
            is_rate = any(kw in exc_s for kw in ("429", "resource_exhausted", "quota", "rate"))
            wait = min(120, 15 * (2 ** (attempt - 1))) if is_rate else min(60, 2 ** attempt)
            logger.warning(
                "LLM call failed (attempt %d/%d): %s. Retrying in %ds…",
                attempt, max_retries, exc, wait,
            )
            time.sleep(wait)

    return ""
