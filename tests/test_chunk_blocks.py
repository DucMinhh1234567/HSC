"""Unit tests for chunk_blocks — grouping, deduplication, metadata."""

from __future__ import annotations

import pytest

from hsc_edu.core.chunking.text_chunker import (
    _group_by_heading,
    chunk_blocks,
)
from hsc_edu.core.models import BlockType, ClassifiedBlock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cb(
    raw_text: str,
    block_type: str = BlockType.PARAGRAPH,
    heading_level: int | None = None,
    section_path: list[str] | None = None,
    page: int = 0,
    block_id: str | None = None,
) -> ClassifiedBlock:
    """Create a minimal ClassifiedBlock."""
    kwargs: dict = dict(
        page=page,
        bbox=(0, 0, 100, 20),
        raw_text=raw_text,
        block_type=block_type,
        heading_level=heading_level,
        section_path=section_path or [],
    )
    if block_id is not None:
        kwargs["block_id"] = block_id
    return ClassifiedBlock(**kwargs)


# ---------------------------------------------------------------------------
# _group_by_heading
# ---------------------------------------------------------------------------

class TestGroupByHeading:
    def test_heading_not_in_body_blocks(self):
        """Heading block should be stored separately, not in group.blocks."""
        blocks = [
            _cb("Chương 1. MỞ ĐẦU", BlockType.HEADING, heading_level=1,
                section_path=["Chương 1. MỞ ĐẦU"], page=5),
            _cb("Nội dung", page=5, section_path=["Chương 1. MỞ ĐẦU"]),
        ]
        groups = _group_by_heading(blocks)
        assert len(groups) == 1
        grp = groups[0]
        assert grp.heading_text == "Chương 1. MỞ ĐẦU"
        assert grp.heading_block is not None
        assert len(grp.blocks) == 1
        assert grp.blocks[0].raw_text == "Nội dung"

    def test_body_before_first_heading(self):
        blocks = [
            _cb("Preamble text", page=0),
            _cb("Chương 1. MỞ ĐẦU", BlockType.HEADING, heading_level=1,
                section_path=["Chương 1. MỞ ĐẦU"], page=5),
            _cb("Body", page=5, section_path=["Chương 1. MỞ ĐẦU"]),
        ]
        groups = _group_by_heading(blocks)
        assert len(groups) == 2
        assert groups[0].heading_block is None
        assert groups[0].blocks[0].raw_text == "Preamble text"
        assert groups[1].heading_block is not None


# ---------------------------------------------------------------------------
# Heading deduplication in chunk text
# ---------------------------------------------------------------------------

class TestHeadingDeduplication:
    def test_heading_appears_once_in_chunk_text(self):
        """The heading should appear exactly once in the chunk text."""
        blocks = [
            _cb("Chương 1. MỞ ĐẦU", BlockType.HEADING, heading_level=1,
                section_path=["Chương 1. MỞ ĐẦU"], page=5),
            _cb("Nội dung chương 1.", page=5,
                section_path=["Chương 1. MỞ ĐẦU"]),
        ]
        chunks = chunk_blocks(blocks, max_tokens=2000, min_tokens=1,
                              overlap_tokens=0, merge_short_threshold=1)
        assert len(chunks) >= 1
        text = chunks[0].text
        count = text.count("Chương 1. MỞ ĐẦU")
        assert count == 1, f"Heading appeared {count} times in chunk text: {text!r}"

    def test_heading_only_group(self):
        """A heading with no body should still produce a valid chunk."""
        blocks = [
            _cb("Chương 1. MỞ ĐẦU", BlockType.HEADING, heading_level=1,
                section_path=["Chương 1. MỞ ĐẦU"], page=5),
        ]
        chunks = chunk_blocks(blocks, max_tokens=2000, min_tokens=1,
                              overlap_tokens=0, merge_short_threshold=1)
        assert len(chunks) == 1
        assert "Chương 1. MỞ ĐẦU" in chunks[0].text


# ---------------------------------------------------------------------------
# Chunk metadata
# ---------------------------------------------------------------------------

class TestChunkMetadata:
    def test_section_path_from_heading(self):
        blocks = [
            _cb("Chương 2. JAVA", BlockType.HEADING, heading_level=1,
                section_path=["Chương 2. JAVA"], page=10),
            _cb("2.1. Biến", BlockType.HEADING, heading_level=2,
                section_path=["Chương 2. JAVA", "2.1. Biến"], page=10),
            _cb("Biến là vùng nhớ...", page=10,
                section_path=["Chương 2. JAVA", "2.1. Biến"]),
        ]
        chunks = chunk_blocks(blocks, max_tokens=2000, min_tokens=1,
                              overlap_tokens=0, merge_short_threshold=1)

        body_chunk = next(c for c in chunks if "Biến là vùng nhớ" in c.text)
        assert body_chunk.chapter == "Chương 2. JAVA"
        assert body_chunk.section == "2.1. Biến"
        assert body_chunk.section_path == ["Chương 2. JAVA", "2.1. Biến"]

    def test_page_range(self):
        blocks = [
            _cb("Chương 1. MỞ ĐẦU", BlockType.HEADING, heading_level=1,
                section_path=["Chương 1. MỞ ĐẦU"], page=5),
            _cb("Đoạn 1", page=5, section_path=["Chương 1. MỞ ĐẦU"]),
            _cb("Đoạn 2", page=7, section_path=["Chương 1. MỞ ĐẦU"]),
        ]
        chunks = chunk_blocks(blocks, max_tokens=2000, min_tokens=1,
                              overlap_tokens=0, merge_short_threshold=1)
        assert len(chunks) >= 1
        ch = chunks[0]
        assert ch.page_start == 5
        assert ch.page_end == 7

    def test_block_ids_include_heading(self):
        h = _cb("Chương 1. MỞ ĐẦU", BlockType.HEADING, heading_level=1,
                section_path=["Chương 1. MỞ ĐẦU"], page=5, block_id="h1")
        b = _cb("Body text", page=5, section_path=["Chương 1. MỞ ĐẦU"],
                block_id="b1")
        chunks = chunk_blocks([h, b], max_tokens=2000, min_tokens=1,
                              overlap_tokens=0, merge_short_threshold=1)
        assert "h1" in chunks[0].block_ids
        assert "b1" in chunks[0].block_ids

    def test_subject_propagated(self):
        """The ``subject`` kwarg should propagate to every chunk."""
        blocks = [
            _cb("Chương 1. MỞ ĐẦU", BlockType.HEADING, heading_level=1,
                section_path=["Chương 1. MỞ ĐẦU"], page=5),
            _cb("Nội dung chương 1.", page=5,
                section_path=["Chương 1. MỞ ĐẦU"]),
            _cb("Chương 2. BIẾN", BlockType.HEADING, heading_level=1,
                section_path=["Chương 2. BIẾN"], page=10),
            _cb("Nội dung chương 2.", page=10,
                section_path=["Chương 2. BIẾN"]),
        ]
        chunks = chunk_blocks(
            blocks, subject="Lập trình Java",
            max_tokens=2000, min_tokens=1,
            overlap_tokens=0, merge_short_threshold=1,
        )
        assert len(chunks) >= 2
        for ch in chunks:
            assert ch.subject == "Lập trình Java"

    def test_subject_default_empty(self):
        """Without ``subject``, the field stays empty (backward compatible)."""
        blocks = [
            _cb("Chương 1. MỞ ĐẦU", BlockType.HEADING, heading_level=1,
                section_path=["Chương 1. MỞ ĐẦU"], page=5),
            _cb("Body", page=5, section_path=["Chương 1. MỞ ĐẦU"]),
        ]
        chunks = chunk_blocks(blocks, max_tokens=2000, min_tokens=1,
                              overlap_tokens=0, merge_short_threshold=1)
        assert chunks[0].subject == ""
