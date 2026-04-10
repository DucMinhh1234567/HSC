# HSC-Edu

**Hierarchical Semantic Chunking** for educational textbooks — a RAG pipeline that turns PDF textbooks into retrieval-ready chunks for automatic Q&A generation.

## Quick start

### 1. Prerequisites

| Service | Purpose | How to get |
|---------|---------|------------|
| **Python 3.10+** | Runtime | [python.org](https://www.python.org/downloads/) |
| **MongoDB Community** | Chunk metadata & text storage | See setup below |
| **Qdrant Cloud** | Vector similarity search | See setup below |
| **Gemini API key** | Embeddings & LLM | See setup below |

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup MongoDB (local)

1. Download **MongoDB Community Server** from [mongodb.com/try/download/community](https://www.mongodb.com/try/download/community) (chon MSI installer cho Windows).
2. Cai dat voi tuy chon mac dinh — **Install as Service** de MongoDB tu dong chay khi khoi dong may.
3. Verify:

```bash
mongosh --eval "db.runCommand({ ping: 1 })"
```

Ket qua mong doi: `{ ok: 1 }`

MongoDB mac dinh chay tai `mongodb://localhost:27017` — khong can dang nhap cho dev local.

### 4. Setup Qdrant Cloud

1. Tao tai khoan tai [cloud.qdrant.io](https://cloud.qdrant.io/) (co free tier).
2. Tao **cluster** moi (chon region gan nhat).
3. Sau khi cluster san sang, lay:
   - **Cluster URL** (dang `https://xxx-xxx.cloud.qdrant.io:6333`)
   - **API Key** (tao trong tab "API Keys")

### 5. Setup Gemini API

1. Truy cap [Google AI Studio](https://aistudio.google.com/apikey).
2. Tao **API key** moi.
3. Ghi nho key — chi hien thi mot lan.

### 6. Tao file `.env`

Tao file `.env` tai thu muc goc cua project (file nay da duoc `.gitignore`):

```env
GOOGLE_API_KEY=your-gemini-api-key-here
QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key-here
MONGO_URI=mongodb://localhost:27017
```

### 7. Chay notebook

```bash
jupyter notebook notebooks/03_retrieval_demo.ipynb
```

Notebook se:
- Ingest `Java.pdf` va `C.pdf` (extract → classify → chunk → embed → store)
- Hien thi thong ke MongoDB va Qdrant
- Thu 5 cau hoi ground truth va hien thi ket qua retrieval

## Project structure

```
hsc_edu/
├── config/             # Settings, subject configs (YAML)
├── core/
│   ├── extraction/     # Layer 1: PDF → blocks
│   ├── classification/ # Layer 2: block → classified block
│   └── chunking/       # Layer 4: blocks → chunks
├── storage/
│   ├── embedding.py    # Gemini embedding client
│   ├── mongo_store.py  # MongoDB chunk store
│   ├── vector_store.py # Qdrant vector store
│   ├── ingest.py       # Orchestrator (embed + store)
│   └── retrieval.py    # Semantic search + fetch
notebooks/
├── 01_extraction_demo.ipynb
├── 02_chunking_demo.ipynb
└── 03_retrieval_demo.ipynb
tests/
data/
└── *.pdf               # Source textbooks
docs/                   # Architecture, specs, project plan
```

## Luu y quan trong

- **Vector dimension phai khop**: Qdrant collection dung `size=768` (mac dinh cua `gemini-embedding-001`). Neu doi model embedding, can xoa va tao lai collection.
- **Rate limit Gemini**: Free tier co gioi han ~1500 requests/phut. Pipeline tu dong batch 20 texts/request va retry khi bi rate-limited.
- **Dong bo Qdrant + MongoDB**: Ca hai duoc ghi trong cung ham `ingest_chunks()`. Neu mot ben loi, chay lai ingest de dong bo.
- **MongoDB khong can auth cho dev local**. Production nen bat authentication.
