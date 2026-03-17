"""Unit tests for classify_blocks and TOC filtering."""

from __future__ import annotations

import pytest

from hsc_edu.core.classification.block_classifier import (
    _is_toc_entry,
    classify_blocks,
    reset_config_cache,
)
from hsc_edu.core.models import Block, BlockType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _block(raw_text: str, page: int = 0) -> Block:
    """Create a minimal Block for testing."""
    return Block(page=page, bbox=(0, 0, 100, 20), raw_text=raw_text)


@pytest.fixture(autouse=True)
def _fresh_cache():
    """Reset classifier caches before each test."""
    reset_config_cache()
    yield
    reset_config_cache()


# ---------------------------------------------------------------------------
# _is_toc_entry
# ---------------------------------------------------------------------------

class TestIsTocEntry:
    def test_dots_with_page_number(self):
        assert _is_toc_entry("Chương 1. MỞ ĐẦU ............7")

    def test_long_dots_with_spaced_number(self):
        assert _is_toc_entry("1.1. KHÁI NIỆM CƠ BẢN ................................................ 12")

    def test_real_heading_no_dots(self):
        assert not _is_toc_entry("Chương 1. MỞ ĐẦU")

    def test_section_number_no_dots(self):
        assert not _is_toc_entry("1.1. KHÁI NIỆM CƠ BẢN")

    def test_plain_paragraph(self):
        assert not _is_toc_entry("Đây là một đoạn văn bản thông thường.")

    def test_few_dots_not_enough(self):
        assert not _is_toc_entry("Xem trang 12.. đúng không?")


# ---------------------------------------------------------------------------
# classify_blocks — heading vs paragraph
# ---------------------------------------------------------------------------

class TestClassifyBlocks:
    def test_heading_detected(self):
        blocks = [_block("Chương 1. MỞ ĐẦU", page=5)]
        result = classify_blocks(blocks)
        assert len(result) == 1
        assert result[0].block_type == BlockType.HEADING
        assert result[0].heading_level == 1

    def test_paragraph_detected(self):
        blocks = [_block("Đây là nội dung bình thường.", page=5)]
        result = classify_blocks(blocks)
        assert len(result) == 1
        assert result[0].block_type == BlockType.PARAGRAPH

    def test_section_path_builds_correctly(self):
        blocks = [
            _block("Chương 1. MỞ ĐẦU", page=5),
            _block("1.1. Tổng quan", page=5),
            _block("Nội dung tổng quan...", page=6),
            _block("1.2. Chi tiết", page=7),
            _block("Nội dung chi tiết...", page=7),
        ]
        result = classify_blocks(blocks)
        assert result[0].section_path == ["Chương 1. MỞ ĐẦU"]
        assert result[1].section_path == ["Chương 1. MỞ ĐẦU", "1.1. Tổng quan"]
        assert result[2].section_path == ["Chương 1. MỞ ĐẦU", "1.1. Tổng quan"]
        assert result[3].section_path == ["Chương 1. MỞ ĐẦU", "1.2. Chi tiết"]
        assert result[4].section_path == ["Chương 1. MỞ ĐẦU", "1.2. Chi tiết"]


# ---------------------------------------------------------------------------
# classify_blocks — TOC contamination prevention
# ---------------------------------------------------------------------------

class TestTocContamination:
    def test_toc_entries_become_paragraphs(self):
        """Lines with dot-leaders should NOT be classified as headings."""
        blocks = [
            _block("Chương 1. MỞ ĐẦU ............7", page=0),
            _block("1.1. KHÁI NIỆM CƠ BẢN .............. 12", page=0),
            _block("Chương 2. NGÔN NGỮ ................... 20", page=0),
        ]
        result = classify_blocks(blocks)
        for cb in result:
            assert cb.block_type == BlockType.PARAGRAPH, (
                f"TOC entry misclassified as {cb.block_type}: {cb.raw_text!r}"
            )

    def test_toc_does_not_pollute_section_stack(self):
        """Real heading after TOC should start a fresh section path."""
        blocks = [
            _block("Chương 1. MỞ ĐẦU ............7", page=0),
            _block("Chương 5. KẾ THỪA ................... 50", page=0),
            _block("Chương 13. COLLECTIONS ............. 120", page=0),
            _block("Chương 1. MỞ ĐẦU", page=5),
            _block("Nội dung chương 1", page=5),
        ]
        result = classify_blocks(blocks)

        real_heading = result[3]
        assert real_heading.block_type == BlockType.HEADING
        assert real_heading.section_path == ["Chương 1. MỞ ĐẦU"]

        body = result[4]
        assert body.section_path == ["Chương 1. MỞ ĐẦU"]

    def test_real_headings_still_detected_after_toc(self):
        blocks = [
            _block("Mục lục", page=0),
            _block("Chương 1. MỞ ĐẦU ............7", page=0),
            _block("Chương 1. MỞ ĐẦU", page=5),
            _block("1.1. Giới thiệu", page=5),
            _block("Nội dung giới thiệu", page=6),
        ]
        result = classify_blocks(blocks)
        ch1 = result[2]
        assert ch1.block_type == BlockType.HEADING
        assert ch1.heading_level == 1

        sec11 = result[3]
        assert sec11.block_type == BlockType.HEADING
        assert sec11.heading_level == 2
        assert sec11.section_path == ["Chương 1. MỞ ĐẦU", "1.1. Giới thiệu"]
