# TECHNICAL SPECIFICATION — HSC-Edu

## 1. Metadata Schema

### 1.1 Document Metadata (khi upload giáo trình)

```python
DocumentMeta = {
    "doc_id": str,              # UUID tự sinh
    "title": str,               # "Giải tích 1"
    "subject": str,             # "Toán học"
    "faculty": str,             # "Khoa Toán - Tin"
    "authors": list[str],       # ["Nguyễn Văn A"]
    "edition": str,             # "Tái bản lần 3, 2023"
    "language": str,            # "vi" | "en"
    "total_pages": int,
    "pdf_type": str,            # "text-based" | "scanned" | "mixed"
    "upload_date": datetime,
    "uploaded_by": str,         # user ID
}
```

### 1.2 Block Metadata (sau Layer 1–2)

```python
BlockMeta = {
    "block_id": str,            # UUID
    "doc_id": str,              # FK → DocumentMeta
    "page": int,                # Trang chứa block
    "bbox": tuple,              # (x0, y0, x1, y1) toạ độ trên trang
    "block_type": str,          # "heading" | "paragraph" | "table"
                                # | "figure" | "caption" | "formula"
                                # | "list" | "example" | "exercise"
                                # | "definition" | "theorem" | "note"
    "heading_level": int|None,  # 1 (Phần/Chương), 2 (Mục), 3 (Tiểu mục)...
    "raw_text": str,            # Nội dung text thô
    "confidence": float|None,   # Confidence score (cho OCR)
}
```

### 1.3 Chunk Metadata (sau Layer 4–5 — lưu vào vector store)

```python
ChunkMeta = {
    "chunk_id": str,            # UUID
    "doc_id": str,              # FK → DocumentMeta
    "subject": str,             # Trùng với doc metadata, dùng để filter
    "chapter": str,             # "Chương 3: Đạo hàm"
    "section": str,             # "3.2 Đạo hàm riêng"
    "subsection": str|None,     # "3.2.1 Định nghĩa"
    "header_path": str,         # "Giải tích 1 > Chương 3 > 3.2 > 3.2.1"
    "chunk_type": str,          # "theory" | "example" | "exercise"
                                # | "definition" | "theorem" | "table"
                                # | "figure_description" | "mixed"
    "pages": list[int],         # [45, 46] nếu chunk span nhiều trang
    "token_count": int,         # Số token (dùng cho kiểm soát context window)
    "has_table": bool,
    "has_figure": bool,
    "has_formula": bool,
    "referenced_chunks": list[str],  # chunk_ids được tham chiếu (semantic link)
    "content": str,             # Nội dung chunk cuối cùng (đã assemble context)
}
```

---

## 2. Layer-by-Layer Technical Detail

### 2.1 Layer 1 — Document Extraction

**Mục tiêu**: Chuyển PDF thành danh sách `blocks` có text + toạ độ + trang.

**Logic xử lý**:

```python
def extract_document(pdf_path: str) -> list[BlockMeta]:
    pdf_type = detect_pdf_type(pdf_path)

    if pdf_type == "text-based":
        blocks = extract_with_pymupdf(pdf_path)
    elif pdf_type == "scanned":
        blocks = extract_with_ocr(pdf_path)
    else:  # mixed
        blocks = extract_mixed(pdf_path)

    blocks = filter_noise(blocks)  # loại header/footer lặp, page number
    return blocks
```

**Phát hiện PDF type**:

```python
def detect_pdf_type(pdf_path: str) -> str:
    """
    Mở PDF, thử trích text từ vài trang đầu.
    - Nếu text ≥ 50 ký tự/trang → text-based
    - Nếu hầu hết trang < 50 ký tự → scanned
    - Nếu lẫn lộn → mixed
    """
```

**Lọc noise**:
- Phát hiện header/footer lặp lại giữa các trang (so sánh text ở vùng trên/dưới).
- Loại bỏ page number (regex pattern: `^\d+$`, `^- \d+ -$`, `^Trang \d+$`).

---

### 2.2 Layer 2 — Layout Classification

**Mục tiêu**: Gán `block_type` và `heading_level` cho từng block.

**Heading Detection — Rule-based + configurable**:

```yaml
# config/subject_configs/default.yaml
heading_patterns:
  level_1:
    - regex: "^(CHƯƠNG|PHẦN|CHAPTER)\s+\d+"
    - regex: "^(Chương|Phần)\s+[IVXLCDM]+"
    - font_size_min: 16        # pt
    - is_bold: true
  level_2:
    - regex: "^\d+\.\d+\s+"   # 3.2 Đạo hàm
    - font_size_min: 13
    - is_bold: true
  level_3:
    - regex: "^\d+\.\d+\.\d+\s+"  # 3.2.1 Định nghĩa
    - font_size_min: 11
    - is_bold: true

special_block_patterns:
  definition: "^(Định nghĩa|Definition)\s+\d+"
  theorem: "^(Định lý|Theorem)\s+\d+"
  example: "^(Ví dụ|Example)\s+\d+"
  exercise: "^(Bài tập|Bài\s+\d+|Exercise)\s*\d*"
  note: "^(Chú ý|Ghi chú|Note|Remark)"
```

**Table Detection**:
- Dùng pdfplumber table finder hoặc bbox-based heuristic.
- Nếu block chứa nhiều ô theo lưới → table.

**Figure Detection**:
- Block là image object trong PDF.
- Hoặc vùng có bbox lớn nhưng ít/không text + gần caption "Hình X.Y".

---

### 2.3 Layer 3 — Semantic Linking

**Mục tiêu**: Xây đồ thị ngữ nghĩa trước khi chunk.

**3 loại link chính**:

```python
@dataclass
class SemanticLink:
    source_block_id: str
    target_block_id: str
    link_type: str        # "reference" | "proximity" | "hierarchy" | "continuation"
    confidence: float     # 0.0 - 1.0

def build_semantic_graph(blocks: list[BlockMeta]) -> SemanticGraph:
    graph = SemanticGraph()

    # 1. Hierarchy links (heading → children)
    graph.add_links(build_hierarchy_tree(blocks))

    # 2. Reference links ("xem Hình 3.2" → Figure 3.2)
    graph.add_links(find_reference_links(blocks))

    # 3. Proximity links (text liền kề table/figure)
    graph.add_links(find_proximity_links(blocks))

    # 4. Table continuation (bảng bị ngắt trang)
    graph.add_links(find_table_continuations(blocks))

    return graph
```

**Reference Pattern Regex (tiếng Việt + Anh)**:

```python
REFERENCE_PATTERNS = [
    r"[Xx]em\s+(Hình|Bảng|Bài tập|Định nghĩa|Định lý|Mục|Chương)\s+[\d.]+",
    r"[Tt]heo\s+(Định lý|Định nghĩa|Hệ quả|Bổ đề)\s+[\d.]+",
    r"[Tt]ại\s+(Bảng|Hình|Phụ lục)\s+[\d.]+",
    r"[Nn]hư\s+(đã trình bày|đề cập)\s+(ở|tại|trong)\s+(Mục|Chương)\s+[\d.]+",
    r"[Ss]ee\s+(Figure|Table|Section|Chapter|Theorem|Definition)\s+[\d.]+",
    r"[Aa]s\s+(shown|described|defined)\s+in\s+(Figure|Table|Section)\s+[\d.]+",
]
```

**Proximity Linking**:
- Nếu block B (table/figure) nằm ngay sau block A (paragraph) trên cùng trang hoặc trang liền kề, và A không có explicit reference → tạo proximity link.

**Table Continuation**:
- Nếu trang N kết thúc bằng bảng (block cuối cùng) VÀ trang N+1 bắt đầu bằng bảng (block đầu tiên) mà không có heading xen giữa → merge thành một entity.

---

### 2.4 Layer 4 — Intelligent Chunking

**Mục tiêu**: Tạo chunk logic, không cắt ngang ý nghĩa.

**Chiến lược chunking**:

```python
CHUNK_CONFIG = {
    "max_tokens": 1024,         # Ngưỡng tối đa cho 1 chunk
    "min_tokens": 64,           # Tránh chunk quá nhỏ
    "overlap_tokens": 128,      # Overlap khi buộc phải split chunk dài
    "merge_short_threshold": 100, # Merge chunk < 100 tokens vào chunk liền kề
}
```

**Logic chunking chính**:

```
Với mỗi section (mục) trong hierarchy tree:
   1. Thu thập tất cả block con thuộc section đó
   2. Nếu tổng tokens ≤ max_tokens:
        → Gộp thành 1 chunk
   3. Nếu tổng tokens > max_tokens:
        → Chia theo sub-section (nếu có)
        → Nếu vẫn vượt → split theo paragraph boundary + overlap
   4. Block loại "table":
        → Luôn giữ nguyên vẹn (1 bảng = 1 chunk)
        → Nếu bảng > max_tokens → giữ nguyên nhưng đánh dấu "large_table"
   5. Block loại "figure":
        → Gọi Vision LLM mô tả → text description thành 1 chunk
   6. Block loại "exercise" / "example":
        → Cố gắng gộp cùng phần lý thuyết liên quan (hoặc ít nhất
          giữ header_path trỏ về lý thuyết)
```

**Xử lý công thức toán**:
- Phase 1: Giữ nguyên text trích xuất (dù có thể bị lỗi).
- Phase 2+: Dùng Math OCR (vd: `pix2tex`, `nougat`) hoặc Vision LLM convert ảnh công thức → LaTeX.

---

### 2.5 Layer 5 — Context Assembly

**Mục tiêu**: Tạo `final_content` giàu ngữ cảnh cho mỗi chunk.

**Template lắp ráp**:

```python
def assemble_chunk(chunk: RawChunk, graph: SemanticGraph) -> FinalChunk:
    parts = []

    # 1. Header path
    parts.append(f"[Ngữ cảnh: {chunk.header_path}]")

    # 2. Chunk type hint
    parts.append(f"[Loại nội dung: {chunk.chunk_type}]")

    # 3. Referenced content (nếu chunk tham chiếu bảng/hình khác)
    for ref in graph.get_references(chunk.id):
        ref_content = get_block_content(ref.target_block_id)
        parts.append(f"[Nội dung tham chiếu - {ref.target_label}]: {ref_content}")

    # 4. Main content
    parts.append(chunk.raw_content)

    final_content = "\n\n".join(parts)
    return FinalChunk(
        content=final_content,
        metadata=chunk.metadata,
        token_count=count_tokens(final_content),
    )
```

**Ví dụ output chunk**:

```
[Ngữ cảnh: Giải tích 1 > Chương 3: Đạo hàm > 3.2 Đạo hàm riêng > 3.2.1 Định nghĩa]
[Loại nội dung: definition]

Định nghĩa 3.1. Cho hàm số f(x,y) xác định trên miền D ⊂ R².
Đạo hàm riêng của f theo biến x tại điểm (x₀, y₀) được định nghĩa:
∂f/∂x(x₀,y₀) = lim[Δx→0] [f(x₀+Δx, y₀) - f(x₀, y₀)] / Δx

Nếu giới hạn trên tồn tại và hữu hạn.

[Nội dung tham chiếu - Hình 3.2]: Hình 3.2 minh họa mặt cong z = f(x,y)
và tiếp tuyến theo phương x tại điểm (x₀, y₀, f(x₀,y₀)).
```

---

## 3. Prompt Design — Sinh câu hỏi vấn đáp

### 3.1 System Prompt

```
Bạn là một giảng viên đại học đang chuẩn bị câu hỏi kiểm tra vấn đáp
(oral exam / viva) cho sinh viên. Bạn PHẢI tuân thủ các nguyên tắc:

1. CHỈ dựa trên nội dung giáo trình được cung cấp bên dưới.
   KHÔNG sử dụng kiến thức ngoài giáo trình.
2. Câu hỏi phải rõ ràng, kiểm tra được sự hiểu biết (không phải nhớ máy móc).
3. Đáp án gợi ý phải ngắn gọn, chính xác, có trích dẫn chương/mục nguồn.
4. Phân loại mức độ khó: Nhận biết / Thông hiểu / Vận dụng / Vận dụng cao.
```

### 3.2 Generation Prompt Template

```
## Nội dung giáo trình (nguồn):

{chunks_content}

## Yêu cầu:

Hãy tạo {num_questions} câu hỏi vấn đáp cho phần nội dung trên.

Với mỗi câu hỏi, trả về đúng format JSON:
{{
  "question": "Nội dung câu hỏi",
  "suggested_answer": "Đáp án gợi ý ngắn gọn",
  "difficulty": "Nhận biết | Thông hiểu | Vận dụng | Vận dụng cao",
  "source": "Chương/Mục/Trang nguồn",
  "bloom_level": "Remember | Understand | Apply | Analyze | Evaluate | Create",
  "keywords": ["từ khoá 1", "từ khoá 2"]
}}

Đảm bảo:
- Câu hỏi đa dạng về mức độ khó
- Bao phủ các ý chính trong nội dung
- Đáp án bám sát giáo trình, có chỉ rõ nguồn
```

### 3.3 Q&A Interactive Prompt

```
## Vai trò:
Bạn là trợ giảng AI cho môn {subject}. Trả lời câu hỏi sinh viên
DỰA TRÊN NỘI DUNG GIÁO TRÌNH được cung cấp.

## Quy tắc:
- Nếu câu trả lời CÓ trong giáo trình → trả lời + trích dẫn nguồn.
- Nếu câu trả lời KHÔNG CÓ trong giáo trình → nói rõ "Nội dung này
  không có trong giáo trình được cung cấp" và gợi ý tham khảo thêm.
- Giải thích rõ ràng, phù hợp trình độ sinh viên đại học.

## Nội dung giáo trình liên quan:
{retrieved_chunks}

## Câu hỏi sinh viên:
{question}
```

---

## 4. Embedding & Retrieval Strategy

### 4.1 Embedding

| Phương án           | Model                             | Ưu điểm                        | Nhược điểm                |
|---------------------|-----------------------------------|---------------------------------|---------------------------|
| **Khuyến nghị MVP** | `text-embedding-3-small` (OpenAI) | Rẻ, nhanh, đa ngôn ngữ tốt    | Kém hơn large ở task khó  |
| Nâng cấp            | `text-embedding-3-large` (OpenAI) | Chính xác hơn                   | Đắt hơn 6x               |
| Self-hosted         | `bge-m3` hoặc `multilingual-e5`  | Miễn phí, kiểm soát hoàn toàn  | Cần GPU, tự maintain      |

### 4.2 Retrieval Strategy

```python
def retrieve_for_generation(
    subject: str,
    chapter: str | None,
    chunk_types: list[str] | None,
    query: str | None,
    top_k: int = 20,
) -> list[FinalChunk]:
    """
    Kết hợp metadata filter + semantic search:
    1. Filter theo subject (bắt buộc), chapter (tuỳ chọn), chunk_type (tuỳ chọn)
    2. Nếu có query → semantic search trong tập đã filter
       Nếu không có query → trả toàn bộ chunk trong filter (dùng cho "sinh câu hỏi
       theo chương" — không cần query cụ thể)
    3. Sắp xếp theo: relevance score (nếu semantic) hoặc thứ tự trang (nếu filter only)
    """
```

---

## 5. Evaluation Plan — Đánh giá chất lượng

### 5.1 Đánh giá Chunking

| Metric                    | Mô tả                                                     | Cách đo                             |
|---------------------------|------------------------------------------------------------|--------------------------------------|
| Context Completeness      | Chunk có chứa đủ ngữ cảnh để hiểu được không?              | Manual review 50 chunks/giáo trình   |
| Table Integrity           | Bảng có bị cắt ngang không?                                | Tự động: check chunk chứa bảng      |
| Reference Resolution      | "Xem Hình 3.2" có được resolve đúng không?                 | Tự động: count resolved vs total ref |
| Header Path Accuracy      | Header path có đúng cấu trúc giáo trình không?             | Manual review                        |

### 5.2 Đánh giá Q&A Generation

| Metric                     | Mô tả                                                     | Người đánh giá        |
|----------------------------|------------------------------------------------------------|------------------------|
| Factual Accuracy           | Câu hỏi & đáp án có đúng so với giáo trình không?          | Giảng viên bộ môn     |
| Relevance                  | Câu hỏi có phù hợp mục tiêu kiểm tra không?               | Giảng viên bộ môn     |
| Difficulty Distribution    | Phân bố mức độ khó có cân bằng không?                      | Thống kê tự động      |
| Coverage                   | Bộ câu hỏi có phủ hết nội dung chương/mục không?           | So sánh với syllabus   |
| Source Traceability        | Có thể truy ngược về đúng chương/trang không?              | Tự động kiểm tra      |

### 5.3 So sánh phương pháp (cho nghiên cứu)

```
Baseline: Fixed-size chunking (512 tokens, 128 overlap)
Proposed: HSC-Edu (hierarchical + semantic linking)

Thí nghiệm trên: ≥ 5 giáo trình, ≥ 3 bộ môn khác nhau

Metrics so sánh:
- Retrieval Precision@K & Recall@K (với bộ câu hỏi do GV tạo)
- Q&A accuracy (GV chấm trên thang 1–5)
- Context completeness score
- Table integrity rate
```
