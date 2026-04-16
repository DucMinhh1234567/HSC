# PROJECT PLAN — Hierarchical Semantic Chunking for Educational Textbooks

## 1. Tổng quan dự án

### 1.1 Tên dự án

**HSC-Edu** — Hệ thống Hierarchical Semantic Chunking cho giáo trình đại học, phục vụ sinh bộ câu hỏi vấn đáp tự động bằng RAG.

### 1.2 Mục tiêu

- Xây dựng pipeline xử lý giáo trình (PDF text-based & scan) thành các chunk **giàu ngữ cảnh phân cấp**.
- Lưu trữ vector cho phép truy vấn **theo chương/mục/chủ đề/loại nội dung**.
- Tự động sinh **bộ câu hỏi + đáp án gợi ý** phục vụ kiểm tra vấn đáp, bám sát giáo trình.
- Đảm bảo tính **đa ngành** — hỗ trợ nhiều bộ môn khác nhau với cùng pipeline.

### 1.3 Đối tượng sử dụng


| Vai trò    | Cách dùng chính                                               |
| ---------- | ------------------------------------------------------------- |
| Giảng viên | Upload giáo trình → sinh bộ câu hỏi vấn đáp → chỉnh sửa/duyệt |
| Sinh viên  | Ôn tập theo bộ câu hỏi, hỏi đáp nội dung giáo trình           |
| Quản trị   | Quản lý kho giáo trình, metadata, theo dõi sử dụng            |


### 1.4 Phạm vi (Scope)

- **Trong phạm vi (In-scope)**:
  - Xử lý PDF text-based (có hình ảnh, bảng).
  - Xử lý PDF scan (OCR).
  - Chunking phân cấp bảo toàn cấu trúc giáo trình.
  - Semantic linking cơ bản (tham chiếu hình, bảng, mục).
  - Sinh câu hỏi & đáp án gợi ý từ nội dung chunk.
  - API ngoài cho LLM (OpenAI / Claude / Gemini).
- **Ngoài phạm vi (Out-of-scope) — có thể mở rộng sau**:
  - Giao diện web hoàn chỉnh (giai đoạn đầu dùng CLI/notebook).
  - Đa ngôn ngữ nâng cao (giai đoạn đầu tập trung tiếng Việt + Anh).
  - Fine-tuning model riêng.

---

## 2. Lộ trình (Roadmap) — 4 giai đoạn

### Phase 1: Foundation & MVP (Tuần 1–4)

> Mục tiêu: Pipeline chạy được end-to-end trên 1–2 giáo trình text-based.


| Tuần | Công việc                                                        | Deliverable                            |
| ---- | ---------------------------------------------------------------- | -------------------------------------- |
| 1    | Thiết kế kiến trúc, metadata schema, cấu trúc project            | `ARCHITECTURE.md`, `TECHNICAL_SPEC.md` |
| 1–2  | Xây module PDF Extraction (text-based) + heading detection       | `extraction/` module                   |
| 2–3  | Xây module Hierarchical Chunking (chunk theo cấu trúc + context) | `chunking/` module                     |
| 3    | Tích hợp vector store + retrieval cơ bản                         | `vectorstore/` module                  |
| 3–4  | Xây module sinh câu hỏi (prompt engineering + LLM API)           | `generation/` module                   |
| 4    | Test end-to-end trên 2 giáo trình, đánh giá sơ bộ                | Demo notebook + báo cáo sơ bộ          |


### Phase 2: HSC Enhancement (Tuần 5–8)

> Mục tiêu: Nâng cấp chunking — semantic linking, xử lý bảng/hình tốt hơn.


| Tuần | Công việc                                                         | Deliverable                         |
| ---- | ----------------------------------------------------------------- | ----------------------------------- |
| 5    | Semantic linking: regex tham chiếu ("xem Hình X", "Bảng Y")       | Linking logic trong chunking module |
| 5–6  | Table extraction nâng cao (pdfplumber / camelot)                  | Table-aware chunking                |
| 6–7  | Figure/chart handling: Vision LLM mô tả hình                      | Image description pipeline          |
| 7–8  | Context injection: tự động embed header path + referenced content | Context-enriched chunks             |
| 8    | Đánh giá so sánh: fixed-size vs HSC-lite trên cùng bộ giáo trình  | Báo cáo benchmark Phase 2           |


### Phase 3: OCR & Multi-format (Tuần 9–12)

> Mục tiêu: Mở rộng cho PDF scan, cải thiện chất lượng toàn diện.


| Tuần  | Công việc                                                         | Deliverable               |
| ----- | ----------------------------------------------------------------- | ------------------------- |
| 9–10  | Tích hợp OCR pipeline (PaddleOCR / Tesseract / EasyOCR)           | OCR module                |
| 10–11 | Layout detection cho scan PDF (heading, paragraph, table regions) | Layout-aware OCR output   |
| 11    | Xử lý công thức toán (LaTeX OCR hoặc Vision LLM)                  | Math formula handling     |
| 12    | Test trên ≥ 5 giáo trình (text + scan), nhiều bộ môn              | Báo cáo đánh giá đa ngành |


### Phase 4: Production & Research Report (Tuần 13–16)

> Mục tiêu: Hoàn thiện hệ thống, viết báo cáo nghiên cứu, demo.


| Tuần  | Công việc                                                  | Deliverable                |
| ----- | ---------------------------------------------------------- | -------------------------- |
| 13    | Xây API backend (FastAPI) cho upload + sinh Q&A            | REST API                   |
| 13–14 | Giao diện đơn giản (Streamlit / Gradio)                    | Web UI prototype           |
| 14–15 | Đánh giá bởi giảng viên (chất lượng câu hỏi, độ chính xác) | Phiếu đánh giá + phân tích |
| 15–16 | Viết báo cáo nghiên cứu, so sánh phương pháp, kết luận     | Báo cáo đề tài hoàn chỉnh  |
| 16    | Demo sản phẩm, bàn giao                                    | Slide + demo live          |


---

## 3. Milestone & Tiêu chí hoàn thành


| Milestone | Mô tả                         | Tiêu chí                                                      |
| --------- | ----------------------------- | ------------------------------------------------------------- |
| M1        | MVP chạy end-to-end           | Sinh được ≥ 50 câu hỏi từ 2 giáo trình, có đáp án gợi ý       |
| M2        | HSC nâng cao hoạt động        | Benchmark cho thấy HSC tốt hơn fixed-size về context accuracy |
| M3        | Hỗ trợ PDF scan               | Xử lý được ≥ 3 giáo trình scan với chất lượng chunk chấp nhận |
| M4        | Hệ thống hoàn chỉnh + báo cáo | Demo chạy, có đánh giá từ GV, báo cáo nghiên cứu hoàn thiện   |


---

## 4. Rủi ro & Giải pháp


| Rủi ro                                         | Mức ảnh hưởng | Giải pháp                                                        |
| ---------------------------------------------- | ------------- | ---------------------------------------------------------------- |
| PDF scan chất lượng thấp → OCR sai nhiều       | Cao           | Ưu tiên text-based trước; dùng OCR tốt + post-processing         |
| Giáo trình cấu trúc không đồng nhất giữa môn   | Trung bình    | Metadata schema linh hoạt; cho phép config heading pattern/môn   |
| Công thức toán bị hỏng khi extract             | Trung bình    | Dùng Math OCR hoặc Vision LLM fallback                           |
| Chi phí API LLM cao khi scale nhiều giáo trình | Trung bình    | Cache kết quả; batch processing; chọn model phù hợp theo task    |
| Câu hỏi sinh ra sai/lệch giáo trình            | Cao           | Prompt chặt chẽ; luôn kèm source chunk; GV review trước khi dùng |


---

## 5. Công nghệ chính (Tech Stack dự kiến)


| Thành phần      | Công nghệ                                                      |
| --------------- | -------------------------------------------------------------- |
| Ngôn ngữ        | Python 3.10+                                                   |
| PDF Extraction  | PyMuPDF (fitz), pdfplumber, unstructured                       |
| OCR             | PaddleOCR / Tesseract / EasyOCR                                |
| Chunking        | Custom HSC pipeline (tự xây)                                   |
| Embedding       | OpenAI text-embedding-3-small/large hoặc sentence-transformers |
| Vector Store    | ChromaDB (MVP) → Qdrant/Weaviate (production)                  |
| LLM API         | OpenAI GPT-4o / Claude 3.5 / Gemini 1.5                        |
| Orchestration   | LangChain (nhẹ, dùng cho chain/prompt template)                |
| Backend API     | FastAPI                                                        |
| Frontend        | Streamlit / Gradio (prototype)                                 |
| Version Control | Git + GitHub/GitLab                                            |


