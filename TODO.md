## Checklist Phase 1 — HSC-Edu MVP

### 1. Chuẩn bị chung

- [V] Cài **Python 3.10+** và tạo **virtualenv** riêng cho project  
- [V] Cài Git và tạo repo (local hoặc GitHub)  
- [V] Đăng ký và lấy **API key LLM/Embedding** (OpenAI / Claude / Gemini)  
- [V] Chọn **1–2 giáo trình PDF text-based** để làm dataset ban đầu  
- [ ] Tạo file ghi chú nhỏ (vd. `notes/dataset.md`) mô tả:
  - [ ] Tên giáo trình, môn học
  - [ ] Số chương, có bảng/hình không
  - [ ] 5–10 đoạn nội dung + câu hỏi chuẩn do bạn/giảng viên biên soạn (ground truth)

---

### 2. Tuần 1 – Kiến trúc & Extraction cơ bản

- [ ] Tạo cấu trúc thư mục chính (theo `ARCHITECTURE.md`, tối thiểu):  
  - [ ] `core/extraction/`  
  - [ ] `core/chunking/`  
  - [ ] `storage/`  
  - [ ] `generation/`  
  - [ ] `config/`  
  - [ ] `notebooks/`  
- [ ] Cài các thư viện nền:
  - [ ] `pymupdf` (fitz), `pdfplumber`
  - [ ] `chromadb` (hoặc Qdrant client nếu dùng Qdrant)
  - [ ] SDK LLM (`openai` hoặc tương đương)
  - [ ] `python-dotenv`, `pydantic`, `pytest`
- [ ] Viết module **detect PDF type** (MVP có thể luôn trả về text-based)
- [ ] Viết module **text extraction**:
  - [ ] Hàm đọc PDF → trả về danh sách block `{text, page, bbox}`
  - [ ] Tạo notebook `01_extraction_demo.ipynb` để test: in ra các block theo trang

---

### 3. Tuần 2 – Heading detection & Chunking đơn giản

- [ ] Thiết kế **schema** cho:
  - [ ] `Block` (raw từ PDF)
  - [ ] `ClassifiedBlock` (có type: heading/paragraph/table/figure…)
  - [ ] `Chunk` (text + metadata cơ bản)
- [ ] Xác định **pattern heading** cho giáo trình:
  - [ ] Regex cho “Chương X”, “1.”, “1.1.”, “1.1.1”, v.v.
  - [ ] Lưu pattern vào file config (vd. `config/subject_configs/default.yaml`)
- [ ] Viết module **classification** (Layer 2 đơn giản):
  - [ ] Phân loại heading vs paragraph dựa vào regex + style cơ bản (nếu lấy được)
  - [ ] Bỏ qua header/footer lặp, số trang
- [ ] Viết module **chunking cơ bản**:
  - [ ] Gom paragraph theo từng heading thành 1 chunk logic
  - [ ] Nếu chunk quá dài: split theo đoạn, giữ lại tên heading ở đầu
- [ ] Tạo notebook `02_chunking_demo.ipynb`:
  - [ ] Chạy: PDF → blocks → classified_blocks → chunks
  - [ ] In ra ví dụ 10 chunk đầu tiên (kèm header path đơn giản)

---

### 4. Tuần 3 – Vector store & Retrieval

- [ ] Thiết kế **schema metadata** cho chunk (MVP):
  - [ ] `subject`, `chapter`, `section`, `page_start`, `page_end`, `type`
- [ ] Viết module **embed_and_store**:
  - [ ] Tạo embedding cho mỗi chunk (gọi API)
  - [ ] Lưu vào **vector store** (Chroma/Qdrant)
  - [ ] Lưu metadata vào DB đơn giản (SQLite hoặc ngay trong vector store)
- [ ] Viết hàm **retrieve_chunks(query, filters, top_k)**:
  - [ ] Cho phép filter theo `subject`, `chapter`
- [ ] Tạo notebook `03_retrieval_demo.ipynb`:
  - [ ] Thử 3–5 câu hỏi thủ công → kiểm tra các chunk được retrieve có hợp lý không

---

### 5. Tuần 4 – Sinh câu hỏi & Đánh giá sơ bộ

- [ ] Thiết kế **prompt sinh câu hỏi** (file `generation/prompts/question_gen.py`):
  - [ ] System: vai trò giảng viên
  - [ ] Context: nội dung các chunk
  - [ ] Instruction: sinh N câu hỏi + đáp án gợi ý + trích nguồn (chương/mục)
- [ ] Viết module **question_generator**:
  - [ ] Input: subject, chapter, số câu, mức độ khó (tạm thời có thể bỏ mức độ khó)
  - [ ] Flow: filter chunk → retrieve → build prompt → call LLM → parse output
- [ ] Tạo notebook `04_generation_demo.ipynb`:
  - [ ] Sinh ra ít nhất 50 câu hỏi từ 1 giáo trình
  - [ ] Đánh dấu (bằng tay) ~20 câu: **đúng/chưa tốt/sai** so với giáo trình
- [ ] Viết **báo cáo ngắn cho MVP** (trong `PROJECT_PLAN.md` hoặc file riêng):
  - [ ] Mô tả pipeline MVP đã chạy được
  - [ ] Một vài ví dụ câu hỏi tốt/xấu
  - [ ] Nhận xét ban đầu và ý tưởng cải thiện (Phase 2 – HSC nâng cao)

