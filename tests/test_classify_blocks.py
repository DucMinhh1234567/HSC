"""Unit tests for classify_blocks and TOC filtering."""

from __future__ import annotations

import pytest

from hsc_edu.core.classification.block_classifier import (
    _detect_toc_pages,
    _get_heading_patterns,
    _get_special_patterns,
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

    def test_multiline_trailing_page_number(self):
        assert _is_toc_entry("5.4. ĐÓNG GÓI VÀ CÁC PHƯƠNG THỨC TRUY NHẬP \n75")

    def test_multiline_trailing_page_number_with_spaces(self):
        assert _is_toc_entry("Chương 10. THÀNH VIÊN LỚP \n 164")

    def test_dots_in_middle_of_multiline(self):
        assert _is_toc_entry("1.1. FOO ......... 12\nbar")

    def test_real_heading_no_dots(self):
        assert not _is_toc_entry("Chương 1. MỞ ĐẦU")

    def test_section_number_no_dots(self):
        assert not _is_toc_entry("1.1. KHÁI NIỆM CƠ BẢN")

    def test_plain_paragraph(self):
        assert not _is_toc_entry("Đây là một đoạn văn bản thông thường.")

    def test_few_dots_not_enough(self):
        assert not _is_toc_entry("Xem trang 12.. đúng không?")

    def test_dots_without_trailing_number(self):
        assert not _is_toc_entry("Xem mục 12... (xem thêm)")

    def test_single_line_no_newline_not_trailing(self):
        assert not _is_toc_entry("Chương 10. THÀNH VIÊN LỚP")


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

    def test_multiline_toc_entries_neutralized(self):
        """TOC entries with trailing page number on second line."""
        blocks = [
            _block("5.4. ĐÓNG GÓI VÀ CÁC PHƯƠNG THỨC TRUY NHẬP \n75", page=1),
            _block("Chương 10. THÀNH VIÊN LỚP\n164", page=2),
        ]
        result = classify_blocks(blocks)
        for cb in result:
            assert cb.block_type == BlockType.PARAGRAPH, (
                f"Multiline TOC entry misclassified: {cb.raw_text!r}"
            )

    def test_mixed_toc_pages_all_neutralized(self):
        """Simulate Java.pdf TOC spanning pages 0-3 with mixed patterns.

        Some entries have dots, some have trailing-newline numbers,
        and some have no recognizable marker at all (caught by page
        detection because they sit on known TOC pages).
        """
        blocks = [
            _block("Mục lục", page=0),
            _block("Chương 1. MỞ ĐẦU ............7", page=0),
            _block("1.1. KHÁI NIỆM CƠ BẢN ........... 12", page=0),
            _block("5.1. PHƯƠNG THỨC VÀ TRẠNG THÁI ĐỐI TƯỢNG\n70", page=1),
            _block("5.4. ĐÓNG GÓI\n75", page=1),
            _block("7.8. GỌI PHIÊN BẢN PHƯƠNG THỨC CỦA LỚP CHA\n114", page=1),
            _block("Chương 10. THÀNH VIÊN LỚP\n164", page=2),
            _block("Chương 13. LẬP TRÌNH TỔNG QUÁT", page=3),
            _block("13.3. CÁC CẤU TRÚC DỮ LIỆU TỔNG QUÁT\n220", page=3),
            # Real content starts at page 11
            _block("Chương 1. MỞ ĐẦU", page=11),
            _block("1.1. KHÁI NIỆM CƠ BẢN", page=11),
            _block("Nội dung thực sự về khái niệm cơ bản.", page=12),
        ]
        result = classify_blocks(blocks)

        for cb in result[:9]:
            assert cb.block_type == BlockType.PARAGRAPH, (
                f"TOC block on page {cb.page} leaked as {cb.block_type}: "
                f"{cb.raw_text[:60]!r}"
            )

        real_ch1 = result[9]
        assert real_ch1.block_type == BlockType.HEADING
        assert real_ch1.section_path == ["Chương 1. MỞ ĐẦU"]

        real_sec = result[10]
        assert real_sec.block_type == BlockType.HEADING
        assert real_sec.section_path == ["Chương 1. MỞ ĐẦU", "1.1. KHÁI NIỆM CƠ BẢN"]

        body = result[11]
        assert body.section_path == ["Chương 1. MỞ ĐẦU", "1.1. KHÁI NIỆM CƠ BẢN"]

    def test_no_toc_no_impact(self):
        """When there are no TOC entries, _detect_toc_pages returns empty."""
        blocks = [
            _block("Chương 1. MỞ ĐẦU", page=5),
            _block("1.1. Giới thiệu", page=5),
            _block("Nội dung", page=6),
        ]
        result = classify_blocks(blocks)
        assert result[0].block_type == BlockType.HEADING
        assert result[1].block_type == BlockType.HEADING


# ---------------------------------------------------------------------------
# _detect_toc_pages
# ---------------------------------------------------------------------------

class TestDetectTocPages:
    def test_anchor_pages_detected(self):
        blocks = [
            _block("Chương 1. MỞ ĐẦU ............7", page=0),
            _block("1.1. FOO ........... 12", page=0),
            _block("Chương 2. BAR\n20", page=1),
            _block("Chương 1. MỞ ĐẦU", page=5),
        ]
        pats = _get_heading_patterns()
        spats = _get_special_patterns()
        toc = _detect_toc_pages(blocks, pats, spats)
        assert 0 in toc
        assert 1 in toc
        assert 5 not in toc

    def test_gap_pages_with_high_density_included(self):
        """Page between anchors with >=2 heading matches is included."""
        blocks = [
            _block("Chương 1. MỞ ĐẦU ............7", page=0),
            _block("Chương 10. FOO", page=2),
            _block("Chương 11. BAR", page=2),
            _block("13.3. DỮ LIỆU\n220", page=3),
        ]
        pats = _get_heading_patterns()
        spats = _get_special_patterns()
        toc = _detect_toc_pages(blocks, pats, spats)
        assert 0 in toc
        assert 2 in toc
        assert 3 in toc

    def test_empty_when_no_toc_entries(self):
        blocks = [
            _block("Chương 1. MỞ ĐẦU", page=5),
            _block("Nội dung", page=5),
        ]
        pats = _get_heading_patterns()
        spats = _get_special_patterns()
        toc = _detect_toc_pages(blocks, pats, spats)
        assert len(toc) == 0
