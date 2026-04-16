"""Unit tests for Layer 5 — Context Assembly."""

from __future__ import annotations

import pytest

from hsc_edu.core.models import (
    BlockType,
    ClassifiedBlock,
    Chunk,
    SemanticGraph,
)
from hsc_edu.core.assembly.context_assembler import assemble_chunks, _enrich_metadata


def _cb(
    raw_text: str,
    block_type: str = BlockType.PARAGRAPH,
    section_path: list[str] | None = None,
    page: int = 0,
    block_id: str = "",
) -> ClassifiedBlock:
    return ClassifiedBlock(
        page=page,
        bbox=(0, 0, 100, 20),
        raw_text=raw_text,
        block_type=block_type,
        section_path=section_path or [],
        block_id=block_id or raw_text[:12].replace(" ", "_"),
    )


def _chunk(
    text: str,
    block_ids: list[str] | None = None,
    section_path: list[str] | None = None,
    block_type: str = BlockType.PARAGRAPH,
) -> Chunk:
    return Chunk(
        text=text,
        block_ids=block_ids or [],
        section_path=section_path or [],
        block_type=block_type,
    )


# ---------------------------------------------------------------------------
# Metadata enrichment
# ---------------------------------------------------------------------------

class TestEnrichMetadata:
    def test_header_path_from_section_path(self):
        blocks = [_cb("text", block_id="b1")]
        block_map = {b.block_id: b for b in blocks}
        chunk = _chunk("text", block_ids=["b1"],
                        section_path=["Chương 1", "1.1 Mục"])
        _enrich_metadata(chunk, block_map)
        assert chunk.header_path == "Chương 1 > 1.1 Mục"

    def test_chunk_type_from_theorem(self):
        blocks = [_cb("Định lý 1.1", block_type=BlockType.THEOREM,
                       block_id="t1")]
        block_map = {b.block_id: b for b in blocks}
        chunk = _chunk("Định lý 1.1...", block_ids=["t1"],
                        block_type=BlockType.THEOREM)
        _enrich_metadata(chunk, block_map)
        assert chunk.chunk_type == "theorem"

    def test_has_formula_detected(self):
        blocks = [_cb("∂f/∂x = lim Δx→0", block_id="p1")]
        block_map = {b.block_id: b for b in blocks}
        chunk = _chunk("∂f/∂x = lim Δx→0", block_ids=["p1"])
        _enrich_metadata(chunk, block_map)
        assert chunk.has_formula is True


# ---------------------------------------------------------------------------
# Full Assembly
# ---------------------------------------------------------------------------

class TestAssembleChunks:
    def test_content_has_context_prefix(self):
        blocks = [_cb("Nội dung", block_id="p1")]

        chunk = _chunk(
            "Nội dung",
            block_ids=["p1"],
            section_path=["Chương 3", "3.2 Đạo hàm"],
        )
        graph = SemanticGraph()
        result = assemble_chunks([chunk], graph, blocks)

        assert len(result) == 1
        content = result[0].content
        assert content.startswith("[Ngữ cảnh: Chương 3 > 3.2 Đạo hàm]")
        assert "[Loại nội dung:" in content
        assert "Nội dung" in content

    def test_empty_chunks_no_error(self):
        result = assemble_chunks([], SemanticGraph(), [])
        assert result == []

    def test_token_count_updated(self):
        blocks = [_cb("Nội dung", block_id="p1")]
        chunk = _chunk("Nội dung", block_ids=["p1"],
                        section_path=["Chương 1"])

        graph = SemanticGraph()
        result = assemble_chunks([chunk], graph, blocks)
        assert result[0].token_count > 0
