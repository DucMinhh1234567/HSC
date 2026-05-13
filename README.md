# HSC-Edu

**Hierarchical Semantic Chunking** for RAG systems

This strategy of chunking groups text into units that stay coherent in meaning and align with how a document is organized, rather than slicing it at fixed lengths. In **retrieval-augmented generation (RAG)**, that usually improves what gets retrieved: the model sees context that matches real sections and topics, which can reduce noise and irrelevant hits compared with naive chunking. This repository implements one such approach end to end; the sections below cover how to run it locally.

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

1. Download **MongoDB Community Server** from [mongodb.com/try/download/community](https://www.mongodb.com/try/download/community).
2. Install with default options — enable **Install as Service** so MongoDB starts automatically on boot.
3. Verify:

```bash
mongosh --eval "db.runCommand({ ping: 1 })"
```

Expected output: `{ ok: 1 }`

By default MongoDB runs at `mongodb://localhost:27017`.

### 4. Setup Qdrant Cloud

1. Create an account at [cloud.qdrant.io](https://cloud.qdrant.io/).
2. Create a **new cluster**.
3. Once the cluster is ready, obtain:
   - **Cluster URL** (format `https://xxx-xxx.cloud.qdrant.io:6333`)
   - **API Key**

### 5. Setup Gemini API

1. Open [Google AI Studio](https://aistudio.google.com/apikey).
2. Create a **new API key**.

### 6. Create the `.env` file

Create a `.env` file in the project root (this file is already listed in `.gitignore`):

```env
GOOGLE_API_KEY=your-gemini-api-key-here
QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key-here
MONGO_URI=mongodb://localhost:27017
```

### 7. Run the notebook

```bash
jupyter notebook notebooks/03_retrieval_demo.ipynb
```

The notebook will:

- Ingest `Java.pdf` and `C.pdf` (extract → classify → chunk → embed → store)
- Show MongoDB and Qdrant statistics
- Run 5 ground-truth queries and display retrieval results

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

## TODO

- **Images and tables**: extend the pipeline to extract, represent, and store figures and tabular content.
- **Semantic linking for figures and tables**: link images and tables to surrounding narrative and headings so retrieval can surface the right visual or table context together with related text.
