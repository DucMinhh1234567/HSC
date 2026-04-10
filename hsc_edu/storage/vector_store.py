"""Qdrant vector store — stores chunk embeddings with lightweight payload."""

from __future__ import annotations

import logging
import os
import time
import uuid

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from hsc_edu.config.settings import settings

logger = logging.getLogger(__name__)


def _to_qdrant_id(chunk_id: str) -> str:
    """Convert a short hex chunk_id to a full UUID string for Qdrant."""
    padded = chunk_id.ljust(32, "0")[:32]
    return str(uuid.UUID(padded))


class QdrantVectorStore:
    """Wrapper around ``qdrant-client`` for chunk vector operations."""

    def __init__(self, *, client: QdrantClient | None = None) -> None:
        cfg = settings.vector_store
        emb_cfg = settings.embedding

        if client is not None:
            self._client = client
        else:
            url = os.environ.get(cfg.url_env, "")
            api_key = os.environ.get(cfg.api_key_env, "")
            if not url:
                raise RuntimeError(
                    f"Environment variable {cfg.url_env!r} is not set. "
                    "Please add your Qdrant Cloud URL to .env"
                )
            self._client = QdrantClient(
                url=url,
                api_key=api_key or None,
                timeout=cfg.http_timeout_sec,
            )

        self._collection = cfg.collection_name
        self._upsert_batch_size = cfg.upsert_batch_size
        self._http_timeout_sec = cfg.http_timeout_sec
        self._dim = emb_cfg.dimensions
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._dim,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(
                "Created Qdrant collection %r (dim=%d, cosine)",
                self._collection, self._dim,
            )
        self._ensure_payload_indexes()

    def _ensure_payload_indexes(self) -> None:
        """Qdrant Cloud requires keyword payload indexes for filtered vector search."""
        for field in ("subject", "chapter", "doc_id"):
            try:
                self._client.create_payload_index(
                    collection_name=self._collection,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                    timeout=self._http_timeout_sec,
                )
                logger.info("Qdrant payload index ready: %r (keyword)", field)
            except UnexpectedResponse as exc:
                text = exc.content.decode("utf-8", errors="replace").lower()
                if exc.status_code == 400 and any(
                    s in text for s in ("already exists", "already exist", "duplicate")
                ):
                    continue
                raise

    def upsert_vectors(
        self,
        chunk_ids: list[str],
        vectors: list[list[float]],
        payloads: list[dict],
    ) -> None:
        """Upsert points into the collection in batches.

        Each point's Qdrant ID is a UUID derived from the ``chunk_id``.
        The original ``chunk_id`` is stored in the payload for reverse lookup.
        """
        batch_size = self._upsert_batch_size
        total = len(chunk_ids)
        cfg = settings.vector_store

        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            points = [
                PointStruct(
                    id=_to_qdrant_id(chunk_ids[i]),
                    vector=vectors[i],
                    payload={**payloads[i], "chunk_id": chunk_ids[i]},
                )
                for i in range(start, end)
            ]
            self._upsert_batch_with_retry(points, timeout_sec=cfg.http_timeout_sec)

        logger.info("Qdrant upsert: %d points into %r", total, self._collection)

    def _upsert_batch_with_retry(
        self,
        points: list[PointStruct],
        *,
        timeout_sec: int,
        max_attempts: int = 4,
    ) -> None:
        """Retry upserts on transient network / timeout errors (Qdrant Cloud)."""
        for attempt in range(1, max_attempts + 1):
            try:
                self._client.upsert(
                    collection_name=self._collection,
                    points=points,
                    timeout=timeout_sec,
                )
                return
            except Exception as exc:
                msg = str(exc).lower()
                transient = any(
                    x in msg
                    for x in (
                        "timeout",
                        "timed out",
                        "write operation",
                        "connection",
                        "temporarily",
                        "503",
                        "502",
                        "429",
                    )
                )
                if not transient or attempt == max_attempts:
                    raise
                wait = min(2.0**attempt, 30.0)
                logger.warning(
                    "Qdrant upsert failed (attempt %d/%d), retrying in %.1fs: %s",
                    attempt,
                    max_attempts,
                    wait,
                    exc,
                )
                time.sleep(wait)

    def search(
        self,
        query_vector: list[float],
        *,
        subject: str = "",
        chapter: str = "",
        doc_id: str = "",
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        """Semantic search with optional metadata filters.

        Returns a list of ``(chunk_id, score)`` sorted by descending score.
        """
        conditions: list[FieldCondition] = []
        if subject:
            conditions.append(FieldCondition(key="subject", match=MatchValue(value=subject)))
        if chapter:
            conditions.append(FieldCondition(key="chapter", match=MatchValue(value=chapter)))
        if doc_id:
            conditions.append(FieldCondition(key="doc_id", match=MatchValue(value=doc_id)))

        query_filter = Filter(must=conditions) if conditions else None

        response = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
        )

        return [
            (pt.payload.get("chunk_id", pt.id), pt.score)
            for pt in response.points
        ]

    def delete_by_doc_id(self, doc_id: str) -> None:
        """Delete all points belonging to a document."""
        self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
        )
        logger.info("Qdrant deleted points for doc_id=%r", doc_id)

    def collection_info(self) -> dict:
        """Return basic stats about the collection."""
        info = self._client.get_collection(self._collection)
        return {
            "name": self._collection,
            "points_count": info.points_count,
            "status": info.status.value,
        }
