"""Build hierarchy links from heading blocks to their child content blocks.

A hierarchy link connects a heading block to every non-heading block
that lives under it (shares the same ``section_path`` prefix).
"""

from __future__ import annotations

from hsc_edu.core.models import BlockType, ClassifiedBlock, LinkType, SemanticLink


def build_hierarchy_links(blocks: list[ClassifiedBlock]) -> list[SemanticLink]:
    """Return ``hierarchy`` links from headings to their children.

    For each heading block at level *L*, all subsequent non-heading blocks
    whose ``section_path`` starts with the heading's ``section_path`` are
    linked as children — until another heading of the same or higher level
    resets the scope.
    """
    links: list[SemanticLink] = []

    heading_stack: list[ClassifiedBlock] = []

    for block in blocks:
        if block.block_type == BlockType.HEADING and block.heading_level is not None:
            while (
                heading_stack
                and heading_stack[-1].heading_level is not None
                and heading_stack[-1].heading_level >= block.heading_level
            ):
                heading_stack.pop()
            heading_stack.append(block)
            continue

        for heading in heading_stack:
            if _is_child_of(heading.section_path, block.section_path):
                links.append(
                    SemanticLink(
                        source_block_id=heading.block_id,
                        target_block_id=block.block_id,
                        link_type=LinkType.HIERARCHY,
                        confidence=1.0,
                        label=heading.raw_text.split("\n", 1)[0].strip(),
                    )
                )

    return links


def _is_child_of(parent_path: list[str], child_path: list[str]) -> bool:
    """True if *child_path* starts with *parent_path* (prefix match)."""
    if len(parent_path) > len(child_path):
        return False
    return child_path[: len(parent_path)] == parent_path
