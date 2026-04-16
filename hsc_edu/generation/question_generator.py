"""Question generator — hybrid chunk selection + LLM generation."""

from __future__ import annotations

import json
import logging
import random
import time
from typing import Any

from pydantic import BaseModel, Field

from hsc_edu.core.models import Chunk
from hsc_edu.generation.llm_client import generate_text
from hsc_edu.generation.prompts import build_prompt
from hsc_edu.storage.mongo_store import MongoChunkStore
from hsc_edu.storage.retrieval import retrieve_chunks

logger = logging.getLogger(__name__)

_INTER_CHAPTER_DELAY = 5.0


class GeneratedQuestion(BaseModel):
    """A single generated exam question with metadata."""

    question: str
    suggested_answer: str
    difficulty: str = ""
    source: str = ""
    bloom_level: str = ""
    keywords: list[str] = Field(default_factory=list)
    subject: str = ""
    chapter: str = ""
    chunk_ids: list[str] = Field(default_factory=list)


def _select_chunks(
    subject: str,
    chapter: str,
    max_context_chunks: int,
    query: str,
    mongo: MongoChunkStore,
) -> list[Chunk]:
    """Hybrid chunk selection: filter → sample/semantic."""
    if query:
        results = retrieve_chunks(
            query, subject=subject, chapter=chapter, top_k=max_context_chunks,
        )
        chunks = [ch for ch, _ in results]
        if chunks:
            return chunks

    all_chunks = mongo.get_chunks_by_filter(subject=subject, chapter=chapter)
    all_chunks = [c for c in all_chunks if c.token_count >= 30]

    if not all_chunks:
        return []

    all_chunks.sort(key=lambda c: c.page_start)

    if len(all_chunks) <= max_context_chunks:
        return all_chunks

    return random.sample(all_chunks, max_context_chunks)


def _parse_questions(raw: str, subject: str, chapter: str, chunk_ids: list[str]) -> list[GeneratedQuestion]:
    """Parse LLM JSON output into validated GeneratedQuestion objects."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM output as JSON: %.200s…", raw)
        return []

    if isinstance(data, dict):
        data = [data]

    if not isinstance(data, list):
        logger.error("LLM output is not a JSON array: %s", type(data))
        return []

    questions: list[GeneratedQuestion] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            q = GeneratedQuestion(
                question=item.get("question", ""),
                suggested_answer=item.get("suggested_answer", ""),
                difficulty=item.get("difficulty", ""),
                source=item.get("source", ""),
                bloom_level=item.get("bloom_level", ""),
                keywords=item.get("keywords", []),
                subject=subject,
                chapter=chapter,
                chunk_ids=chunk_ids,
            )
            if q.question.strip():
                questions.append(q)
        except Exception as exc:
            logger.warning("Skipping invalid question item: %s", exc)
    return questions


def generate_questions(
    subject: str,
    chapter: str = "",
    num_questions: int = 5,
    max_context_chunks: int = 15,
    query: str = "",
    *,
    mongo: MongoChunkStore | None = None,
) -> list[GeneratedQuestion]:
    """Generate exam questions from textbook chunks.

    Parameters
    ----------
    subject:
        Subject name (e.g. ``"Lập trình Java"``).
    chapter:
        Chapter name. Empty string = all chapters.
    num_questions:
        Target number of questions.
    max_context_chunks:
        Max chunks to include in the LLM context.
    query:
        Optional semantic query to bias chunk selection.
    mongo:
        Optional explicit MongoChunkStore (for testing).
    """
    mongo = mongo or MongoChunkStore()

    chunks = _select_chunks(subject, chapter, max_context_chunks, query, mongo)

    if not chunks:
        logger.warning("No chunks found for subject=%r chapter=%r", subject, chapter)
        return []

    logger.info(
        "Selected %d chunks for generation (subject=%r, chapter=%r)",
        len(chunks), subject, chapter,
    )

    system_prompt, user_prompt = build_prompt(chunks, num_questions)
    raw = generate_text(system_prompt, user_prompt)

    if not raw:
        logger.error("LLM returned empty response")
        return []

    chunk_ids = [c.chunk_id for c in chunks]
    questions = _parse_questions(raw, subject, chapter, chunk_ids)

    logger.info(
        "Generated %d questions for subject=%r chapter=%r",
        len(questions), subject, chapter,
    )
    return questions


def generate_for_textbook(
    subject: str,
    questions_per_chapter: int = 5,
    max_context_chunks: int = 15,
    *,
    mongo: MongoChunkStore | None = None,
) -> list[GeneratedQuestion]:
    """Generate questions for every chapter of a textbook.

    Parameters
    ----------
    subject:
        Subject name.
    questions_per_chapter:
        Number of questions to generate per chapter.
    max_context_chunks:
        Max chunks per chapter in the LLM context.
    mongo:
        Optional explicit MongoChunkStore.

    Returns
    -------
    list[GeneratedQuestion]
        All generated questions across all chapters.
    """
    mongo = mongo or MongoChunkStore()

    all_chunks = mongo.get_chunks_by_filter(subject=subject)
    chapters = sorted({c.chapter for c in all_chunks if c.chapter})

    logger.info("Generating for %d chapters of %r", len(chapters), subject)

    all_questions: list[GeneratedQuestion] = []
    for i, ch in enumerate(chapters):
        logger.info("[%d/%d] Chapter: %s", i + 1, len(chapters), ch)
        qs = generate_questions(
            subject, chapter=ch,
            num_questions=questions_per_chapter,
            max_context_chunks=max_context_chunks,
            mongo=mongo,
        )
        all_questions.extend(qs)
        if i < len(chapters) - 1:
            time.sleep(_INTER_CHAPTER_DELAY)

    logger.info(
        "Total: %d questions generated for %r (%d chapters)",
        len(all_questions), subject, len(chapters),
    )
    return all_questions
