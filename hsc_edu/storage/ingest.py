"""Ingest orchestrator — embed chunks and store in Qdrant + MongoDB."""

from __future__ import annotations

import logging
from pathlib import Path

from hsc_edu.core.models import Chunk
from hsc_edu.storage.embedding import embed_texts
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


def ingest_chunks(
    chunks: list[Chunk],
    *,
    mongo: MongoChunkStore | None = None,
    qdrant: QdrantVectorStore | None = None,
) -> int:
    """Embed chunks and persist to both MongoDB and Qdrant.

    Parameters
    ----------
    chunks:
        Chunk objects (output of ``chunk_blocks``).
    mongo:
        Optional explicit MongoDB store (for testing).
    qdrant:
        Optional explicit Qdrant store (for testing).

    Returns
    -------
    int
        Number of chunks successfully ingested.
    """
    if not chunks:
        return 0

    mongo_store = mongo or _get_mongo()
    qdrant_store = qdrant or _get_qdrant()

    texts = [ch.text for ch in chunks]
    logger.info("Embedding %d chunks…", len(texts))
    vectors = embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

    logger.info("Storing %d chunks in MongoDB…", len(chunks))
    mongo_store.upsert_chunks(chunks)

    chunk_ids = [ch.chunk_id for ch in chunks]
    payloads = [
        {
            "doc_id": ch.doc_id,
            "subject": ch.subject,
            "chapter": ch.chapter,
        }
        for ch in chunks
    ]

    logger.info("Upserting %d vectors in Qdrant…", len(vectors))
    qdrant_store.upsert_vectors(chunk_ids, vectors, payloads)

    logger.info("Ingested %d chunks successfully.", len(chunks))
    return len(chunks)


def ingest_pdf(
    pdf_path: str | Path,
    *,
    subject: str,
    doc_id: str | None = None,
    mongo: MongoChunkStore | None = None,
    qdrant: QdrantVectorStore | None = None,
) -> int:
    """Full pipeline: extract → classify → chunk → embed → store.

    Parameters
    ----------
    pdf_path:
        Path to the source PDF.
    subject:
        Subject name (e.g. ``"Lập trình Java"``).
    doc_id:
        Optional document ID. Auto-generated if not supplied.

    Returns
    -------
    int
        Number of chunks ingested.
    """
    from hsc_edu.core.extraction import extract_document
    from hsc_edu.core.classification import classify_blocks
    from hsc_edu.core.chunking import chunk_blocks

    pdf_path = Path(pdf_path)
    if doc_id is None:
        doc_id = pdf_path.stem.lower().replace(" ", "-")

    logger.info("Ingesting %r (subject=%r, doc_id=%r)…", pdf_path.name, subject, doc_id)

    blocks = extract_document(pdf_path, doc_id=doc_id)
    classified = classify_blocks(blocks)
    chunks = chunk_blocks(classified, subject=subject)

    return ingest_chunks(chunks, mongo=mongo, qdrant=qdrant)
