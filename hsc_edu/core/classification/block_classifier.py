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

_TOC_RE = re.compile(r"\.{3,}\s*\d+\s*$")


def _is_toc_entry(line: str) -> bool:
    """Return *True* if *line* looks like a table-of-contents entry.

    TOC lines typically end with a run of dots followed by a page number,
    e.g. ``"Chương 1. MỞ ĐẦU ............7"``.  Letting these through the
    heading classifier would pollute the section stack with every chapter
    listed in the TOC (all on page 0) before the real headings appear.
    """
    return _TOC_RE.search(line) is not None


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

    section_stack: list[tuple[int, str]] = []
    classified: list[ClassifiedBlock] = []

    for block in blocks:
        first_line = block.raw_text.split("\n", 1)[0].strip()

        if _is_toc_entry(first_line):
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
