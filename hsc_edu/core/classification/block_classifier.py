"""Classify raw Blocks into ClassifiedBlocks (Layer 2).

Reads heading / special-block regex patterns and font hints from the
subject config YAML (default: ``default.yaml``).  Classification is
rule-based: regex match on ``raw_text`` plus optional font-size /
bold boosts.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from hsc_edu.config.settings import settings
from hsc_edu.core.models import Block, BlockType, ClassifiedBlock, FontInfo

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal config cache
# ---------------------------------------------------------------------------

_CONFIG_CACHE: dict[str, Any] | None = None


def _load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load and cache the subject config YAML."""
    global _CONFIG_CACHE  # noqa: PLW0603
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    if config_path is None:
        config_path = settings.classification.heading_config_path

    if not config_path.is_absolute():
        pkg_root = Path(__file__).resolve().parents[2]  # hsc_edu/
        config_path = pkg_root / config_path

    if not config_path.exists():
        logger.warning("Config not found at %s — using empty config", config_path)
        _CONFIG_CACHE = {}
        return _CONFIG_CACHE

    with open(config_path, encoding="utf-8") as fh:
        _CONFIG_CACHE = yaml.safe_load(fh) or {}

    logger.info("Loaded classification config from %s", config_path)
    return _CONFIG_CACHE


def reset_config_cache() -> None:
    """Clear the cached config and compiled patterns (useful for tests)."""
    global _CONFIG_CACHE, _HEADING_RE, _SPECIAL_RE  # noqa: PLW0603
    _CONFIG_CACHE = None
    _HEADING_RE = None
    _SPECIAL_RE = None


# ---------------------------------------------------------------------------
# Compiled pattern helpers
# ---------------------------------------------------------------------------

_HEADING_RE: list[tuple[int, re.Pattern[str], dict[str, Any]]] | None = None
_SPECIAL_RE: list[tuple[BlockType, re.Pattern[str]]] | None = None


def _compile_heading_patterns(
    cfg: dict[str, Any],
) -> list[tuple[int, re.Pattern[str], dict[str, Any]]]:
    """Return ``(level, compiled_re, font_hints)`` for each heading level."""
    result: list[tuple[int, re.Pattern[str], dict[str, Any]]] = []
    heading_cfg = cfg.get("heading_patterns", {})
    for key in sorted(heading_cfg):
        level_data = heading_cfg[key]
        level_num = int(key.split("_")[-1])
        hints = level_data.get("font_hints", {})
        for pat in level_data.get("patterns", []):
            result.append((level_num, re.compile(pat), hints))
    return result


def _compile_special_patterns(
    cfg: dict[str, Any],
) -> list[tuple[BlockType, re.Pattern[str]]]:
    """Return ``(BlockType, compiled_re)`` for each special block type."""
    result: list[tuple[BlockType, re.Pattern[str]]] = []
    special_cfg = cfg.get("special_block_patterns", {})
    type_map: dict[str, BlockType] = {
        "definition": BlockType.DEFINITION,
        "theorem": BlockType.THEOREM,
        "example": BlockType.EXAMPLE,
        "exercise": BlockType.EXERCISE,
        "note": BlockType.NOTE,
        "proof": BlockType.PROOF,
    }
    for name, patterns in special_cfg.items():
        bt = type_map.get(name)
        if bt is None:
            continue
        for pat in patterns:
            result.append((bt, re.compile(pat)))
    return result


def _get_heading_patterns() -> list[tuple[int, re.Pattern[str], dict[str, Any]]]:
    global _HEADING_RE  # noqa: PLW0603
    if _HEADING_RE is None:
        _HEADING_RE = _compile_heading_patterns(_load_config())
    return _HEADING_RE


def _get_special_patterns() -> list[tuple[BlockType, re.Pattern[str]]]:
    global _SPECIAL_RE  # noqa: PLW0603
    if _SPECIAL_RE is None:
        _SPECIAL_RE = _compile_special_patterns(_load_config())
    return _SPECIAL_RE


# ---------------------------------------------------------------------------
# Font-hint scoring
# ---------------------------------------------------------------------------


def _font_confidence_boost(font: FontInfo | None, hints: dict[str, Any]) -> float:
    """Return a confidence boost in ``[0.0, 0.2]`` based on font hints.

    Font hints are *soft signals*: they increase confidence when present
    but never prevent a regex match from succeeding.
    """
    if not hints or font is None:
        return 0.0

    boost = 0.0
    size_min = hints.get("size_min")
    if size_min is not None and font.size >= size_min:
        boost += 0.1

    bold_hint = hints.get("is_bold")
    if bold_hint == "preferred" and font.is_bold:
        boost += 0.1

    return boost


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_BASE_REGEX_CONFIDENCE = 0.75

_MAX_TOC_START_PAGE = 15
_MAX_TOC_GAP = 3

_TOC_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\.{3,}\s*\d+", re.MULTILINE),
    re.compile(r"\n\s*\d{1,4}\s*$"),
]


def _is_toc_entry(text: str) -> bool:
    """Return *True* if *text* looks like a table-of-contents entry.

    Matches two common TOC patterns found in Vietnamese textbook PDFs:

    * Dot-leader followed by a page number anywhere in the text, e.g.
      ``"Chương 1. MỞ ĐẦU ............7"``
    * A bare page number sitting alone on the last line of a multi-line
      block, e.g. ``"5.4. ĐÓNG GÓI ...\\n75"``
    """
    return any(p.search(text) for p in _TOC_PATTERNS)


def _detect_toc_pages(
    blocks: list[Block],
    heading_pats: list[tuple[int, re.Pattern[str], dict[str, Any]]],
    special_pats: list[tuple[BlockType, re.Pattern[str]]],
) -> frozenset[int]:
    """Identify pages that belong to the table of contents.

    Phase 1 — find *anchor* pages containing at least one block that
    matches :func:`_is_toc_entry`.

    Phase 2 — walk through anchor pages sorted by page number.
    Starting from the first anchor (which must be within the first
    15 pages), include all pages from 0 up through the last anchor
    that is still within *_MAX_TOC_GAP* pages of the previous one.
    This fills gap pages that lack dot-leaders while ignoring
    spurious anchors deep in the document body.

    Phase 3 — extend for heading-dense pages immediately after the
    anchor range (TOC continuation without dot-leaders).
    """
    from collections import defaultdict

    anchor_pages: set[int] = set()
    page_heading_count: dict[int, int] = defaultdict(int)

    for block in blocks:
        if _is_toc_entry(block.raw_text):
            anchor_pages.add(block.page)
        first_line = block.raw_text.split("\n", 1)[0].strip()
        btype, _, _ = _match_block(first_line, block.font_info, heading_pats, special_pats)
        if btype == BlockType.HEADING:
            page_heading_count[block.page] += 1

    if not anchor_pages:
        return frozenset()

    sorted_anchors = sorted(anchor_pages)

    if sorted_anchors[0] > _MAX_TOC_START_PAGE:
        return frozenset()

    toc_end = sorted_anchors[0]
    for i in range(1, len(sorted_anchors)):
        if sorted_anchors[i] - toc_end > _MAX_TOC_GAP:
            break
        toc_end = sorted_anchors[i]

    toc_pages: set[int] = set(range(toc_end + 1))

    page = toc_end + 1
    while page_heading_count.get(page, 0) >= 2:
        toc_pages.add(page)
        page += 1

    return frozenset(toc_pages)


def classify_blocks(
    blocks: list[Block],
    *,
    config_path: Path | None = None,
) -> list[ClassifiedBlock]:
    """Classify a sequence of raw blocks into :class:`ClassifiedBlock`.

    Parameters
    ----------
    blocks:
        Layer 1 output — raw ``Block`` objects.
    config_path:
        Optional override for the subject config YAML.

    Returns
    -------
    list[ClassifiedBlock]
        Blocks enriched with ``block_type``, ``heading_level``,
        ``section_path``, and ``classification_confidence``.
    """
    if config_path is not None:
        reset_config_cache()
        _load_config(config_path)

    heading_pats = _get_heading_patterns()
    special_pats = _get_special_patterns()
    toc_pages = _detect_toc_pages(blocks, heading_pats, special_pats)

    section_stack: list[tuple[int, str]] = []
    classified: list[ClassifiedBlock] = []

    for block in blocks:
        first_line = block.raw_text.split("\n", 1)[0].strip()

        if _is_toc_entry(block.raw_text) or block.page in toc_pages:
            btype, level, confidence = BlockType.PARAGRAPH, None, 0.5
        else:
            btype, level, confidence = _match_block(
                first_line, block.font_info, heading_pats, special_pats,
            )

        if btype == BlockType.HEADING and level is not None:
            _update_section_stack(section_stack, level, first_line)

        section_path = [text for _, text in section_stack]

        cb = ClassifiedBlock(
            block_id=block.block_id,
            doc_id=block.doc_id,
            page=block.page,
            bbox=block.bbox,
            raw_text=block.raw_text,
            block_type=btype,
            heading_level=level,
            confidence=block.confidence,
            font_info=block.font_info,
            section_path=section_path,
            classification_confidence=round(confidence, 4),
        )
        classified.append(cb)

    logger.info(
        "Classified %d blocks: %d headings, %d paragraphs, %d special",
        len(classified),
        sum(1 for c in classified if c.block_type == BlockType.HEADING),
        sum(1 for c in classified if c.block_type == BlockType.PARAGRAPH),
        sum(
            1
            for c in classified
            if c.block_type
            not in (BlockType.HEADING, BlockType.PARAGRAPH, BlockType.UNKNOWN)
        ),
    )

    return classified


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------


def _match_block(
    first_line: str,
    font: FontInfo | None,
    heading_pats: list[tuple[int, re.Pattern[str], dict[str, Any]]],
    special_pats: list[tuple[BlockType, re.Pattern[str]]],
) -> tuple[BlockType, int | None, float]:
    """Return ``(block_type, heading_level, confidence)``."""

    for level, pat, hints in heading_pats:
        if pat.search(first_line):
            conf = _BASE_REGEX_CONFIDENCE + _font_confidence_boost(font, hints)
            return BlockType.HEADING, level, min(conf, 1.0)

    for btype, pat in special_pats:
        if pat.search(first_line):
            return btype, None, _BASE_REGEX_CONFIDENCE

    return BlockType.PARAGRAPH, None, _BASE_REGEX_CONFIDENCE


def _update_section_stack(
    stack: list[tuple[int, str]],
    level: int,
    heading_text: str,
) -> None:
    """Maintain a heading hierarchy stack.

    When a new heading at *level* appears, pop all entries whose level
    is >= *level*, then push the new heading.
    """
    while stack and stack[-1][0] >= level:
        stack.pop()
    stack.append((level, heading_text))
