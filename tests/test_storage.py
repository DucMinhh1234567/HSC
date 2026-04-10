"""Unit tests for the storage layer (Mongo, Qdrant, retrieval)."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from qdrant_client import QdrantClient

from hsc_edu.core.models import Chunk
from hsc_edu.storage.mongo_store import MongoChunkStore
from hsc_edu.storage.vector_store import QdrantVectorStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _chunk(
    chunk_id: str = "c1",
    doc_id: str = "doc1",
    subject: str = "Java",
    chapter: str = "Chương 1. MỞ ĐẦU",
    text: str = "Nội dung mẫu.",
    page_start: int = 5,
    page_end: int = 6,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        doc_id=doc_id,
        subject=subject,
        chapter=chapter,
        text=text,
        page_start=page_start,
        page_end=page_end,
        token_count=10,
    )


# ---------------------------------------------------------------------------
# QdrantVectorStore (uses in-memory client — no external service needed)
# ---------------------------------------------------------------------------

class TestQdrantVectorStore:
    @pytest.fixture(autouse=True)
    def setup(self):
        mem_client = QdrantClient(":memory:")
        with patch.dict("os.environ", {"QDRANT_URL": "http://fake", "QDRANT_API_KEY": "fake"}):
            self.store = QdrantVectorStore(client=mem_client)

    def test_upsert_and_search(self):
        ids = ["c1", "c2"]
        vectors = [[0.1] * 768, [0.9] * 768]
        payloads = [
            {"doc_id": "d1", "subject": "Java", "chapter": "Ch1"},
            {"doc_id": "d1", "subject": "Java", "chapter": "Ch2"},
        ]
        self.store.upsert_vectors(ids, vectors, payloads)

        results = self.store.search([0.9] * 768, top_k=2)
        assert len(results) == 2
        assert results[0][0] == "c2"
        assert results[0][1] > results[1][1]

    def test_search_with_subject_filter(self):
        self.store.upsert_vectors(
            ["c1", "c2"],
            [[0.5] * 768, [0.5] * 768],
            [
                {"doc_id": "d1", "subject": "Java", "chapter": "Ch1"},
                {"doc_id": "d2", "subject": "C", "chapter": "Ch1"},
            ],
        )
        results = self.store.search([0.5] * 768, subject="C", top_k=5)
        assert len(results) == 1
        assert results[0][0] == "c2"

    def test_delete_by_doc_id(self):
        self.store.upsert_vectors(
            ["c1", "c2"],
            [[0.1] * 768, [0.2] * 768],
            [
                {"doc_id": "d1", "subject": "Java", "chapter": "Ch1"},
                {"doc_id": "d2", "subject": "C", "chapter": "Ch1"},
            ],
        )
        self.store.delete_by_doc_id("d1")
        results = self.store.search([0.1] * 768, top_k=5)
        assert len(results) == 1
        assert results[0][0] == "c2"

    def test_collection_info(self):
        self.store.upsert_vectors(["c1"], [[0.1] * 768], [{"doc_id": "d1", "subject": "X", "chapter": "Y"}])
        info = self.store.collection_info()
        assert info["name"] == "hsc_edu_chunks"
        assert info["points_count"] >= 1


# ---------------------------------------------------------------------------
# MongoChunkStore (uses mongomock-like approach via mongomock or real local)
# ---------------------------------------------------------------------------

class TestMongoChunkStore:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Use a temporary test database to avoid polluting real data."""
        with patch("hsc_edu.storage.mongo_store.settings") as mock_settings:
            mock_settings.mongo.uri_env = "MONGO_URI"
            mock_settings.mongo.uri_default = "mongodb://localhost:27017"
            mock_settings.mongo.database = "hsc_edu_test"
            mock_settings.mongo.collection = "chunks_test"

            import hsc_edu.storage.mongo_store as mod
            mod._CLIENT = None

            try:
                self.store = MongoChunkStore()
                self.store._col.delete_many({})
            except Exception:
                pytest.skip("MongoDB not available locally")

        yield
        try:
            self.store._col.delete_many({})
        except Exception:
            pass

    def test_upsert_and_get_by_ids(self):
        c1 = _chunk("c1", text="Hello")
        c2 = _chunk("c2", text="World")
        self.store.upsert_chunks([c1, c2])

        result = self.store.get_chunks_by_ids(["c2", "c1"])
        assert len(result) == 2
        assert result[0].chunk_id == "c2"
        assert result[1].chunk_id == "c1"
        assert result[0].text == "World"

    def test_upsert_idempotent(self):
        c1 = _chunk("c1", text="v1")
        self.store.upsert_chunks([c1])
        assert self.store.count() == 1

        c1_v2 = _chunk("c1", text="v2")
        self.store.upsert_chunks([c1_v2])
        assert self.store.count() == 1

        result = self.store.get_chunks_by_ids(["c1"])
        assert result[0].text == "v2"

    def test_get_by_filter(self):
        self.store.upsert_chunks([
            _chunk("c1", subject="Java", chapter="Ch1"),
            _chunk("c2", subject="Java", chapter="Ch2"),
            _chunk("c3", subject="C", chapter="Ch1"),
        ])

        java_chunks = self.store.get_chunks_by_filter(subject="Java")
        assert len(java_chunks) == 2

        ch1_chunks = self.store.get_chunks_by_filter(subject="Java", chapter="Ch1")
        assert len(ch1_chunks) == 1
        assert ch1_chunks[0].chunk_id == "c1"

    def test_delete_by_doc_id(self):
        self.store.upsert_chunks([
            _chunk("c1", doc_id="d1"),
            _chunk("c2", doc_id="d2"),
        ])
        deleted = self.store.delete_by_doc_id("d1")
        assert deleted == 1
        assert self.store.count() == 1

    def test_distinct_values(self):
        self.store.upsert_chunks([
            _chunk("c1", subject="Java"),
            _chunk("c2", subject="C"),
            _chunk("c3", subject="Java"),
        ])
        subjects = self.store.distinct_values("subject")
        assert set(subjects) == {"Java", "C"}

    def test_get_missing_id_skipped(self):
        self.store.upsert_chunks([_chunk("c1")])
        result = self.store.get_chunks_by_ids(["c1", "nonexistent"])
        assert len(result) == 1
