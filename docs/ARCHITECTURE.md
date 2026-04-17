# ARCHITECTURE — HSC-Edu System

## 1. Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HSC-Edu System Overview                         │
│                                                                        │
│  ┌──────────┐   ┌──────────────┐   ┌───────────┐   ┌───────────────┐  │
│  │  INPUT    │──▶│  PROCESSING  │──▶│  STORAGE  │──▶│   OUTPUT      │  │
│  │          │   │  PIPELINE    │   │           │   │               │  │
│  │ PDF/DOC  │   │  (5 Layers)  │   │ Vector DB │   │ Q&A Generator │  │
│  │ Upload   │   │              │   │ + MetaDB  │   │ + Retrieval   │  │
│  └──────────┘   └──────────────┘   └───────────┘   └───────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

Hệ thống gồm **4 khối chính** xử lý tuần tự:

1. **Input Layer** — Nhận giáo trình (PDF text-based / scan).
2. **Processing Pipeline** — 5 lớp HSC biến PDF thô thành chunk giàu ngữ cảnh.
3. **Storage Layer** — Lưu trữ vector embeddings + metadata có cấu trúc.
4. **Output Layer** — Retrieval + sinh câu hỏi/đáp án bằng LLM.

---

## 2. Processing Pipeline — 5 Lớp HSC chi tiết

```
PDF Input
    │
    ▼
┌─────────────────────────────────────────────────┐
│  LAYER 1: Document Extraction                    │
│  ─────────────────────────────────               │
│  • PDF text-based → PyMuPDF / pdfplumber         │
│  • PDF scan → OCR (PaddleOCR / Tesseract)        │
│  • Output: raw blocks {text, bbox, page, type}   │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│  LAYER 2: Layout Classification                  │
│  ─────────────────────────────────               │
│  • Phân loại block: heading / paragraph / table  │
│    / figure / caption / formula / list / footer  │
│  • Xác định heading level (H1→Chương, H2→Mục…)  │
│  • Lọc bỏ noise: header/footer lặp, page number │
│  • Output: classified_blocks[] với type + level  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│  LAYER 3: Semantic Linking                       │
│  ─────────────────────────────────               │
│  • Xây dựng Hierarchy Tree (Chương→Mục→Tiểu mục)│
│  • Reference Linking: "xem Hình 3.2" → Figure 3.2│
│  • Proximity Linking: text gần bảng/hình → link  │
│  • Table Continuation: merge bảng bị ngắt trang  │
│  • Output: semantic_graph (nodes + edges)        │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│  LAYER 4: Intelligent Chunking                   │
│  ─────────────────────────────────               │
│  • Chunk theo đơn vị logic (mục/tiểu mục)       │
│  • Giữ nguyên bảng như 1 chunk (không cắt ngang) │
│  • Hình → Vision LLM mô tả → chunk text         │
│  • Nếu chunk > max_tokens → split nhưng giữ     │
│    overlap + header context                       │
│  • Output: raw_chunks[] với content + metadata    │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
               Vector Store + MetaDB
```

---

## 3. Luồng dữ liệu chi tiết (Data Flow)

### 3.1 Ingestion Flow (Upload → Index)

```
Giảng viên upload PDF
       │
       ▼
[1] detect_pdf_type(file)
       │
       ├── text-based ──▶ extract_text_blocks(pymupdf/pdfplumber)
       │
       └── scan-based ──▶ ocr_pipeline(paddleocr)
                                │
                                ▼
                    [2] classify_blocks(blocks)
                          │
                          ▼
                    [3] build_semantic_graph(classified_blocks)
                          │
                          ▼
                    [4] create_chunks(semantic_graph, config)
                          │
                          ▼
                    [5] assemble_context(raw_chunks, semantic_graph)
                          │
                          ▼
                    [6] embed_and_store(final_chunks)
                          │
                          ├──▶ Vector Store (ChromaDB/Qdrant)
                          │         embeddings + chunk_id
                          │
                          └──▶ Metadata DB (SQLite/PostgreSQL)
                                    chunk metadata (subject, chapter,
                                    section, page, type, ...)
```

### 3.2 Query Flow (Sinh câu hỏi)

```
Giảng viên chọn: Môn + Chương + Số câu hỏi + Mức độ khó
       │
       ▼
[1] metadata_filter(subject, chapter, difficulty)
       │
       ▼
[2] retrieve_chunks(query, filters, top_k)
       │  ├── semantic search trên vector store
       │  └── filter theo metadata
       │
       ▼
[3] build_generation_prompt(chunks, config)
       │  ├── system prompt: vai trò giảng viên
       │  ├── context: nội dung các chunks
       │  └── instruction: sinh N câu hỏi + đáp án
       │
       ▼
[4] call_llm_api(prompt)
       │
       ▼
[5] parse_and_format(llm_response)
       │
       ▼
Output: Bộ câu hỏi + Đáp án gợi ý + Source (chương/trang)
```

### 3.3 Interactive Q&A Flow (Sinh viên hỏi đáp)

```
Sinh viên đặt câu hỏi tự do
       │
       ▼
[1] retrieve_chunks(question, subject_filter, top_k)
       │
       ▼
[2] build_qa_prompt(question, chunks)
       │
       ▼
[3] call_llm_api(prompt)
       │
       ▼
Output: Câu trả lời + Trích dẫn nguồn (chương, trang)
```

---

## 4. Component Architecture

```
hsc_edu/
│
├── core/                        # Lõi xử lý
│   ├── extraction/              # Layer 1: PDF → raw blocks
│   │   ├── text_extractor.py    #   PyMuPDF / pdfplumber
│   │   ├── ocr_extractor.py     #   PaddleOCR / Tesseract
│   │   └── pdf_detector.py      #   Phát hiện text-based vs scan
│   │
│   ├── classification/          # Layer 2: block → classified block
│   │   ├── block_classifier.py  #   heading/paragraph/table/figure...
│   │   └── heading_parser.py    #   Xác định heading level
│   │
│   ├── linking/                 # Layer 3: semantic graph
│   │   ├── hierarchy_builder.py #   Xây cây phân cấp heading
│   │   ├── reference_linker.py  #   Phát hiện "xem Hình X", "Bảng Y"
│   │   ├── proximity_linker.py  #   Link theo vị trí liền kề
│   │   └── table_merger.py      #   Merge bảng ngắt trang
│   │
│   ├── chunking/                # Layer 4: semantic graph → chunks
│   │   ├── structure_chunker.py #   Chunk theo đơn vị logic
│   │   ├── table_chunker.py     #   Xử lý bảng thành chunk
│   │   ├── figure_chunker.py    #   Hình → Vision LLM → text chunk
│   │   └── splitter.py          #   Split chunk quá dài
│   │
│   └── assembly/                # Layer 5: raw chunk → final chunk
│       ├── context_assembler.py #   Prepend header path + metadata
│       └── reference_injector.py#   Nhúng nội dung tham chiếu
│
├── storage/                     # Lưu trữ
│   ├── vector_store.py          #   ChromaDB / Qdrant wrapper
│   └── metadata_store.py        #   SQLite metadata queries
│
├── generation/                  # Sinh câu hỏi & Q&A
│   ├── question_generator.py    #   Sinh bộ câu hỏi từ chunks
│   ├── qa_chain.py              #   RAG chain cho hỏi đáp
│   └── prompts/                 #   Prompt templates
│       ├── question_gen.py      #     Prompt sinh câu hỏi
│       ├── answer_gen.py        #     Prompt sinh đáp án
│       └── qa_system.py         #     Prompt cho interactive Q&A
│
├── api/                         # Backend API (Phase 4)
│   ├── main.py                  #   FastAPI app
│   └── routes/
│       ├── upload.py            #   Upload & process PDF
│       ├── generate.py          #   Sinh câu hỏi
│       └── query.py             #   Hỏi đáp tự do
│
├── config/                      # Cấu hình
│   ├── settings.py              #   Cấu hình chung
│   └── subject_configs/         #   Config riêng theo môn (heading patterns...)
│       ├── default.yaml
│       └── ...
│
├── notebooks/                   # Jupyter notebooks demo/test
│   ├── 01_extraction_demo.ipynb
│   ├── 02_chunking_demo.ipynb
│   ├── 03_generation_demo.ipynb
│   └── 04_evaluation.ipynb
│
└── tests/                       # Unit tests
    ├── test_extraction.py
    ├── test_classification.py
    ├── test_chunking.py
    └── test_generation.py
```

---

## 5. Tích hợp bên ngoài (External Services)

| Service           | Vai trò                              | Khi nào dùng                  |
|-------------------|--------------------------------------|-------------------------------|
| OpenAI API        | Embedding + LLM sinh Q&A            | Mọi flow                     |
| Claude / Gemini   | LLM thay thế/bổ sung                | Tuỳ chọn                     |
| Vision LLM        | Mô tả hình ảnh, biểu đồ trong sách  | Layer 4 (figure_chunker)     |
| PaddleOCR         | OCR cho PDF scan                     | Layer 1 (ocr_extractor)      |

---

## 6. Nguyên tắc thiết kế (Design Principles)

1. **Modular & Pluggable**: Mỗi layer là module riêng, có thể thay thế/nâng cấp độc lập.
2. **Config-Driven**: Heading patterns, chunk size, prompt template đều cấu hình qua YAML/settings, không hard-code.
3. **Progressive Enhancement**: Hệ thống chạy được ở mức cơ bản (chỉ Layer 1+2+4+5), bổ sung Layer 3 (linking) và nâng cấp dần.
4. **Source Traceability**: Mọi chunk/câu hỏi đều truy ngược được về trang/chương/giáo trình gốc.
5. **Subject-Agnostic Core**: Pipeline lõi không gắn chặt với ngành nào; chỉ config heading pattern/metadata khác nhau theo môn.
