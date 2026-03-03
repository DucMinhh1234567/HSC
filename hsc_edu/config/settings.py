"""Global settings for HSC-Edu pipeline."""

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
    """Embedding model settings."""

    model_name: str = "text-embedding-3-small"
    dimensions: int = 1536


class LLMConfig(BaseModel):
    """LLM API settings."""

    model_name: str = "gpt-4o"
    temperature: float = 0.3
    max_output_tokens: int = 4096


class VectorStoreConfig(BaseModel):
    """Vector store settings."""

    provider: str = "chromadb"
    collection_name: str = "hsc_edu_chunks"
    persist_directory: str = "./data/vectorstore"


class Settings(BaseModel):
    """Root settings object aggregating all configs."""

    extraction: ExtractionConfig = ExtractionConfig()
    classification: ClassificationConfig = ClassificationConfig()
    linking: LinkingConfig = LinkingConfig()
    chunking: ChunkingConfig = ChunkingConfig()
    embedding: EmbeddingConfig = EmbeddingConfig()
    llm: LLMConfig = LLMConfig()
    vector_store: VectorStoreConfig = VectorStoreConfig()


settings = Settings()
