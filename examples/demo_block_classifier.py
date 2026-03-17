from __future__ import annotations

from pathlib import Path

from hsc_edu.core.classification import classify_blocks
from hsc_edu.core.extraction.text_extractor import extract_document
from hsc_edu.core.models import BlockType


# ---------------------------------------------------------------------------
# CẤU HÌNH NHANH — chỉ cần sửa các biến này rồi chạy file
# ---------------------------------------------------------------------------

PDF_PATH = Path("data/C.pdf")

START_PAGE = 15
END_PAGE: int | None = 17

MAX_HEADINGS = 30
MAX_PARAGRAPHS = 20


def main() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF không tồn tại: {PDF_PATH}")

    print(f"=== DEMO: {PDF_PATH} ===")
    print(
        f"Page range: start={START_PAGE}, "
        f"end={END_PAGE if END_PAGE is not None else 'tới cuối'}"
    )

    print("\n[1] Extracting blocks ...")
    blocks = extract_document(PDF_PATH)
    print(f"→ Tổng số block raw: {len(blocks)}")

    start_zero = max(START_PAGE - 1, 0)
    end_zero = END_PAGE - 1 if END_PAGE is not None else None

    if end_zero is not None and end_zero < start_zero:
        raise ValueError("END_PAGE phải >= START_PAGE")

    filtered_blocks = [
        b
        for b in blocks
        if b.page >= start_zero and (end_zero is None or b.page <= end_zero)
    ]

    print(
        f"→ Số block trong khoảng trang chọn: {len(filtered_blocks)} "
        f"(pages {start_zero + 1}–{(end_zero + 1) if end_zero is not None else 'end'})"
    )

    if not filtered_blocks:
        print("Không có block nào trong khoảng trang được chọn, dừng.")
        return

    print("\n[2] Classifying blocks ...")
    classified = classify_blocks(filtered_blocks)
    print(f"→ Đã phân loại {len(classified)} block")

    num_headings = sum(1 for c in classified if c.block_type == BlockType.HEADING)
    num_para = sum(1 for c in classified if c.block_type == BlockType.PARAGRAPH)
    num_special = sum(
        1
        for c in classified
        if c.block_type
        not in (BlockType.HEADING, BlockType.PARAGRAPH, BlockType.UNKNOWN)
    )

    print(
        f"\n[3] Summary:"
        f"\n  - Headings:   {num_headings}"
        f"\n  - Paragraphs: {num_para}"
        f"\n  - Special:    {num_special}"
    )

    print("\n=== HEADINGS (limited) ===")
    count_h = 0
    for cb in classified:
        if cb.block_type != BlockType.HEADING:
            continue
        first_line = cb.raw_text.splitlines()[0]
        print(
            f"[LEVEL {cb.heading_level}] "
            f"(page {cb.page + 1}) "
            f"{first_line[:160]}"
        )
        print(f"   path = {' > '.join(cb.section_path)}")
        print(f"   conf = {cb.classification_confidence}")
        print("-")
        count_h += 1
        if count_h >= MAX_HEADINGS:
            break
    if count_h == 0:
        print("(không có heading nào trong khoảng trang chọn)")

    print("\n=== PARAGRAPHS (limited) ===")
    count_p = 0
    for cb in classified:
        if cb.block_type != BlockType.PARAGRAPH:
            continue
        first_line = cb.raw_text.splitlines()[0]
        print(
            f"[PARA] page {cb.page + 1} "
            f"under {' > '.join(cb.section_path) if cb.section_path else '(no heading)'}"
        )
        print(f"   {first_line[:200]} ...")
        print("-")
        count_p += 1
        if count_p >= MAX_PARAGRAPHS:
            break
    if count_p == 0:
        print("(không có paragraph nào trong khoảng trang chọn)")


if __name__ == "__main__":
    main()
