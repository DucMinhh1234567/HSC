"""Data models shared across HSC-Edu pipeline layers."""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class BlockType(str, Enum):
    """Semantic types assignable to a text block (Layer 2)."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE_CAPTION = "figure_caption"
    CODE = "code"
    LIST_ITEM = "list_item"
    DEFINITION = "definition"
    THEOREM = "theorem"
    EXAMPLE = "example"
    EXERCISE = "exercise"
    PROOF = "proof"
    NOTE = "note"
    UNKNOWN = "unknown"


class LinkType(str, Enum):
    """Types of semantic links between blocks."""

    HIERARCHY = "hierarchy"


# ---------------------------------------------------------------------------
# Layer 1 — Extraction
# ---------------------------------------------------------------------------


class FontInfo(BaseModel):
    """Dominant font metadata for a text block."""

    name: str = ""
    size: float = 0.0
    is_bold: bool = False
    is_italic: bool = False
    color: int = 0


class Block(BaseModel):
    """Raw text block extracted from a PDF page (Layer 1 output).

    Attributes
    ----------
    block_id : str
        Unique identifier (auto-generated short UUID).
    doc_id : str
        Foreign key to the source document.
    page : int
        Zero-based page index.
    bbox : tuple
        Bounding box ``(x0, y0, x1, y1)`` in PDF points.
    raw_text : str
        Extracted text content.
    block_type : str
        Semantic type — assigned later by Layer 2 classification.
    heading_level : int | None
        Heading depth (1 = chapter, 2 = section …) — set by Layer 2.
    confidence : float | None
        OCR confidence score (only for scanned PDFs).
    font_info : FontInfo | None
        Dominant font in this block (size, bold, name).
    """

    block_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    doc_id: str = ""
    page: int
    bbox: tuple[float, float, float, float]
    raw_text: str
    block_type: str = BlockType.UNKNOWN
    heading_level: int | None = None
    confidence: float | None = None
    font_info: FontInfo | None = None


# ---------------------------------------------------------------------------
# Layer 2 — Classification
# ---------------------------------------------------------------------------


class ClassifiedBlock(Block):
    """Block after Layer 2 classification.

    Inherits all ``Block`` fields.  The classifier sets ``block_type``
    to a concrete :class:`BlockType` value and populates
    ``section_path`` with the heading hierarchy leading to this block.
    """

    section_path: list[str] = Field(
        default_factory=list,
        description="Heading hierarchy, e.g. ['Chương 1. MỞ ĐẦU', '1.1. KHÁI NIỆM CƠ BẢN']",
    )
    classification_confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="How confident the classifier is about block_type.",
    )


# ---------------------------------------------------------------------------
# Layer 3 — Semantic Linking
# ---------------------------------------------------------------------------


@dataclass
class SemanticLink:
    """Directed edge in the semantic graph between two blocks."""

    source_block_id: str
    target_block_id: str
    link_type: str  # one of LinkType values
    confidence: float = 1.0
    label: str = ""  # human-readable label, e.g. "Hình 3.2"


@dataclass
class SemanticGraph:
    """Adjacency-list graph of :class:`SemanticLink` objects."""

    _outgoing: dict[str, list[SemanticLink]] = field(
        default_factory=lambda: defaultdict(list),
    )
    _incoming: dict[str, list[SemanticLink]] = field(
        default_factory=lambda: defaultdict(list),
    )

    def add_link(self, link: SemanticLink) -> None:
        self._outgoing[link.source_block_id].append(link)
        self._incoming[link.target_block_id].append(link)

    def add_links(self, links: list[SemanticLink]) -> None:
        for link in links:
            self.add_link(link)

    def get_outgoing(self, block_id: str) -> list[SemanticLink]:
        return self._outgoing.get(block_id, [])

    def get_incoming(self, block_id: str) -> list[SemanticLink]:
        return self._incoming.get(block_id, [])

    def get_links_by_type(self, link_type: str) -> list[SemanticLink]:
        result: list[SemanticLink] = []
        for links in self._outgoing.values():
            result.extend(lk for lk in links if lk.link_type == link_type)
        return result

    @property
    def all_links(self) -> list[SemanticLink]:
        result: list[SemanticLink] = []
        for links in self._outgoing.values():
            result.extend(links)
        return result

    def __len__(self) -> int:
        return sum(len(v) for v in self._outgoing.values())


# ---------------------------------------------------------------------------
# Layer 4 — Chunking
# ---------------------------------------------------------------------------


BLOCK_TYPE_TO_CHUNK_TYPE: dict[str, str] = {
    BlockType.THEOREM: "theorem",
    BlockType.DEFINITION: "definition",
    BlockType.EXAMPLE: "example",
    BlockType.EXERCISE: "exercise",
    BlockType.PROOF: "proof",
    BlockType.NOTE: "note",
    BlockType.CODE: "code",
    BlockType.PARAGRAPH: "theory",
    BlockType.HEADING: "theory",
    BlockType.LIST_ITEM: "theory",
}


class Chunk(BaseModel):
    """Semantic text chunk ready for embedding and retrieval.

    A chunk groups one or more consecutive :class:`ClassifiedBlock`
    objects under the same heading into a single retrieval unit.
    """

    chunk_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    doc_id: str = ""
    text: str
    block_ids: list[str] = Field(
        default_factory=list,
        description="IDs of the ClassifiedBlocks composing this chunk.",
    )

    subject: str = ""
    chapter: str = ""
    section: str = ""
    section_path: list[str] = Field(default_factory=list)
    page_start: int = 0
    page_end: int = 0
    block_type: str = BlockType.PARAGRAPH

    header_path: str = ""
    chunk_type: str = "mixed"
    has_formula: bool = False
    content: str = ""

    token_count: int = 0
