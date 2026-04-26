# RAG Learning Lab

A local educational web app for learning the full Retrieval-Augmented Generation (RAG) pipeline hands-on — every stage visible and interactive.

Upload documents, tune chunking strategies, inspect embeddings, watch retrieval scoring, and trace the exact prompt sent to the LLM before you see the answer.

## What it does

| Panel | What you learn |
|---|---|
| **Documents** | Upload PDF/DOCX/TXT or crawl a blog URL; organise into folders |
| **Chunking Lab** | Compare fixed-size, recursive, and semantic chunking strategies side-by-side |
| **Embeddings** | Generate OpenAI embeddings, visualise them in 2-D (PCA scatter plot), compare cosine similarity |
| **Chat** | Ask questions; see retrieved chunks, relevance scores, the assembled prompt, and token cost |
| **Metrics** | Session stats — tokens used, cost, query latency |
| **Tutorial** | Built-in guided walkthrough of the full pipeline |

## Stack

- **Backend:** FastAPI · ChromaDB · OpenAI SDK · Python 3.9+
- **Frontend:** React 18 · TypeScript · Vite · Tailwind CSS

## Prerequisites

- Python 3.9+
- Node.js 18+
- An OpenAI API key

## Setup

### 1. Clone

```bash
git clone https://github.com/<your-username>/rag-learning-lab.git
cd rag-learning-lab
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

uvicorn main:app --reload --port 8000
```

Backend runs at `http://localhost:8000` · Swagger UI: `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

## Usage

1. **Documents** — upload files or crawl a blog URL; assign them to folders
2. **Chunking Lab** — pick a strategy and chunk your documents; browse the result
3. **Embeddings** — generate embeddings; explore the scatter plot
4. **Chat** — ask a question and inspect the full RAG pipeline in real time

## Running tests

```bash
cd backend
pytest tests/ -v
```

## Project structure

```
backend/
├── api/           # FastAPI routers (documents, chunks, embeddings, chat, folders, metrics)
├── models/        # Pydantic models
├── services/      # Business logic (chunkers, embeddings, LLM, vector store, web crawler)
├── tests/         # Unit tests + RAG evaluation suite
├── persistence.py # In-memory data store
└── main.py

frontend/
└── src/
    ├── api/           # Typed API client
    ├── components/    # React components (chat, chunks, documents, embeddings, tutorial, …)
    └── types/         # TypeScript types
```

## Notes

- All data is stored in memory (ChromaDB) and resets on backend restart.
- The web crawler supports public blogs; heavy-traffic sites may rate-limit or block requests.
- Semantic chunking uses sentence-transformers and is slower than fixed-size chunking.
