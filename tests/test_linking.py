"""Unit tests for Layer 3 — Semantic Linking (hierarchy only)."""

from __future__ import annotations

import pytest

from hsc_edu.core.models import (
    BlockType,
    ClassifiedBlock,
    LinkType,
    SemanticGraph,
)
from hsc_edu.core.linking.hierarchy_builder import build_hierarchy_links
from hsc_edu.core.linking import build_semantic_graph


def _cb(
    raw_text: str,
    block_type: str = BlockType.PARAGRAPH,
    heading_level: int | None = None,
    section_path: list[str] | None = None,
    page: int = 0,
    block_id: str | None = None,
    bbox: tuple[float, float, float, float] = (0, 0, 100, 20),
) -> ClassifiedBlock:
    kwargs: dict = dict(
        page=page,
        bbox=bbox,
        raw_text=raw_text,
        block_type=block_type,
        heading_level=heading_level,
        section_path=section_path or [],
    )
    if block_id is not None:
        kwargs["block_id"] = block_id
    return ClassifiedBlock(**kwargs)


# ---------------------------------------------------------------------------
# Hierarchy Builder
# ---------------------------------------------------------------------------

class TestHierarchyBuilder:
    def test_heading_links_to_children(self):
        blocks = [
            _cb("Chương 1. MỞ ĐẦU", BlockType.HEADING, heading_level=1,
                section_path=["Chương 1. MỞ ĐẦU"], block_id="h1"),
            _cb("Đoạn nội dung 1", section_path=["Chương 1. MỞ ĐẦU"],
                block_id="p1"),
            _cb("Đoạn nội dung 2", section_path=["Chương 1. MỞ ĐẦU"],
                block_id="p2"),
        ]
        links = build_hierarchy_links(blocks)
        assert len(links) == 2
        assert all(lk.link_type == LinkType.HIERARCHY for lk in links)
        assert all(lk.source_block_id == "h1" for lk in links)
        targets = {lk.target_block_id for lk in links}
        assert targets == {"p1", "p2"}

    def test_nested_headings(self):
        blocks = [
            _cb("Chương 1", BlockType.HEADING, heading_level=1,
                section_path=["Chương 1"], block_id="h1"),
            _cb("1.1 Mục", BlockType.HEADING, heading_level=2,
                section_path=["Chương 1", "1.1 Mục"], block_id="h2"),
            _cb("Nội dung mục 1.1",
                section_path=["Chương 1", "1.1 Mục"], block_id="p1"),
        ]
        links = build_hierarchy_links(blocks)
        source_ids = {(lk.source_block_id, lk.target_block_id) for lk in links}
        assert ("h1", "p1") in source_ids
        assert ("h2", "p1") in source_ids

    def test_empty_blocks(self):
        assert build_hierarchy_links([]) == []


# ---------------------------------------------------------------------------
# Full build_semantic_graph
# ---------------------------------------------------------------------------

class TestBuildSemanticGraph:
    def test_graph_contains_hierarchy(self):
        blocks = [
            _cb("Chương 1. MỞ ĐẦU", BlockType.HEADING, heading_level=1,
                section_path=["Chương 1. MỞ ĐẦU"], block_id="h1"),
            _cb("Nội dung", section_path=["Chương 1. MỞ ĐẦU"],
                block_id="p1"),
        ]
        graph = build_semantic_graph(blocks)
        assert len(graph) >= 1
        hierarchy = graph.get_links_by_type(LinkType.HIERARCHY)
        assert len(hierarchy) >= 1

    def test_graph_is_semantic_graph_instance(self):
        graph = build_semantic_graph([])
        assert isinstance(graph, SemanticGraph)
