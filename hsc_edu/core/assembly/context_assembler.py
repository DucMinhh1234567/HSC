"""Assemble final chunk content with context header and type hints (Layer 5).

Each chunk's ``content`` field is populated with a rich text that
includes the navigation path, content type label, and the original text.
"""

from __future__ import annotations

import logging
import re

from hsc_edu.core.models import (
    BLOCK_TYPE_TO_CHUNK_TYPE,
    BlockType,
    ClassifiedBlock,
    Chunk,
    SemanticGraph,
)
from hsc_edu.core.chunking.text_chunker import count_tokens

logger = logging.getLogger(__name__)

_FORMULA_HINTS = re.compile(
    r"\\frac|\\sum|\\int|\\lim|\\partial|∂|∑|∫|→|≥|≤|≠|∈|⊂|⊃|∀|∃|α|β|γ|δ|ε|θ|λ|μ|σ|φ|ω"
)


def assemble_chunks(
    chunks: list[Chunk],
    graph: SemanticGraph,
    blocks: list[ClassifiedBlock],
) -> list[Chunk]:
    """Enrich every chunk with assembled ``content`` and metadata.

    Parameters
    ----------
    chunks:
        Raw chunks from Layer 4.
    graph:
        Semantic graph from Layer 3.
    blocks:
        Full list of classified blocks.

    Returns
    -------
    list[Chunk]
        The same chunk objects, mutated in place, with ``content``,
        ``header_path``, ``chunk_type``, and ``has_formula`` populated.
    """
    block_map: dict[str, ClassifiedBlock] = {b.block_id: b for b in blocks}

    for chunk in chunks:
        _enrich_metadata(chunk, block_map)
        _assemble_content(chunk)

    logger.info("Assembled context for %d chunks", len(chunks))
    return chunks


def _enrich_metadata(
    chunk: Chunk,
    block_map: dict[str, ClassifiedBlock],
) -> None:
    """Populate ``header_path``, ``chunk_type``, and ``has_formula``."""
    if chunk.section_path:
        chunk.header_path = " > ".join(chunk.section_path)

    chunk.chunk_type = BLOCK_TYPE_TO_CHUNK_TYPE.get(chunk.block_type, "mixed")

    constituent_types: set[str] = set()
    for bid in chunk.block_ids:
        blk = block_map.get(bid)
        if blk is None:
            continue
        constituent_types.add(blk.block_type)

    if _FORMULA_HINTS.search(chunk.text):
        chunk.has_formula = True

    if len(constituent_types - {BlockType.HEADING}) > 1:
        chunk.chunk_type = "mixed"


def _assemble_content(chunk: Chunk) -> None:
    """Build the ``content`` field with context prefix."""
    parts: list[str] = []

    if chunk.header_path:
        parts.append(f"[Ngữ cảnh: {chunk.header_path}]")

    parts.append(f"[Loại nội dung: {chunk.chunk_type}]")

    parts.append(chunk.text)

    chunk.content = "\n\n".join(parts)
    chunk.token_count = count_tokens(chunk.content)
