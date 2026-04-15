"""MongoDB chunk store — persists full Chunk documents with metadata."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection

from hsc_edu.config.settings import settings
from hsc_edu.core.models import Chunk

logger = logging.getLogger(__name__)

_CLIENT: MongoClient | None = None


def _get_collection() -> Collection:
    global _CLIENT  # noqa: PLW0603
    cfg = settings.mongo
    if _CLIENT is None:
        uri = os.environ.get(cfg.uri_env, cfg.uri_default)
        _CLIENT = MongoClient(uri)
    db_name = os.environ.get(cfg.database_env, cfg.database)
    db = _CLIENT[db_name]
    return db[cfg.collection]


def _ensure_indexes(col: Collection) -> None:
    col.create_index("chunk_id", unique=True)
    col.create_index("doc_id")
    col.create_index("subject")
    col.create_index("chapter")
    col.create_index([("subject", 1), ("chapter", 1)])


class MongoChunkStore:
    """CRUD operations on the MongoDB ``chunks`` collection."""

    def __init__(self) -> None:
        self._col = _get_collection()
        _ensure_indexes(self._col)

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        """Insert or update chunks, keyed by ``chunk_id``.

        Returns the number of upserted/modified documents.
        """
        if not chunks:
            return 0

        ops = []
        now = datetime.now(timezone.utc)
        for ch in chunks:
            doc = ch.model_dump()
            doc["updated_at"] = now
            ops.append(
                UpdateOne(
                    {"chunk_id": ch.chunk_id},
                    {"$set": doc, "$setOnInsert": {"created_at": now}},
                    upsert=True,
                )
            )

        result = self._col.bulk_write(ops)
        total = result.upserted_count + result.modified_count
        logger.info("MongoDB upsert: %d upserted, %d modified", result.upserted_count, result.modified_count)
        return total

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        """Fetch full Chunk documents by their IDs, preserving input order."""
        if not chunk_ids:
            return []

        docs = list(self._col.find({"chunk_id": {"$in": chunk_ids}}))
        id_to_doc = {d["chunk_id"]: d for d in docs}

        result: list[Chunk] = []
        for cid in chunk_ids:
            doc = id_to_doc.get(cid)
            if doc is None:
                logger.warning("chunk_id %r not found in MongoDB", cid)
                continue
            result.append(_doc_to_chunk(doc))
        return result

    def get_chunks_by_filter(
        self,
        *,
        subject: str = "",
        chapter: str = "",
        doc_id: str = "",
    ) -> list[Chunk]:
        """Query chunks by metadata filters."""
        query: dict = {}
        if subject:
            query["subject"] = subject
        if chapter:
            query["chapter"] = chapter
        if doc_id:
            query["doc_id"] = doc_id

        docs = list(self._col.find(query))
        return [_doc_to_chunk(d) for d in docs]

    def delete_by_doc_id(self, doc_id: str) -> int:
        """Delete all chunks belonging to a document. Returns deleted count."""
        result = self._col.delete_many({"doc_id": doc_id})
        logger.info("MongoDB deleted %d chunks for doc_id=%r", result.deleted_count, doc_id)
        return result.deleted_count

    def count(self, **filters: str) -> int:
        """Count documents matching optional filters."""
        return self._col.count_documents(filters or {})

    def distinct_values(self, field: str) -> list:
        """Return distinct values for a field (e.g. ``'subject'``)."""
        return self._col.distinct(field)


def _doc_to_chunk(doc: dict) -> Chunk:
    """Convert a MongoDB document back to a Chunk, ignoring Mongo-specific fields."""
    filtered = {
        k: v for k, v in doc.items()
        if k not in ("_id", "created_at", "updated_at")
    }
    return Chunk(**filtered)
