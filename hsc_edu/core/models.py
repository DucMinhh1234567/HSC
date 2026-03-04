"""Data models shared across HSC-Edu pipeline layers."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


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
    block_type: str = "unknown"
    heading_level: int | None = None
    confidence: float | None = None
    font_info: FontInfo | None = None
