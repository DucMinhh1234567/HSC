"""Global settings for HSC-Edu pipeline."""

import os
from pathlib import Path

from pydantic import BaseModel


class ExtractionConfig(BaseModel):
    """Layer 1 — PDF extraction settings."""

    min_text_chars_per_page: int = 50
    noise_patterns: list[str] = [
        r"^\s*\d+\s*$",
        r"^-\s*\d+\s*-$",
        r"^Trang\s+\d+$",
        r"^Page\s+\d+$",
    ]


class ClassificationConfig(BaseModel):
    """Layer 2 — Block classification settings."""

    heading_config_path: Path = Path("config/subject_configs/default.yaml")
    min_heading_font_size: float = 12.0


class LinkingConfig(BaseModel):
    """Layer 3 — Semantic linking settings."""

    enable_reference_linking: bool = True
    enable_proximity_linking: bool = True
    enable_table_continuation: bool = True
    proximity_max_distance_px: float = 50.0


class ChunkingConfig(BaseModel):
    """Layer 4 — Chunking settings."""

    max_tokens: int = 1024
    min_tokens: int = 64
    overlap_tokens: int = 128
    merge_short_threshold: int = 100


class EmbeddingConfig(BaseModel):
    """Gemini embedding model settings."""

    model_name: str = "gemini-embedding-001"
    dimensions: int = 768
    batch_size: int = 20
    api_key_env: str = "GOOGLE_API_KEY"
    #: Seconds to wait between successful batches (reduces RPM / burst 429s on free tier).
    embed_batch_delay_sec: float = 7.0


class LLMConfig(BaseModel):
    """Gemini LLM API settings."""

    model_name: str = "gemini-flash-latest"
    temperature: float = 0.3
    max_output_tokens: int = 4096
    api_key_env: str = "GOOGLE_API_KEY"


class VectorStoreConfig(BaseModel):
    """Qdrant vector store settings."""

    provider: str = "qdrant"
    collection_name: str = "hsc_edu_chunks"
    url_env: str = "QDRANT_URL"
    api_key_env: str = "QDRANT_API_KEY"
    #: HTTP client timeout (seconds) for Qdrant Cloud — large upserts need generous limits.
    http_timeout_sec: int = 180
    #: Points per upsert request; smaller batches reduce write timeouts on slow links.
    upsert_batch_size: int = 40


class MongoConfig(BaseModel):
    """MongoDB metadata/chunk store settings."""

    uri_env: str = "MONGO_URI"
    uri_default: str = "mongodb://localhost:27017"
    database_env: str = "MONGO_DB"
    database: str = "learn"
    collection: str = "chunks"


class Settings(BaseModel):
    """Root settings object aggregating all configs."""

    extraction: ExtractionConfig = ExtractionConfig()
    classification: ClassificationConfig = ClassificationConfig()
    linking: LinkingConfig = LinkingConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    llm: LLMConfig = LLMConfig()
    vector_store: VectorStoreConfig = VectorStoreConfig()
    mongo: MongoConfig = MongoConfig()


settings = Settings()
