"""Layer 3 — Semantic Linking.

Builds a :class:`SemanticGraph` capturing the heading hierarchy
between classified blocks.
"""

from __future__ import annotations

import logging

from hsc_edu.core.models import ClassifiedBlock, SemanticGraph

from hsc_edu.core.linking.hierarchy_builder import build_hierarchy_links

logger = logging.getLogger(__name__)

__all__ = ["build_semantic_graph"]


def build_semantic_graph(
    blocks: list[ClassifiedBlock],
) -> SemanticGraph:
    """Build a semantic graph with hierarchy links for a document's blocks."""
    graph = SemanticGraph()

    hierarchy_links = build_hierarchy_links(blocks)
    graph.add_links(hierarchy_links)
    logger.info("Hierarchy links: %d", len(hierarchy_links))

    logger.info("Semantic graph built: %d total links", len(graph))
    return graph
