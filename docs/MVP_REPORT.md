# Báo cáo MVP — HSC-Edu Phase 1

## 1. Tổng quan Pipeline

```
PDF → Extract → Classify → Chunk → Embed → Store → Retrieve → Generate
```

| Bước | Module | Mô tả |
|------|--------|-------|
| Extract (L1) | `hsc_edu.core.extraction` | PyMuPDF: tách blocks từ PDF, loại noise (số trang, header/footer) |
| Classify (L2) | `hsc_edu.core.classification` | Rule-based: heading detection, TOC filtering, block typing |
| Chunk (L4) | `hsc_edu.core.chunking` | Group by heading, split/merge theo token budget (max 1024 tokens) |
| Embed | `hsc_edu.storage.embedding` | Gemini `gemini-embedding-001` (768 dim), batch 20 texts, retry |
| Store | `hsc_edu.storage.ingest` | MongoDB (full chunk + metadata) + Qdrant Cloud (vector + payload) |
| Retrieve | `hsc_edu.storage.retrieval` | Semantic search (Qdrant) + metadata filter → fetch full chunk (MongoDB) |
| Generate | `hsc_edu.generation` | Hybrid chunk selection → prompt → Gemini 2.5 Flash → parse JSON |

## 2. Thống kê dữ liệu

| Metric | Java.pdf | C.pdf | Tổng |
|--------|----------|-------|------|
| Trang PDF | 241 | 102 | 343 |
| Blocks extracted | 2121 | 2328 | 4449 |
| Chunks | 322 | 115 | 437 |
| Avg tokens/chunk | ~549 | ~410 | ~513 |
| Chapters detected | 68 | 17 | 85 |

## 3. Kết quả Retrieval (Tuần 3)

5 câu hỏi ground truth → **Top-1 accuracy: 5/5 (100%)**

| Câu hỏi | Score | Đánh giá |
|----------|-------|----------|
| 4 nguyên tắc OOP (Java) | 0.79 | Tốt |
| Đa hình (Java) | 0.80 | Rất tốt |
| Thuật giải (C) | 0.73 | Trung bình |
| Kiểu dữ liệu C | 0.75 | Tốt |
| Thừa kế (cross-subject) | 0.79 | Rất tốt |

## 4. Kết quả sinh câu hỏi (Tuần 4)

*Phần này sẽ được cập nhật sau khi chạy notebook `04_generation_demo.ipynb`.*

### Mẫu câu hỏi tốt

*(Bổ sung sau khi chạy)*

### Mẫu câu hỏi chưa tốt

*(Bổ sung sau khi chạy)*

### Thống kê

- Tổng số câu hỏi sinh được: ___ (mục tiêu ≥ 50)
- Phân bố difficulty: Nhận biết / Thông hiểu / Vận dụng / Vận dụng cao
- Chapter coverage: ___/85 chapters

## 5. Nhận xét ban đầu

### Điểm mạnh

- Pipeline end-to-end hoạt động: từ PDF thô đến câu hỏi vấn đáp có đáp án
- Retrieval chính xác: top-1 đúng cho 100% câu hỏi ground truth
- Đồng bộ dữ liệu tốt: MongoDB ↔ Qdrant (437/437 chunks)
- Filter metadata (subject, chapter) hoạt động chính xác
- Retry mechanism cho cả embedding lẫn LLM generation

### Điểm yếu / Hạn chế

- 104 chunks có token_count < 64 (heading-only) → chunking chưa tối ưu
- 16 chunks thiếu chapter/section_path (phần mở đầu tài liệu)
- C.pdf: một số con số trong bảng bị mis-classify thành heading
- Rate limit Gemini free tier gây chậm khi xử lý nhiều chapters liên tục
- Chưa có OCR pipeline cho tài liệu scan

## 6. Ý tưởng cải thiện — Phase 2 (HSC Nâng cao)

1. **Chunking strategy**: Merge heading-only chunks vào chunk kế tiếp; tăng `min_tokens`
2. **Classification**: Thêm rule cho C.pdf patterns; xử lý phần mở đầu tài liệu tốt hơn
3. **Multi-format**: OCR pipeline (PaddleOCR/EasyOCR) cho tài liệu scan
4. **Evaluation tự động**: So sánh câu hỏi sinh ra với ground truth bằng semantic similarity
5. **Difficulty calibration**: Fine-tune prompt để phân bố difficulty cân bằng hơn
6. **Coverage tracking**: Đảm bảo mọi section trong syllabus đều có câu hỏi
7. **Interactive Q&A**: Module trả lời câu hỏi sinh viên dựa trên chunks (TECHNICAL_SPEC §3.3)
8. **API backend**: FastAPI endpoint cho sinh câu hỏi theo yêu cầu
