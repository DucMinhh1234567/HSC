"""Group ClassifiedBlocks into semantic Chunks (Layer 4).

Strategy
--------
1. **Group by heading**: consecutive non-heading blocks that share the
   same ``section_path`` are grouped under their nearest heading.
2. **Split long groups**: if a group exceeds ``max_tokens``, it is
   split at paragraph boundaries.  Each sub-chunk keeps the heading
   text prepended so retrieval context is preserved.
3. **Merge short chunks**: chunks shorter than ``merge_short_threshold``
   tokens are folded into their predecessor when they belong to the
   same section.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import tiktoken

from hsc_edu.config.settings import settings
from hsc_edu.core.models import BlockType, Chunk, ClassifiedBlock

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

_ENCODER: tiktoken.Encoding | None = None


def _get_encoder() -> tiktoken.Encoding:
    global _ENCODER  # noqa: PLW0603
    if _ENCODER is None:
        _ENCODER = tiktoken.get_encoding("cl100k_base")
    return _ENCODER


def count_tokens(text: str) -> int:
    return len(_get_encoder().encode(text))


def _token_ids_to_safe_text(enc: tiktoken.Encoding, token_ids: list[int]) -> str:
    """Decode token IDs, replacing invalid UTF-8 sequences at truncation boundaries."""
    raw_bytes = b"".join(enc.decode_single_token_bytes(t) for t in token_ids)
    return raw_bytes.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Internal grouping structure
# ---------------------------------------------------------------------------


@dataclass
class _BlockGroup:
    """Accumulator for blocks under one heading.

    The heading block (if any) is stored separately from the body
    ``blocks`` so that ``full_text`` never duplicates the heading.
    """

    heading_text: str = ""
    heading_level: int | None = None
    heading_block: ClassifiedBlock | None = None
    section_path: list[str] = field(default_factory=list)
    blocks: list[ClassifiedBlock] = field(default_factory=list)
    doc_id: str = ""

    @property
    def body_text(self) -> str:
        return "\n\n".join(
            b.raw_text for b in self.blocks if b.raw_text.strip()
        )

    @property
    def full_text(self) -> str:
        parts: list[str] = []
        if self.heading_text:
            parts.append(self.heading_text)
        body = self.body_text
        if body:
            parts.append(body)
        return "\n\n".join(parts)

    @property
    def block_ids(self) -> list[str]:
        ids: list[str] = []
        if self.heading_block is not None:
            ids.append(self.heading_block.block_id)
        ids.extend(b.block_id for b in self.blocks)
        return ids

    @property
    def page_start(self) -> int:
        if self.heading_block is not None:
            if self.blocks:
                return min(self.heading_block.page, self.blocks[0].page)
            return self.heading_block.page
        return self.blocks[0].page if self.blocks else 0

    @property
    def page_end(self) -> int:
        if self.blocks:
            return self.blocks[-1].page
        if self.heading_block is not None:
            return self.heading_block.page
        return 0

    @property
    def dominant_block_type(self) -> str:
        types = [b.block_type for b in self.blocks]
        if not types:
            return BlockType.PARAGRAPH
        from collections import Counter
        return Counter(types).most_common(1)[0][0]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_blocks(
    blocks: list[ClassifiedBlock],
    *,
    max_tokens: int | None = None,
    min_tokens: int | None = None,
    overlap_tokens: int | None = None,
    merge_short_threshold: int | None = None,
) -> list[Chunk]:
    """Convert classified blocks into retrieval-ready :class:`Chunk` objects.

    Parameters
    ----------
    blocks:
        Layer 2 output — classified blocks in document order.
    max_tokens:
        Maximum tokens per chunk.  *None* → ``settings.chunking.max_tokens``.
    min_tokens:
        Minimum tokens per chunk.  Acts as the default threshold for merging
        short chunks when ``merge_short_threshold`` is not explicitly provided.
        *None* → ``settings.chunking.min_tokens``.
    overlap_tokens:
        Token overlap when splitting long groups.
    merge_short_threshold:
        Chunks below this token count are merged into their predecessor.
        *None* → ``settings.chunking.merge_short_threshold``, falling back to
        ``min_tokens`` if that is also unset.
    """
    cfg = settings.chunking
    max_tokens = max_tokens or cfg.max_tokens
    min_tokens = min_tokens or cfg.min_tokens
    overlap_tokens = overlap_tokens or cfg.overlap_tokens
    # merge_short_threshold falls back to min_tokens so the config value is
    # not silently ignored when no explicit override is provided.
    merge_short_threshold = merge_short_threshold or cfg.merge_short_threshold or min_tokens

    groups = _group_by_heading(blocks)
    raw_chunks = _groups_to_chunks(groups, max_tokens, overlap_tokens)
    merged = _merge_short_chunks(raw_chunks, merge_short_threshold)

    logger.info(
        "Chunked %d blocks → %d groups → %d raw chunks → %d final chunks",
        len(blocks),
        len(groups),
        len(raw_chunks),
        len(merged),
    )
    return merged


# ---------------------------------------------------------------------------
# Step 1: group consecutive blocks by heading
# ---------------------------------------------------------------------------


def _group_by_heading(blocks: list[ClassifiedBlock]) -> list[_BlockGroup]:
    """Split blocks into groups, each headed by a HEADING block.

    The heading block is stored in ``heading_block`` (not in ``blocks``)
    so that ``full_text`` never duplicates the heading text.
    """
    groups: list[_BlockGroup] = []
    current: _BlockGroup | None = None

    for block in blocks:
        if block.block_type == BlockType.HEADING:
            if current is not None:
                groups.append(current)
            current = _BlockGroup(
                heading_text=block.raw_text.strip(),
                heading_level=block.heading_level,
                heading_block=block,
                section_path=list(block.section_path),
                doc_id=block.doc_id,
            )
        else:
            if current is None:
                current = _BlockGroup(
                    section_path=list(block.section_path),
                    doc_id=block.doc_id,
                )
            current.blocks.append(block)

    if current is not None:
        groups.append(current)

    return groups


# ---------------------------------------------------------------------------
# Step 2: convert groups to chunks (split long ones)
# ---------------------------------------------------------------------------


def _groups_to_chunks(
    groups: list[_BlockGroup],
    max_tokens: int,
    overlap_tokens: int,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for grp in groups:
        full = grp.full_text
        tokens = count_tokens(full)

        if tokens <= max_tokens:
            chunks.append(_group_to_chunk(grp, full, tokens))
        else:
            chunks.extend(_split_group(grp, max_tokens, overlap_tokens))

    return chunks


def _group_to_chunk(grp: _BlockGroup, text: str, tokens: int) -> Chunk:
    chapter = grp.section_path[0] if grp.section_path else ""
    section = grp.section_path[-1] if grp.section_path else ""
    return Chunk(
        doc_id=grp.doc_id,
        text=text,
        block_ids=grp.block_ids,
        chapter=chapter,
        section=section,
        section_path=list(grp.section_path),
        page_start=grp.page_start,
        page_end=grp.page_end,
        block_type=grp.dominant_block_type,
        token_count=tokens,
    )


def _split_group(
    grp: _BlockGroup,
    max_tokens: int,
    overlap_tokens: int,
) -> list[Chunk]:
    """Split a long group at paragraph boundaries with heading prefix."""
    heading_prefix = grp.heading_text + "\n\n" if grp.heading_text else ""
    heading_tokens = count_tokens(heading_prefix) if heading_prefix else 0
    if heading_tokens >= max_tokens:
        heading_prefix = ""
        heading_tokens = 0

    budget = max_tokens - heading_tokens
    if budget < 1:
        budget = 1

    heading_blk = grp.heading_block
    body_blocks = grp.blocks
    if not body_blocks:
        text = grp.full_text
        tokens = count_tokens(text)
        if tokens > max_tokens:
            enc = _get_encoder()
            token_ids = enc.encode(text)[:max_tokens]
            text = _token_ids_to_safe_text(enc, token_ids)
            tokens = count_tokens(text)
            logger.warning(
                "Heading-only group exceeds max_tokens (%d > %d); truncated. "
                "doc_id=%r section_path=%r",
                count_tokens(grp.full_text),
                max_tokens,
                grp.doc_id,
                grp.section_path,
            )
        return [_group_to_chunk(grp, text, tokens)]

    id_to_block = {b.block_id: b for b in body_blocks}

    chunks: list[Chunk] = []
    buf_texts: list[str] = []
    buf_ids: list[str] = []
    buf_tokens = 0
    buf_page_start = body_blocks[0].page
    buf_page_end = body_blocks[0].page

    for blk in body_blocks:
        ptokens = count_tokens(blk.raw_text)

        if buf_tokens + ptokens > budget and buf_texts:
            chunk_text = heading_prefix + "\n\n".join(buf_texts)
            chunk_block_ids = list(buf_ids)
            if heading_blk is not None:
                chunk_block_ids = [heading_blk.block_id] + chunk_block_ids

            page_start = buf_page_start
            if heading_blk is not None:
                page_start = min(heading_blk.page, page_start)

            chunks.append(
                Chunk(
                    doc_id=grp.doc_id,
                    text=chunk_text,
                    block_ids=chunk_block_ids,
                    chapter=grp.section_path[0] if grp.section_path else "",
                    section=grp.section_path[-1] if grp.section_path else "",
                    section_path=list(grp.section_path),
                    page_start=page_start,
                    page_end=buf_page_end,
                    block_type=grp.dominant_block_type,
                    token_count=count_tokens(chunk_text),
                )
            )

            overlap_texts, overlap_ids, overlap_tok = _compute_overlap(
                buf_texts, buf_ids, overlap_tokens,
            )
            buf_texts = overlap_texts
            buf_ids = overlap_ids
            buf_tokens = overlap_tok
            if overlap_ids:
                buf_page_start = id_to_block[overlap_ids[0]].page
            else:
                buf_page_start = blk.page

        buf_texts.append(blk.raw_text)
        buf_ids.append(blk.block_id)
        buf_tokens += ptokens
        buf_page_end = blk.page

    if buf_texts:
        chunk_text = heading_prefix + "\n\n".join(buf_texts)
        chunk_block_ids = list(buf_ids)
        if heading_blk is not None:
            chunk_block_ids = [heading_blk.block_id] + chunk_block_ids

        page_start = buf_page_start
        if heading_blk is not None:
            page_start = min(heading_blk.page, page_start)

        chunks.append(
            Chunk(
                doc_id=grp.doc_id,
                text=chunk_text,
                block_ids=chunk_block_ids,
                chapter=grp.section_path[0] if grp.section_path else "",
                section=grp.section_path[-1] if grp.section_path else "",
                section_path=list(grp.section_path),
                page_start=page_start,
                page_end=buf_page_end,
                block_type=grp.dominant_block_type,
                token_count=count_tokens(chunk_text),
            )
        )

    return chunks


def _compute_overlap(
    texts: list[str],
    ids: list[str],
    overlap_tokens: int,
) -> tuple[list[str], list[str], int]:
    """Take paragraphs from the *end* of the buffer for overlap."""
    overlap_texts: list[str] = []
    overlap_ids: list[str] = []
    total = 0
    for t, bid in zip(reversed(texts), reversed(ids)):
        tok = count_tokens(t)
        if total + tok > overlap_tokens and overlap_texts:
            break
        overlap_texts.insert(0, t)
        overlap_ids.insert(0, bid)
        total += tok
    return overlap_texts, overlap_ids, total


# ---------------------------------------------------------------------------
# Step 3: merge very short chunks into predecessor
# ---------------------------------------------------------------------------


def _merge_short_chunks(
    chunks: list[Chunk],
    threshold: int,
) -> list[Chunk]:
    """Merge chunks below *threshold* tokens into the previous chunk."""
    if not chunks:
        return []

    merged: list[Chunk] = [chunks[0]]

    for ch in chunks[1:]:
        prev = merged[-1]
        same_section = prev.section_path == ch.section_path
        if ch.token_count < threshold and same_section:
            combined_text = prev.text + "\n\n" + ch.text
            merged[-1] = Chunk(
                doc_id=prev.doc_id,
                text=combined_text,
                block_ids=prev.block_ids + ch.block_ids,
                chapter=prev.chapter,
                section=prev.section,
                section_path=prev.section_path,
                page_start=prev.page_start,
                page_end=ch.page_end,
                block_type=prev.block_type,
                token_count=count_tokens(combined_text),
            )
        else:
            merged.append(ch)

    return merged