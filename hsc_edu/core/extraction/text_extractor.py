"""Extract text blocks from text-based PDFs using PyMuPDF.

Each block carries its raw text, bounding box, page number and
dominant font information (size, bold, name) — ready for Layer 2
classification.
"""

from __future__ import annotations

import logging
import re
import uuid
import math
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF

from hsc_edu.config.settings import settings
from hsc_edu.core.extraction.pdf_detector import PDFType, detect_pdf_type
from hsc_edu.core.models import Block, FontInfo

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_document(
    pdf_path: str | Path,
    *,
    doc_id: str | None = None,
) -> list[Block]:
    """Auto-detect PDF type, then extract text blocks accordingly.

    For *text-based* and *mixed* PDFs the PyMuPDF backend is used.
    *Scanned* PDFs will raise ``NotImplementedError`` until the OCR
    module is implemented in Phase 3.

    Parameters
    ----------
    pdf_path:
        Path to the PDF file.
    doc_id:
        Document identifier attached to every block.
        Auto-generated if not supplied.
    """
    result = detect_pdf_type(pdf_path)

    if result.pdf_type == PDFType.SCANNED:
        raise NotImplementedError(
            "OCR extraction is not yet implemented (planned for Phase 3). "
            f"PDF '{Path(pdf_path).name}' appears to be scanned."
        )

    return extract_with_pymupdf(pdf_path, doc_id=doc_id)


def extract_with_pymupdf(
    pdf_path: str | Path,
    *,
    doc_id: str | None = None,
) -> list[Block]:
    """Extract text blocks from a text-based PDF with PyMuPDF.

    Parameters
    ----------
    pdf_path:
        Path to the PDF file.
    doc_id:
        Document identifier.  Auto-generated if *None*.

    Returns
    -------
    list[Block]
        Blocks with ``raw_text``, ``page``, ``bbox``, and ``font_info``
        populated.  Noise (page numbers, repeated headers/footers) is
        already filtered out.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if doc_id is None:
        doc_id = uuid.uuid4().hex[:12]

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        raise RuntimeError(f"Cannot open PDF: {pdf_path}") from exc

    try:
        total_pages = len(doc)
        if total_pages == 0:
            raise RuntimeError(f"PDF has 0 pages: {pdf_path}")

        page_heights: dict[int, float] = {}
        raw_blocks: list[Block] = []

        for page_num in range(total_pages):
            page = doc[page_num]
            page_heights[page_num] = page.rect.height
            raw_blocks.extend(_extract_page_blocks(page, page_num, doc_id))
    finally:
        doc.close()

    filtered = _filter_noise(raw_blocks, total_pages, page_heights)

    logger.info(
        "Extracted %d blocks from '%s' (%d raw → %d after noise filter)",
        len(filtered),
        pdf_path.name,
        len(raw_blocks),
        len(filtered),
    )

    return filtered


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_page_blocks(
    page: fitz.Page,
    page_num: int,
    doc_id: str,
) -> list[Block]:
    """Return :class:`Block` objects for every text block on *page*."""
    page_dict = page.get_text("dict")
    blocks: list[Block] = []

    for blk in page_dict.get("blocks", []):
        if blk.get("type") != 0:  # 0 = text, 1 = image
            continue

        text = _block_text(blk)
        if not text.strip():
            continue

        blocks.append(
            Block(
                doc_id=doc_id,
                page=page_num,
                bbox=(
                    round(blk["bbox"][0], 2),
                    round(blk["bbox"][1], 2),
                    round(blk["bbox"][2], 2),
                    round(blk["bbox"][3], 2),
                ),
                raw_text=text.strip(),
                font_info=_dominant_font(blk),
            )
        )

    return blocks


def _block_text(blk: dict) -> str:
    """Concatenate all spans in *blk*, preserving line breaks."""
    lines: list[str] = []
    for line in blk.get("lines", []):
        spans_text = "".join(s.get("text", "") for s in line.get("spans", []))
        lines.append(spans_text)
    return "\n".join(lines)


def _dominant_font(blk: dict) -> FontInfo:
    """Return the :class:`FontInfo` covering the most characters."""
    counts: Counter[tuple[str, float, bool, bool]] = Counter()
    info_map: dict[tuple[str, float, bool, bool], FontInfo] = {}

    for line in blk.get("lines", []):
        for span in line.get("spans", []):
            n = len(span.get("text", ""))
            if n == 0:
                continue
            flags = span.get("flags", 0)
            font_name = span.get("font", "").lower()
            is_bold = bool(flags & 16) or any(
                kw in font_name for kw in ("bold", "bd", "heavy", "black")
            )
            is_italic = bool(flags & 2) or any(
                kw in font_name for kw in ("italic", "oblique", "it")
            )
            key = (
                span.get("font", ""),
                round(span.get("size", 0), 1),
                is_bold,
                is_italic,
            )
            counts[key] += n
            if key not in info_map:
                info_map[key] = FontInfo(
                    name=key[0],
                    size=key[1],
                    is_bold=key[2],
                    is_italic=key[3],
                    color=span.get("color", 0),
                )

    if not counts:
        return FontInfo()
    return info_map[counts.most_common(1)[0][0]]


# ---------------------------------------------------------------------------
# Noise filtering
# ---------------------------------------------------------------------------

_NOISE_RE: list[re.Pattern[str]] | None = None


def _get_noise_patterns() -> list[re.Pattern[str]]:
    global _NOISE_RE  # noqa: PLW0603
    if _NOISE_RE is None:
        _NOISE_RE = [re.compile(p) for p in settings.extraction.noise_patterns]
    return _NOISE_RE


def _filter_noise(
    blocks: list[Block],
    total_pages: int,
    page_heights: dict[int, float],
) -> list[Block]:
    """Remove page numbers and repeated header/footer text."""
    patterns = _get_noise_patterns()
    repeated = _find_repeated_header_footer(blocks, total_pages, page_heights)

    result: list[Block] = []
    for b in blocks:
        text = b.raw_text.strip()
        if any(p.match(text) for p in patterns):
            continue
        if text in repeated:
            continue
        result.append(b)
    return result


def _find_repeated_header_footer(
    blocks: list[Block],
    total_pages: int,
    page_heights: dict[int, float],
    *,
    zone_ratio: float = 0.08,
    min_page_ratio: float = 0.4,
) -> set[str]:
    """Identify text that repeats in the top/bottom margin across pages.

    A string found in the top/bottom *zone_ratio* of the page on strictly
    more than *min_page_ratio* of all pages is considered noise.
    """
    if total_pages < 3:
        return set()

    candidate_pages: dict[str, set[int]] = {}

    for b in blocks:
        ph = page_heights.get(b.page, 800.0)
        top_limit = ph * zone_ratio
        bottom_limit = ph * (1 - zone_ratio)

        in_top = b.bbox[1] < top_limit
        in_bottom = b.bbox[3] > bottom_limit

        if in_top or in_bottom:
            text = b.raw_text.strip()
            if text:
                candidate_pages.setdefault(text, set()).add(b.page)

    # Use a ratio-based threshold consistent with "strictly more than"
    # *min_page_ratio* of pages.
    threshold = math.floor(total_pages * min_page_ratio) + 1
    return {
        text for text, pages in candidate_pages.items() if len(pages) >= threshold
    }
