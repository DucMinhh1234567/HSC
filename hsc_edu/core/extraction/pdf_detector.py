"""Detect whether a PDF is text-based, scanned, or mixed.

Uses PyMuPDF (fitz) to sample pages and count extractable characters.
The threshold comes from ``ExtractionConfig.min_text_chars_per_page``
(default 50).
"""

from __future__ import annotations

import logging
import math
from enum import Enum
from pathlib import Path
from typing import NamedTuple

import fitz  # PyMuPDF

from hsc_edu.config.settings import settings

logger = logging.getLogger(__name__)


class PDFType(str, Enum):
    """Possible PDF types."""

    TEXT_BASED = "text-based"
    SCANNED = "scanned"
    MIXED = "mixed"


class DetectionResult(NamedTuple):
    """Structured result returned by :func:`detect_pdf_type`."""

    pdf_type: PDFType
    total_pages: int
    text_pages: int
    scan_pages: int
    text_ratio: float


def _count_text_chars(page: fitz.Page) -> int:
    """Return the number of non-whitespace characters on *page*."""
    text = page.get_text("text") or ""
    return len(text.replace(" ", "").replace("\n", "").replace("\t", ""))


def detect_pdf_type(
    pdf_path: str | Path,
    *,
    sample_size: int | None = None,
    threshold: int | None = None,
) -> DetectionResult:
    """Classify a PDF as ``text-based``, ``scanned``, or ``mixed``.

    Parameters
    ----------
    pdf_path:
        Path to the PDF file.
    sample_size:
        Maximum number of pages to inspect.  ``None`` means *all* pages.
    threshold:
        Minimum non-whitespace characters for a page to count as
        *text-based*.  Defaults to
        ``settings.extraction.min_text_chars_per_page`` (50).

    Returns
    -------
    DetectionResult
        A named tuple with ``pdf_type``, page counts, and ``text_ratio``.

    Raises
    ------
    FileNotFoundError
        If *pdf_path* does not exist.
    RuntimeError
        If the file cannot be opened as a PDF.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if threshold is None:
        threshold = settings.extraction.min_text_chars_per_page

    if sample_size is not None and sample_size <= 0:
        raise ValueError("sample_size must be a positive integer or None")

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        raise RuntimeError(f"Cannot open PDF: {pdf_path}") from exc

    try:
        total_pages = len(doc)
        if total_pages == 0:
            raise RuntimeError(f"PDF has 0 pages: {pdf_path}")

        pages_to_check = _sample_page_indices(total_pages, sample_size)

        text_pages = 0
        scan_pages = 0

        for page_idx in pages_to_check:
            char_count = _count_text_chars(doc[page_idx])
            if char_count >= threshold:
                text_pages += 1
            else:
                scan_pages += 1
    finally:
        doc.close()

    inspected = text_pages + scan_pages
    text_ratio = text_pages / inspected if inspected else 0.0

    if text_ratio >= 0.8:
        pdf_type = PDFType.TEXT_BASED
    elif text_ratio <= 0.2:
        pdf_type = PDFType.SCANNED
    else:
        pdf_type = PDFType.MIXED

    result = DetectionResult(
        pdf_type=pdf_type,
        total_pages=total_pages,
        text_pages=text_pages,
        scan_pages=scan_pages,
        text_ratio=round(text_ratio, 4),
    )

    logger.info(
        "PDF detection: %s → %s  (text_pages=%d, scan_pages=%d, ratio=%.2f)",
        pdf_path.name,
        result.pdf_type.value,
        result.text_pages,
        result.scan_pages,
        result.text_ratio,
    )

    return result


def _sample_page_indices(total_pages: int, sample_size: int | None) -> list[int]:
    """Return a list of page indices to inspect.

    Attempts to use up to *sample_size* samples, without exceeding it.
    """
    if sample_size is None or sample_size >= total_pages:
        return list(range(total_pages))

    # Evenly sample across the whole document, including both ends, similar to
    # numpy.linspace(0, total_pages - 1, num=sample_size, dtype=int) but
    # without introducing a dependency.
    count = min(sample_size, total_pages)
    if count <= 1:
        return [0]

    positions = [
        round(i * (total_pages - 1) / (count - 1)) for i in range(count)
    ]

    # Deduplicate while preserving order.
    seen: set[int] = set()
    indices: list[int] = []
    for idx in positions:
        if idx not in seen:
            seen.add(idx)
            indices.append(int(idx))

    # Ensure we never exceed the requested upper bound.
    return indices[:count]
