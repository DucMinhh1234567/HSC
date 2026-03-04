"""Layer 1 — Document extraction modules."""

from hsc_edu.core.extraction.pdf_detector import PDFType, detect_pdf_type
from hsc_edu.core.extraction.text_extractor import (
    extract_document,
    extract_with_pymupdf,
)

__all__ = [
    "PDFType",
    "detect_pdf_type",
    "extract_document",
    "extract_with_pymupdf",
]
