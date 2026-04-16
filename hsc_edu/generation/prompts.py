"""Prompt templates for question generation."""

from __future__ import annotations

from hsc_edu.core.models import Chunk

SYSTEM_PROMPT = """\
Bạn là một giảng viên đại học đang chuẩn bị câu hỏi kiểm tra vấn đáp \
(oral exam / viva) cho sinh viên. Bạn PHẢI tuân thủ các nguyên tắc:

1. CHỈ dựa trên nội dung giáo trình được cung cấp bên dưới.
   KHÔNG sử dụng kiến thức ngoài giáo trình.
2. Câu hỏi phải rõ ràng, kiểm tra được sự hiểu biết (không phải nhớ máy móc).
3. Đáp án gợi ý phải ngắn gọn, chính xác, có trích dẫn chương/mục nguồn.
4. Phân loại mức độ khó: Nhận biết / Thông hiểu / Vận dụng / Vận dụng cao."""

GENERATION_TEMPLATE = """\
## Nội dung giáo trình (nguồn):

{chunks_content}

## Yêu cầu:

Hãy tạo {num_questions} câu hỏi vấn đáp cho phần nội dung trên.

Với mỗi câu hỏi, trả về đúng format JSON (một JSON array):
[
  {{
    "question": "Nội dung câu hỏi",
    "suggested_answer": "Đáp án gợi ý ngắn gọn",
    "difficulty": "Nhận biết | Thông hiểu | Vận dụng | Vận dụng cao",
    "source": "Chương/Mục/Trang nguồn",
    "bloom_level": "Remember | Understand | Apply | Analyze | Evaluate | Create",
    "keywords": ["từ khoá 1", "từ khoá 2"]
  }}
]

Đảm bảo:
- Câu hỏi đa dạng về mức độ khó
- Bao phủ các ý chính trong nội dung
- Đáp án bám sát giáo trình, có chỉ rõ nguồn"""


def _format_chunk(idx: int, chunk: Chunk) -> str:
    """Format a single chunk for inclusion in the prompt."""
    heading = " > ".join(chunk.section_path) if chunk.section_path else "(không có tiêu đề)"
    return (
        f"### Đoạn {idx + 1} — {heading} "
        f"(trang {chunk.page_start}–{chunk.page_end})\n\n"
        f"{chunk.text}"
    )


def build_prompt(
    chunks: list[Chunk],
    num_questions: int,
) -> tuple[str, str]:
    """Build the (system_prompt, user_prompt) pair for the LLM.

    Parameters
    ----------
    chunks:
        Selected chunks to include as context.
    num_questions:
        Number of questions to request.

    Returns
    -------
    tuple[str, str]
        ``(system_prompt, user_prompt)``
    """
    chunks_content = "\n\n---\n\n".join(
        _format_chunk(i, c) for i, c in enumerate(chunks)
    )
    user_prompt = GENERATION_TEMPLATE.format(
        chunks_content=chunks_content,
        num_questions=num_questions,
    )
    return SYSTEM_PROMPT, user_prompt
