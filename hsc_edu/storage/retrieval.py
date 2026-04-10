"""Retrieval — semantic search over stored chunks."""

from __future__ import annotations

import logging

from hsc_edu.core.models import Chunk
from hsc_edu.storage.embedding import embed_query
from hsc_edu.storage.mongo_store import MongoChunkStore
from hsc_edu.storage.vector_store import QdrantVectorStore

logger = logging.getLogger(__name__)

_mongo: MongoChunkStore | None = None
_qdrant: QdrantVectorStore | None = None


def _get_mongo() -> MongoChunkStore:
    global _mongo  # noqa: PLW0603
    if _mongo is None:
        _mongo = MongoChunkStore()
    return _mongo


def _get_qdrant() -> QdrantVectorStore:
    global _qdrant  # noqa: PLW0603
    if _qdrant is None:
        _qdrant = QdrantVectorStore()
    return _qdrant


def retrieve_chunks(
    query: str,
    *,
    subject: str = "",
    chapter: str = "",
    doc_id: str = "",
    top_k: int = 10,
    mongo: MongoChunkStore | None = None,
    qdrant: QdrantVectorStore | None = None,
) -> list[tuple[Chunk, float]]:
    """Retrieve the most relevant chunks for a natural-language query.

    Flow
    ----
    1. Embed *query* with ``task_type=RETRIEVAL_QUERY``.
    2. Search Qdrant with optional metadata filters → ``(chunk_id, score)`` list.
    3. Fetch full Chunk documents from MongoDB by ID.
    4. Return ``(Chunk, score)`` pairs sorted by descending score.

    Parameters
    ----------
    query:
        Natural-language question or search string.
    subject:
        Filter by subject (exact match). Empty string = no filter.
    chapter:
        Filter by chapter (exact match).
    doc_id:
        Filter by document ID.
    top_k:
        Maximum number of results.
    mongo / qdrant:
        Optional explicit stores (for testing).
    """
    mongo_store = mongo or _get_mongo()
    qdrant_store = qdrant or _get_qdrant()

    query_vector = embed_query(query)

    hits = qdrant_store.search(
        query_vector,
        subject=subject,
        chapter=chapter,
        doc_id=doc_id,
        top_k=top_k,
    )

    if not hits:
        logger.info("No results for query=%r", query[:80])
        return []

    chunk_ids = [cid for cid, _ in hits]
    score_map = {cid: score for cid, score in hits}

    chunks = mongo_store.get_chunks_by_ids(chunk_ids)

    results = [(ch, score_map.get(ch.chunk_id, 0.0)) for ch in chunks]
    results.sort(key=lambda x: x[1], reverse=True)

    logger.info(
        "Retrieved %d chunks for query=%r (top score=%.4f)",
        len(results), query[:80],
        results[0][1] if results else 0.0,
    )
    return results
