# RAG Learning Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zbudować lokalną aplikację webową RAG Learning Lab — pełny pipeline RAG z transparentnym UI edukacyjnym pokazującym każdy etap przetwarzania.

**Architecture:** Backend FastAPI (Python 3.11+) obsługuje parsowanie dokumentów, chunking, embeddingi przez OpenAI API i ChromaDB jako lokalny vector store, streaming LLM przez SSE. Frontend React+Vite+TypeScript+Tailwind+shadcn/ui z panelami: Dokumenty → Chunking → Embeddings → Chat/Retrieval/Prompt → Metryki.

**Tech Stack:** Python 3.11+, FastAPI, ChromaDB, OpenAI SDK, tiktoken, scikit-learn/UMAP, PyPDF2, python-docx | React 18, Vite, TypeScript, TailwindCSS, shadcn/ui, Recharts, Lucide Icons

---

## Struktura plików

```
RAG/
├── backend/
│   ├── main.py                        # FastAPI app, CORS, router mounting
│   ├── requirements.txt
│   ├── .env.example
│   ├── api/
│   │   ├── documents.py               # POST /upload, GET /, GET /{id}, DELETE /{id}
│   │   ├── chunks.py                  # POST /generate, GET /{document_id}
│   │   ├── embeddings.py              # POST /generate, GET /visualize, GET /similarity
│   │   ├── chat.py                    # POST /chat (SSE), GET /retrieval, GET /prompt
│   │   └── metrics.py                 # GET /session, DELETE /reset
│   ├── services/
│   │   ├── document_parser.py         # parse_pdf, parse_docx, parse_txt
│   │   ├── chunkers/
│   │   │   ├── __init__.py
│   │   │   ├── fixed_size.py          # chunk_fixed_size(text, size, overlap)
│   │   │   ├── recursive.py           # chunk_recursive(text, separators, size)
│   │   │   └── semantic.py            # chunk_semantic(text)
│   │   ├── vector_store.py            # ChromaDB wrapper: add, query, delete, list
│   │   ├── embeddings_service.py      # embed_texts(), embed_query()
│   │   ├── retrieval_service.py       # retrieve(query, k), last_retrieval state
│   │   ├── prompt_builder.py          # build_prompt(system, chunks, query), token counts
│   │   └── llm_service.py             # stream_chat(prompt), session_metrics state
│   ├── models/
│   │   ├── document.py                # DocumentMeta, DocumentDetail Pydantic models
│   │   ├── chunk.py                   # Chunk, ChunkRequest, ChunkResponse models
│   │   └── metrics.py                 # SessionMetrics, QueryMetrics models
│   └── tests/
│       ├── test_document_parser.py
│       ├── test_chunkers.py
│       ├── test_prompt_builder.py
│       └── test_token_counter.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── components.json                # shadcn/ui config
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                    # Layout + routing between panels
│       ├── api/
│       │   └── client.ts              # Typed fetch wrappers for all endpoints
│       ├── types/
│       │   └── index.ts               # TypeScript interfaces matching backend models
│       ├── hooks/
│       │   ├── useDocuments.ts
│       │   ├── useChunks.ts
│       │   ├── useEmbeddings.ts
│       │   └── useChat.ts
│       └── components/
│           ├── layout/
│           │   ├── Header.tsx
│           │   ├── Sidebar.tsx
│           │   └── Footer.tsx
│           ├── documents/
│           │   ├── DocumentManager.tsx
│           │   ├── UploadZone.tsx
│           │   └── DocumentList.tsx
│           ├── chunks/
│           │   ├── ChunkingLab.tsx
│           │   ├── StrategySelector.tsx
│           │   └── ChunkViewer.tsx
│           ├── embeddings/
│           │   ├── EmbeddingExplorer.tsx
│           │   └── ScatterPlot.tsx
│           ├── chat/
│           │   ├── ChatInterface.tsx
│           │   ├── RetrievalPanel.tsx
│           │   └── PromptBuilderPanel.tsx
│           └── metrics/
│               └── MetricsPanel.tsx
└── docs/
    └── superpowers/
        └── plans/
            └── 2026-03-29-rag-learning-lab.md
```

---

## Faza 1: Scaffolding projektu

### Task 1: Inicjalizacja backendu Python

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/main.py`

- [ ] **Step 1: Utwórz `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9
python-dotenv==1.0.1
PyPDF2==3.0.1
python-docx==1.1.2
tiktoken==0.7.0
openai==1.51.0
chromadb==0.5.15
scikit-learn==1.5.2
umap-learn==0.5.6
numpy==1.26.4
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 2: Utwórz `backend/.env.example`**

```
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4o-mini
CHROMA_PERSIST_DIR=./chroma_data
```

- [ ] **Step 3: Utwórz `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="RAG Learning Lab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Zainstaluj zależności i uruchom**

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Oczekiwany wynik: `http://localhost:8000/health` zwraca `{"status": "ok"}`

- [ ] **Step 5: Commit**

```bash
git init
git add backend/
git commit -m "feat: backend scaffolding — FastAPI + deps"
```

---

### Task 2: Inicjalizacja frontendu React

**Files:**
- Create: `frontend/` (Vite scaffold)
- Create: `frontend/src/types/index.ts`

- [ ] **Step 1: Utwórz projekt Vite**

```bash
cd RAG
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss@3 postcss autoprefixer
npx tailwindcss init -p
npm install lucide-react recharts
npm install @radix-ui/react-slot class-variance-authority clsx tailwind-merge
```

- [ ] **Step 2: Skonfiguruj `frontend/tailwind.config.ts`**

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 3: Zastąp `frontend/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --border: 214.3 31.8% 91.4%;
    --primary: 221.2 83.2% 53.3%;
    --primary-foreground: 210 40% 98%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --radius: 0.5rem;
  }
}

body {
  @apply bg-background text-foreground;
}
```

- [ ] **Step 4: Utwórz `frontend/src/types/index.ts`**

```typescript
export interface DocumentMeta {
  id: string;
  name: string;
  size_bytes: number;
  page_count: number | null;
  upload_date: string;
  char_count: number;
}

export interface DocumentDetail extends DocumentMeta {
  raw_text: string;
}

export interface Chunk {
  id: string;
  document_id: string;
  content: string;
  index: number;
  char_count: number;
  token_count: number;
  start_char: number;
  end_char: number;
}

export interface ChunkRequest {
  document_id: string;
  strategy: "fixed" | "recursive" | "semantic";
  chunk_size?: number;
  overlap?: number;
  separators?: string[];
}

export interface ChunkStats {
  count: number;
  avg_length: number;
  min_length: number;
  max_length: number;
  overlap_pct: number;
}

export interface ChunkResponse {
  chunks: Chunk[];
  stats: ChunkStats;
}

export interface EmbeddingPoint {
  chunk_id: string;
  document_id: string;
  document_name: string;
  x: number;
  y: number;
  content_preview: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  document_name: string;
  content: string;
  score: number;
  rank: number;
}

export interface PromptData {
  system_message: string;
  context_block: string;
  user_query: string;
  full_prompt: string;
  token_counts: {
    system: number;
    context: number;
    query: number;
    total: number;
  };
}

export interface QueryMetrics {
  query_id: string;
  timestamp: string;
  query: string;
  chunking_ms: number;
  embedding_ms: number;
  retrieval_ms: number;
  llm_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
}

export interface SessionMetrics {
  total_queries: number;
  total_tokens: number;
  total_cost_usd: number;
  queries: QueryMetrics[];
}

export type Panel = "documents" | "chunks" | "embeddings" | "chat" | "metrics";
```

- [ ] **Step 5: Uruchom i sprawdź**

```bash
cd frontend
npm run dev
```

Oczekiwany wynik: `http://localhost:5173` ładuje się bez błędów.

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: frontend scaffolding — React+Vite+TS+Tailwind"
```

---

## Faza 2: Backend — parsowanie dokumentów

### Task 3: Modele Pydantic

**Files:**
- Create: `backend/models/document.py`
- Create: `backend/models/chunk.py`
- Create: `backend/models/metrics.py`
- Create: `backend/models/__init__.py`

- [ ] **Step 1: Utwórz `backend/models/__init__.py`** (pusty)

- [ ] **Step 2: Utwórz `backend/models/document.py`**

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentMeta(BaseModel):
    id: str
    name: str
    size_bytes: int
    page_count: Optional[int] = None
    upload_date: str
    char_count: int


class DocumentDetail(DocumentMeta):
    raw_text: str
```

- [ ] **Step 3: Utwórz `backend/models/chunk.py`**

```python
from pydantic import BaseModel
from typing import List, Optional


class Chunk(BaseModel):
    id: str
    document_id: str
    content: str
    index: int
    char_count: int
    token_count: int
    start_char: int
    end_char: int


class ChunkRequest(BaseModel):
    document_id: str
    strategy: str = "fixed"  # "fixed" | "recursive" | "semantic"
    chunk_size: int = 500
    overlap: int = 50
    separators: Optional[List[str]] = None


class ChunkStats(BaseModel):
    count: int
    avg_length: float
    min_length: int
    max_length: int
    overlap_pct: float


class ChunkResponse(BaseModel):
    chunks: List[Chunk]
    stats: ChunkStats
```

- [ ] **Step 4: Utwórz `backend/models/metrics.py`**

```python
from pydantic import BaseModel
from typing import List


class TokenCounts(BaseModel):
    system: int
    context: int
    query: int
    total: int


class PromptData(BaseModel):
    system_message: str
    context_block: str
    user_query: str
    full_prompt: str
    token_counts: TokenCounts


class QueryMetrics(BaseModel):
    query_id: str
    timestamp: str
    query: str
    chunking_ms: float = 0.0
    embedding_ms: float
    retrieval_ms: float
    llm_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class SessionMetrics(BaseModel):
    total_queries: int
    total_tokens: int
    total_cost_usd: float
    queries: List[QueryMetrics]
```

- [ ] **Step 5: Commit**

```bash
git add backend/models/
git commit -m "feat: Pydantic models — document, chunk, metrics"
```

---

### Task 4: Parser dokumentów + testy

**Files:**
- Create: `backend/services/document_parser.py`
- Create: `backend/tests/test_document_parser.py`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Napisz testy**

Utwórz `backend/tests/__init__.py` (pusty), następnie `backend/tests/test_document_parser.py`:

```python
import pytest
from services.document_parser import parse_txt, parse_pdf, parse_docx
import tempfile
import os


def test_parse_txt_basic():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Hello world\nSecond line")
        path = f.name
    try:
        result = parse_txt(path)
        assert result["text"] == "Hello world\nSecond line"
        assert result["char_count"] == len("Hello world\nSecond line")
        assert result["page_count"] is None
    finally:
        os.unlink(path)


def test_parse_txt_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        path = f.name
    try:
        result = parse_txt(path)
        assert result["text"] == ""
        assert result["char_count"] == 0
    finally:
        os.unlink(path)
```

- [ ] **Step 2: Uruchom testy — oczekiwany FAIL**

```bash
cd backend
pytest tests/test_document_parser.py -v
```

Oczekiwany wynik: `ImportError: No module named 'services.document_parser'`

- [ ] **Step 3: Utwórz `backend/services/__init__.py`** (pusty)

- [ ] **Step 4: Utwórz `backend/services/document_parser.py`**

```python
import os
from typing import Dict, Any, Optional
import PyPDF2
from docx import Document


def parse_txt(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return {"text": text, "char_count": len(text), "page_count": None}


def parse_pdf(path: str) -> Dict[str, Any]:
    text_parts = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        page_count = len(reader.pages)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
    text = "\n".join(text_parts)
    return {"text": text, "char_count": len(text), "page_count": page_count}


def parse_docx(path: str) -> Dict[str, Any]:
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)
    return {"text": text, "char_count": len(text), "page_count": None}


def parse_document(path: str, filename: str) -> Dict[str, Any]:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".txt":
        return parse_txt(path)
    elif ext == ".pdf":
        return parse_pdf(path)
    elif ext == ".docx":
        return parse_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
```

- [ ] **Step 5: Uruchom testy — oczekiwany PASS**

```bash
cd backend
pytest tests/test_document_parser.py -v
```

Oczekiwany wynik: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/services/ backend/tests/
git commit -m "feat: document parser — txt/pdf/docx with tests"
```

---

### Task 5: API dokumentów + in-memory storage

**Files:**
- Create: `backend/api/__init__.py`
- Create: `backend/api/documents.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Utwórz `backend/api/__init__.py`** (pusty)

- [ ] **Step 2: Utwórz `backend/api/documents.py`**

```python
import os
import uuid
import tempfile
from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, UploadFile, File, HTTPException
from models.document import DocumentMeta, DocumentDetail
from services.document_parser import parse_document

router = APIRouter(prefix="/api/documents", tags=["documents"])

# In-memory store: id -> {meta: DocumentMeta, text: str}
_documents: Dict[str, Dict] = {}


@router.post("/upload", response_model=DocumentMeta)
async def upload_document(file: UploadFile = File(...)):
    allowed = {".pdf", ".docx", ".txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(allowed)}")

    contents = await file.read()
    size_bytes = len(contents)

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        parsed = parse_document(tmp_path, file.filename)
    finally:
        os.unlink(tmp_path)

    doc_id = str(uuid.uuid4())
    meta = DocumentMeta(
        id=doc_id,
        name=file.filename,
        size_bytes=size_bytes,
        page_count=parsed.get("page_count"),
        upload_date=datetime.utcnow().isoformat(),
        char_count=parsed["char_count"],
    )
    _documents[doc_id] = {"meta": meta, "text": parsed["text"]}
    return meta


@router.get("/", response_model=List[DocumentMeta])
def list_documents():
    return [v["meta"] for v in _documents.values()]


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: str):
    if doc_id not in _documents:
        raise HTTPException(404, "Document not found")
    entry = _documents[doc_id]
    return DocumentDetail(**entry["meta"].model_dump(), raw_text=entry["text"])


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    if doc_id not in _documents:
        raise HTTPException(404, "Document not found")
    del _documents[doc_id]
    return {"deleted": doc_id}


def get_document_text(doc_id: str) -> str:
    """Helper for other services."""
    if doc_id not in _documents:
        raise HTTPException(404, "Document not found")
    return _documents[doc_id]["text"]
```

- [ ] **Step 3: Zaktualizuj `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.documents import router as documents_router

load_dotenv()

app = FastAPI(title="RAG Learning Lab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Sprawdź ręcznie**

```bash
uvicorn main:app --reload --port 8000
# W przeglądarce: http://localhost:8000/docs
# Wgraj testowy plik .txt przez /api/documents/upload
```

- [ ] **Step 5: Commit**

```bash
git add backend/api/ backend/main.py
git commit -m "feat: documents API — upload, list, get, delete"
```

---

## Faza 3: Backend — Chunking

### Task 6: Fixed-size i recursive chunker + testy

**Files:**
- Create: `backend/services/chunkers/__init__.py`
- Create: `backend/services/chunkers/fixed_size.py`
- Create: `backend/services/chunkers/recursive.py`
- Create: `backend/tests/test_chunkers.py`

- [ ] **Step 1: Napisz testy**

Utwórz `backend/tests/test_chunkers.py`:

```python
from services.chunkers.fixed_size import chunk_fixed_size
from services.chunkers.recursive import chunk_recursive


def test_fixed_size_basic():
    text = "A" * 100
    chunks = chunk_fixed_size(text, chunk_size=30, overlap=10)
    assert len(chunks) > 1
    for c in chunks:
        assert c["content"]
        assert c["start_char"] >= 0
        assert c["end_char"] <= len(text)


def test_fixed_size_no_overlap():
    text = "Hello World " * 20
    chunks = chunk_fixed_size(text, chunk_size=50, overlap=0)
    total_chars = sum(len(c["content"]) for c in chunks)
    assert total_chars >= len(text) - 10  # allow minor trim


def test_fixed_size_overlap_boundaries():
    text = "X" * 200
    chunks = chunk_fixed_size(text, chunk_size=50, overlap=20)
    # Second chunk should start before end of first
    assert chunks[1]["start_char"] < chunks[0]["end_char"]


def test_recursive_basic():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_recursive(text, separators=["\n\n", "\n", " "], chunk_size=30)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c["content"]) <= 60  # allow some flex


def test_recursive_single_chunk():
    text = "Short text."
    chunks = chunk_recursive(text, separators=["\n\n"], chunk_size=500)
    assert len(chunks) == 1
    assert chunks[0]["content"] == "Short text."
```

- [ ] **Step 2: Uruchom — oczekiwany FAIL**

```bash
pytest tests/test_chunkers.py -v
```

- [ ] **Step 3: Utwórz `backend/services/chunkers/__init__.py`** (pusty)

- [ ] **Step 4: Utwórz `backend/services/chunkers/fixed_size.py`**

```python
from typing import List, Dict, Any


def chunk_fixed_size(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Dict[str, Any]]:
    """Split text into fixed-size chunks with optional overlap."""
    if not text:
        return []

    chunks = []
    step = max(1, chunk_size - overlap)
    index = 0
    pos = 0

    while pos < len(text):
        end = min(pos + chunk_size, len(text))
        content = text[pos:end]
        chunks.append({
            "content": content,
            "index": index,
            "start_char": pos,
            "end_char": end,
        })
        if end == len(text):
            break
        pos += step
        index += 1

    return chunks
```

- [ ] **Step 5: Utwórz `backend/services/chunkers/recursive.py`**

```python
from typing import List, Dict, Any, Optional


def chunk_recursive(
    text: str,
    separators: Optional[List[str]] = None,
    chunk_size: int = 500,
) -> List[Dict[str, Any]]:
    """Recursively split text using a list of separators (priority order)."""
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]

    if not text:
        return []

    if len(text) <= chunk_size:
        return [{"content": text, "index": 0, "start_char": 0, "end_char": len(text)}]

    # Find the first separator that produces splits
    separator = ""
    for sep in separators:
        if sep and sep in text:
            separator = sep
            break

    if separator:
        parts = text.split(separator)
    else:
        parts = list(text)  # character split

    chunks = []
    current = ""
    current_start = 0
    global_offset = 0

    for i, part in enumerate(parts):
        piece = part + (separator if i < len(parts) - 1 else "")
        if len(current) + len(piece) <= chunk_size:
            current += piece
        else:
            if current:
                chunks.append({
                    "content": current,
                    "index": len(chunks),
                    "start_char": current_start,
                    "end_char": current_start + len(current),
                })
                global_offset = current_start + len(current)
                current_start = global_offset
            current = piece

        if not current_start and not current:
            current_start = global_offset

    if current:
        chunks.append({
            "content": current,
            "index": len(chunks),
            "start_char": current_start,
            "end_char": current_start + len(current),
        })

    return chunks
```

- [ ] **Step 6: Uruchom testy — oczekiwany PASS**

```bash
pytest tests/test_chunkers.py -v
```

Oczekiwany wynik: `5 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/services/chunkers/ backend/tests/test_chunkers.py
git commit -m "feat: fixed-size and recursive chunkers with tests"
```

---

### Task 7: Semantic chunker

**Files:**
- Create: `backend/services/chunkers/semantic.py`

- [ ] **Step 1: Dodaj test do `backend/tests/test_chunkers.py`**

```python
from services.chunkers.semantic import chunk_semantic


def test_semantic_basic():
    text = "This is sentence one. This is sentence two. And sentence three! What about four?"
    chunks = chunk_semantic(text)
    assert len(chunks) >= 1
    for c in chunks:
        assert c["content"].strip()
        assert c["start_char"] >= 0


def test_semantic_empty():
    chunks = chunk_semantic("")
    assert chunks == []
```

- [ ] **Step 2: Utwórz `backend/services/chunkers/semantic.py`**

```python
import re
from typing import List, Dict, Any


def _split_sentences(text: str) -> List[str]:
    """Split text into sentences on . ! ? boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]


def chunk_semantic(text: str, max_sentences: int = 5) -> List[Dict[str, Any]]:
    """Group sentences into chunks, respecting sentence boundaries."""
    if not text:
        return []

    sentences = _split_sentences(text)
    chunks = []
    current_sentences: List[str] = []
    current_start = 0
    pos = 0

    for sentence in sentences:
        sent_start = text.find(sentence, pos)
        if sent_start == -1:
            sent_start = pos

        if len(current_sentences) >= max_sentences:
            content = " ".join(current_sentences)
            chunks.append({
                "content": content,
                "index": len(chunks),
                "start_char": current_start,
                "end_char": current_start + len(content),
            })
            current_sentences = []
            current_start = sent_start

        current_sentences.append(sentence)
        pos = sent_start + len(sentence)

    if current_sentences:
        content = " ".join(current_sentences)
        chunks.append({
            "content": content,
            "index": len(chunks),
            "start_char": current_start,
            "end_char": current_start + len(content),
        })

    return chunks
```

- [ ] **Step 3: Uruchom testy**

```bash
pytest tests/test_chunkers.py -v
```

Oczekiwany wynik: `7 passed`

- [ ] **Step 4: Commit**

```bash
git add backend/services/chunkers/semantic.py backend/tests/test_chunkers.py
git commit -m "feat: semantic chunker (sentence-boundary)"
```

---

### Task 8: Token counter + API chunkingu

**Files:**
- Create: `backend/services/token_counter.py`
- Create: `backend/api/chunks.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Napisz test token countera**

Dodaj do `backend/tests/test_token_counter.py`:

```python
from services.token_counter import count_tokens


def test_count_tokens_basic():
    n = count_tokens("Hello world")
    assert isinstance(n, int)
    assert n > 0


def test_count_tokens_empty():
    assert count_tokens("") == 0
```

- [ ] **Step 2: Utwórz `backend/services/token_counter.py`**

```python
import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_enc.encode(text))
```

- [ ] **Step 3: Uruchom test**

```bash
pytest tests/test_token_counter.py -v
```

Oczekiwany wynik: `2 passed`

- [ ] **Step 4: Utwórz `backend/api/chunks.py`**

```python
from fastapi import APIRouter, HTTPException
from typing import List, Dict
from models.chunk import Chunk, ChunkRequest, ChunkResponse, ChunkStats
from services.chunkers.fixed_size import chunk_fixed_size
from services.chunkers.recursive import chunk_recursive
from services.chunkers.semantic import chunk_semantic
from services.token_counter import count_tokens
from api.documents import get_document_text
import uuid

router = APIRouter(prefix="/api/chunks", tags=["chunks"])

# In-memory: document_id -> ChunkResponse
_chunks_store: Dict[str, ChunkResponse] = {}


def _build_chunk_response(raw_chunks: List[dict], doc_id: str, overlap: int = 0) -> ChunkResponse:
    chunks = []
    for raw in raw_chunks:
        chunks.append(Chunk(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            content=raw["content"],
            index=raw["index"],
            char_count=len(raw["content"]),
            token_count=count_tokens(raw["content"]),
            start_char=raw["start_char"],
            end_char=raw["end_char"],
        ))

    lengths = [c.char_count for c in chunks]
    stats = ChunkStats(
        count=len(chunks),
        avg_length=sum(lengths) / len(lengths) if lengths else 0.0,
        min_length=min(lengths) if lengths else 0,
        max_length=max(lengths) if lengths else 0,
        overlap_pct=overlap,
    )
    return ChunkResponse(chunks=chunks, stats=stats)


@router.post("/generate", response_model=ChunkResponse)
def generate_chunks(req: ChunkRequest):
    text = get_document_text(req.document_id)

    if req.strategy == "fixed":
        raw = chunk_fixed_size(text, chunk_size=req.chunk_size, overlap=req.overlap)
    elif req.strategy == "recursive":
        seps = req.separators or ["\n\n", "\n", ". ", " "]
        raw = chunk_recursive(text, separators=seps, chunk_size=req.chunk_size)
    elif req.strategy == "semantic":
        raw = chunk_semantic(text)
    else:
        raise HTTPException(400, f"Unknown strategy: {req.strategy}")

    response = _build_chunk_response(raw, req.document_id, overlap=req.overlap)
    _chunks_store[req.document_id] = response
    return response


@router.get("/{document_id}", response_model=ChunkResponse)
def get_chunks(document_id: str):
    if document_id not in _chunks_store:
        raise HTTPException(404, "No chunks generated for this document yet")
    return _chunks_store[document_id]


def get_chunks_for_document(document_id: str) -> List[Chunk]:
    if document_id not in _chunks_store:
        return []
    return _chunks_store[document_id].chunks
```

- [ ] **Step 5: Zaktualizuj `backend/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.documents import router as documents_router
from api.chunks import router as chunks_router

load_dotenv()

app = FastAPI(title="RAG Learning Lab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(chunks_router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Commit**

```bash
git add backend/services/token_counter.py backend/api/chunks.py backend/main.py backend/tests/
git commit -m "feat: chunking API with token counting"
```

---

## Faza 4: Backend — Embeddingi i Vector Store

### Task 9: ChromaDB vector store + embeddingi

**Files:**
- Create: `backend/services/vector_store.py`
- Create: `backend/services/embeddings_service.py`
- Create: `backend/api/embeddings.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Utwórz `backend/services/vector_store.py`**

```python
import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional

_client: Optional[chromadb.ClientAPI] = None
_collection = None
COLLECTION_NAME = "rag_chunks"


def _get_collection():
    global _client, _collection
    if _collection is None:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        _client = chromadb.PersistentClient(path=persist_dir)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks(
    chunk_ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: List[Dict[str, Any]],
) -> None:
    col = _get_collection()
    col.upsert(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def query_chunks(
    query_embedding: List[float],
    n_results: int = 5,
    where: Optional[Dict] = None,
) -> Dict[str, Any]:
    col = _get_collection()
    params = {
        "query_embeddings": [query_embedding],
        "n_results": min(n_results, col.count() or 1),
        "include": ["documents", "metadatas", "distances", "embeddings"],
    }
    if where:
        params["where"] = where
    return col.query(**params)


def delete_by_document(document_id: str) -> None:
    col = _get_collection()
    results = col.get(where={"document_id": document_id})
    if results["ids"]:
        col.delete(ids=results["ids"])


def get_all_embeddings() -> Dict[str, Any]:
    col = _get_collection()
    return col.get(include=["embeddings", "metadatas", "documents"])


def reset_collection() -> None:
    global _collection
    if _client is not None:
        _client.delete_collection(COLLECTION_NAME)
        _collection = None
    _get_collection()
```

- [ ] **Step 2: Utwórz `backend/services/embeddings_service.py`**

```python
import os
import time
from typing import List, Tuple
from openai import OpenAI

_client: OpenAI = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def embed_texts(texts: List[str]) -> Tuple[List[List[float]], float]:
    """Returns (embeddings, elapsed_ms)."""
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    start = time.time()
    client = _get_client()
    response = client.embeddings.create(model=model, input=texts)
    elapsed_ms = (time.time() - start) * 1000
    embeddings = [item.embedding for item in response.data]
    return embeddings, elapsed_ms


def embed_query(query: str) -> Tuple[List[float], float]:
    embeddings, ms = embed_texts([query])
    return embeddings[0], ms
```

- [ ] **Step 3: Utwórz `backend/api/embeddings.py`**

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import numpy as np
from sklearn.decomposition import PCA
from models.chunk import Chunk
from services.embeddings_service import embed_texts, embed_query
from services.vector_store import add_chunks, get_all_embeddings, query_chunks
from api.chunks import get_chunks_for_document

router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])


class EmbedRequest(BaseModel):
    document_id: str


class EmbeddingPoint(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    x: float
    y: float
    content_preview: str


class SimilarityRequest(BaseModel):
    chunk_id_a: str
    chunk_id_b: str


@router.post("/generate")
def generate_embeddings(req: EmbedRequest):
    chunks: List[Chunk] = get_chunks_for_document(req.document_id)
    if not chunks:
        raise HTTPException(404, "No chunks found for this document. Generate chunks first.")

    texts = [c.content for c in chunks]
    embeddings, elapsed_ms = embed_texts(texts)

    chunk_ids = [c.id for c in chunks]
    metadatas = [
        {"document_id": c.document_id, "index": c.index, "char_count": c.char_count}
        for c in chunks
    ]

    add_chunks(
        chunk_ids=chunk_ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    return {
        "embedded_count": len(chunks),
        "elapsed_ms": elapsed_ms,
        "model": "text-embedding-3-small",
    }


@router.get("/visualize", response_model=List[EmbeddingPoint])
def visualize_embeddings():
    data = get_all_embeddings()
    if not data["ids"]:
        return []

    embeddings = np.array(data["embeddings"])
    if embeddings.shape[0] < 2:
        coords = np.zeros((embeddings.shape[0], 2))
    else:
        n_components = min(2, embeddings.shape[0])
        pca = PCA(n_components=n_components)
        coords = pca.fit_transform(embeddings)
        if coords.shape[1] == 1:
            coords = np.column_stack([coords, np.zeros(len(coords))])

    points = []
    for i, chunk_id in enumerate(data["ids"]):
        meta = data["metadatas"][i]
        points.append(EmbeddingPoint(
            chunk_id=chunk_id,
            document_id=meta.get("document_id", ""),
            document_name=meta.get("document_id", "")[:8],
            x=float(coords[i, 0]),
            y=float(coords[i, 1]),
            content_preview=data["documents"][i][:100],
        ))
    return points


@router.get("/similarity")
def get_similarity(chunk_id_a: str, chunk_id_b: str):
    from chromadb import errors
    data = get_all_embeddings()

    def find_embedding(cid: str):
        for i, c in enumerate(data["ids"]):
            if c == cid:
                return np.array(data["embeddings"][i])
        return None

    emb_a = find_embedding(chunk_id_a)
    emb_b = find_embedding(chunk_id_b)

    if emb_a is None or emb_b is None:
        raise HTTPException(404, "One or both chunk IDs not found in vector store")

    cosine = float(np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b)))
    return {"chunk_id_a": chunk_id_a, "chunk_id_b": chunk_id_b, "cosine_similarity": cosine}
```

- [ ] **Step 4: Zaktualizuj `backend/main.py`** — dodaj router:

```python
from api.embeddings import router as embeddings_router
# ...
app.include_router(embeddings_router)
```

- [ ] **Step 5: Commit**

```bash
git add backend/services/vector_store.py backend/services/embeddings_service.py backend/api/embeddings.py backend/main.py
git commit -m "feat: embeddings — OpenAI embed, ChromaDB store, PCA visualization"
```

---

## Faza 5: Backend — Chat, Retrieval i Prompt Builder

### Task 10: Prompt builder + testy

**Files:**
- Create: `backend/services/prompt_builder.py`
- Create: `backend/tests/test_prompt_builder.py`

- [ ] **Step 1: Napisz testy**

`backend/tests/test_prompt_builder.py`:

```python
from services.prompt_builder import build_prompt, DEFAULT_SYSTEM_PROMPT
from models.chunk import Chunk


def _make_chunk(content: str, idx: int = 0) -> Chunk:
    return Chunk(
        id=f"c{idx}", document_id="doc1", content=content,
        index=idx, char_count=len(content), token_count=10,
        start_char=0, end_char=len(content),
    )


def test_build_prompt_contains_query():
    chunks = [_make_chunk("Some context text.")]
    result = build_prompt("What is X?", chunks, DEFAULT_SYSTEM_PROMPT)
    assert "What is X?" in result["full_prompt"]
    assert "What is X?" in result["user_query"]


def test_build_prompt_contains_chunks():
    chunks = [_make_chunk("Relevant fact about Y.")]
    result = build_prompt("Tell me about Y", chunks, DEFAULT_SYSTEM_PROMPT)
    assert "Relevant fact about Y." in result["context_block"]


def test_build_prompt_token_counts_positive():
    chunks = [_make_chunk("Some context.")]
    result = build_prompt("Query", chunks, DEFAULT_SYSTEM_PROMPT)
    assert result["token_counts"]["system"] > 0
    assert result["token_counts"]["context"] > 0
    assert result["token_counts"]["query"] > 0
    assert result["token_counts"]["total"] > 0


def test_build_prompt_empty_chunks():
    result = build_prompt("Question?", [], DEFAULT_SYSTEM_PROMPT)
    assert "Question?" in result["full_prompt"]
    assert result["token_counts"]["context"] == 0
```

- [ ] **Step 2: Uruchom — oczekiwany FAIL**

```bash
pytest tests/test_prompt_builder.py -v
```

- [ ] **Step 3: Utwórz `backend/services/prompt_builder.py`**

```python
from typing import List, Dict, Any
from models.chunk import Chunk
from services.token_counter import count_tokens

DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided context documents.
Always base your answer on the context provided. If the context doesn't contain the answer, say so clearly.
Be concise and accurate."""


def build_prompt(
    query: str,
    chunks: List[Chunk],
    system_message: str = DEFAULT_SYSTEM_PROMPT,
) -> Dict[str, Any]:
    if chunks:
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[{i}] {chunk.content}")
        context_block = "\n\n".join(context_parts)
    else:
        context_block = ""

    if context_block:
        full_prompt = f"{system_message}\n\nContext:\n{context_block}\n\nQuestion: {query}"
    else:
        full_prompt = f"{system_message}\n\nQuestion: {query}"

    token_counts = {
        "system": count_tokens(system_message),
        "context": count_tokens(context_block),
        "query": count_tokens(query),
        "total": count_tokens(full_prompt),
    }

    return {
        "system_message": system_message,
        "context_block": context_block,
        "user_query": query,
        "full_prompt": full_prompt,
        "token_counts": token_counts,
    }
```

- [ ] **Step 4: Uruchom testy — oczekiwany PASS**

```bash
pytest tests/test_prompt_builder.py -v
```

Oczekiwany wynik: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/services/prompt_builder.py backend/tests/test_prompt_builder.py
git commit -m "feat: prompt builder with token counting — tested"
```

---

### Task 11: Chat API ze streamingiem SSE

**Files:**
- Create: `backend/services/llm_service.py`
- Create: `backend/api/chat.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Utwórz `backend/services/llm_service.py`**

```python
import os
import time
import uuid
from datetime import datetime
from typing import List, Generator, Dict, Any
from openai import OpenAI
from models.metrics import QueryMetrics, SessionMetrics

_client: OpenAI = None

# GPT-4o-mini pricing (per 1M tokens, as of 2024)
_PRICING = {
    "gpt-4o-mini": {"prompt": 0.150, "completion": 0.600},
    "gpt-4o": {"prompt": 5.0, "completion": 15.0},
}

_session_metrics: SessionMetrics = SessionMetrics(
    total_queries=0, total_tokens=0, total_cost_usd=0.0, queries=[]
)

_last_query_metrics: Dict[str, Any] = {}


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def stream_chat(
    full_prompt: str,
    query: str,
    embedding_ms: float = 0.0,
    retrieval_ms: float = 0.0,
) -> Generator[str, None, None]:
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    client = _get_client()
    start = time.time()

    prompt_tokens = 0
    completion_tokens = 0
    full_response = ""

    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": full_prompt}],
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            full_response += delta.content
            yield delta.content

        if chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens
            completion_tokens = chunk.usage.completion_tokens

    llm_ms = (time.time() - start) * 1000

    # Fallback token count if usage not in stream
    if prompt_tokens == 0:
        from services.token_counter import count_tokens
        prompt_tokens = count_tokens(full_prompt)
        completion_tokens = count_tokens(full_response)

    pricing = _PRICING.get(model, {"prompt": 0.150, "completion": 0.600})
    cost = (prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]) / 1_000_000

    qm = QueryMetrics(
        query_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        query=query,
        embedding_ms=embedding_ms,
        retrieval_ms=retrieval_ms,
        llm_ms=llm_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        estimated_cost_usd=cost,
    )

    global _session_metrics, _last_query_metrics
    _session_metrics.total_queries += 1
    _session_metrics.total_tokens += qm.total_tokens
    _session_metrics.total_cost_usd += cost
    _session_metrics.queries.append(qm)
    _last_query_metrics = qm.model_dump()


def get_session_metrics() -> SessionMetrics:
    return _session_metrics


def reset_session_metrics() -> None:
    global _session_metrics, _last_query_metrics
    _session_metrics = SessionMetrics(
        total_queries=0, total_tokens=0, total_cost_usd=0.0, queries=[]
    )
    _last_query_metrics = {}
```

- [ ] **Step 2: Utwórz `backend/api/chat.py`**

```python
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from models.chunk import Chunk
from services.embeddings_service import embed_query
from services.vector_store import query_chunks
from services.prompt_builder import build_prompt, DEFAULT_SYSTEM_PROMPT
from services.llm_service import stream_chat

router = APIRouter(prefix="/api/chat", tags=["chat"])

_last_retrieval: List[Dict[str, Any]] = []
_last_prompt_data: Dict[str, Any] = {}
_current_system_prompt: str = DEFAULT_SYSTEM_PROMPT


class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    system_prompt: Optional[str] = None


class SystemPromptRequest(BaseModel):
    system_prompt: str


@router.post("")
async def chat(req: ChatRequest):
    global _last_retrieval, _last_prompt_data, _current_system_prompt

    system_prompt = req.system_prompt or _current_system_prompt

    # 1. Embed query
    t_emb_start = time.time()
    query_embedding, _ = embed_query(req.query)
    embedding_ms = (time.time() - t_emb_start) * 1000

    # 2. Retrieve chunks
    t_ret_start = time.time()
    results = query_chunks(query_embedding, n_results=req.top_k)
    retrieval_ms = (time.time() - t_ret_start) * 1000

    retrieved = []
    if results["ids"] and results["ids"][0]:
        for i, chunk_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            retrieved.append({
                "chunk_id": chunk_id,
                "document_id": meta.get("document_id", ""),
                "document_name": meta.get("document_id", "")[:12],
                "content": results["documents"][0][i] if results["documents"] else "",
                "score": 1.0 - float(results["distances"][0][i]),
                "rank": i + 1,
            })

    _last_retrieval = retrieved

    # 3. Build mock chunks for prompt builder
    chunks_for_prompt = [
        Chunk(
            id=r["chunk_id"], document_id=r["document_id"], content=r["content"],
            index=r["rank"] - 1, char_count=len(r["content"]),
            token_count=0, start_char=0, end_char=len(r["content"]),
        )
        for r in retrieved
    ]

    prompt_data = build_prompt(req.query, chunks_for_prompt, system_prompt)
    _last_prompt_data = prompt_data

    # 4. Stream response
    def event_stream():
        for token in stream_chat(
            prompt_data["full_prompt"],
            req.query,
            embedding_ms=embedding_ms,
            retrieval_ms=retrieval_ms,
        ):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/retrieval")
def get_retrieval():
    return _last_retrieval


@router.get("/prompt")
def get_prompt():
    return _last_prompt_data


@router.post("/system-prompt")
def update_system_prompt(req: SystemPromptRequest):
    global _current_system_prompt
    _current_system_prompt = req.system_prompt
    return {"updated": True}
```

- [ ] **Step 3: Utwórz `backend/api/metrics.py`**

```python
from fastapi import APIRouter
from services.llm_service import get_session_metrics, reset_session_metrics
from services.vector_store import reset_collection

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics/session")
def session_metrics():
    return get_session_metrics()


@router.delete("/data/reset")
def reset_all():
    reset_collection()
    reset_session_metrics()
    # Clear in-memory document and chunk stores
    from api.documents import _documents
    from api.chunks import _chunks_store
    _documents.clear()
    _chunks_store.clear()
    return {"reset": True}
```

- [ ] **Step 4: Zaktualizuj `backend/main.py`** (finalna wersja)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from api.documents import router as documents_router
from api.chunks import router as chunks_router
from api.embeddings import router as embeddings_router
from api.chat import router as chat_router
from api.metrics import router as metrics_router

load_dotenv()

app = FastAPI(title="RAG Learning Lab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents_router)
app.include_router(chunks_router)
app.include_router(embeddings_router)
app.include_router(chat_router)
app.include_router(metrics_router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Uruchom i przetestuj w Swagger**

```bash
uvicorn main:app --reload --port 8000
# http://localhost:8000/docs
# Przetestuj cały pipeline: upload → chunks → embeddings → chat
```

- [ ] **Step 6: Uruchom wszystkie testy backendu**

```bash
pytest tests/ -v
```

Oczekiwany wynik: wszystkie testy pass.

- [ ] **Step 7: Commit**

```bash
git add backend/services/llm_service.py backend/api/chat.py backend/api/metrics.py backend/main.py
git commit -m "feat: chat SSE streaming, retrieval, prompt builder, metrics API"
```

---

## Faza 6: Frontend — Layout i API client

### Task 12: API client i layout aplikacji

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/components/layout/Header.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/layout/Footer.tsx`

- [ ] **Step 1: Utwórz `frontend/src/api/client.ts`**

```typescript
const BASE = "http://localhost:8000/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Documents
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<import("../types").DocumentMeta>("/documents/upload", {
      method: "POST",
      body: form,
    });
  },
  listDocuments: () => request<import("../types").DocumentMeta[]>("/documents/"),
  getDocument: (id: string) => request<import("../types").DocumentDetail>(`/documents/${id}`),
  deleteDocument: (id: string) => request<{ deleted: string }>(`/documents/${id}`, { method: "DELETE" }),

  // Chunks
  generateChunks: (body: import("../types").ChunkRequest) =>
    request<import("../types").ChunkResponse>("/chunks/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  getChunks: (documentId: string) =>
    request<import("../types").ChunkResponse>(`/chunks/${documentId}`),

  // Embeddings
  generateEmbeddings: (documentId: string) =>
    request<{ embedded_count: number; elapsed_ms: number }>("/embeddings/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: documentId }),
    }),
  getVisualization: () =>
    request<import("../types").EmbeddingPoint[]>("/embeddings/visualize"),
  getSimilarity: (a: string, b: string) =>
    request<{ cosine_similarity: number }>(`/embeddings/similarity?chunk_id_a=${a}&chunk_id_b=${b}`),

  // Chat
  getRetrieval: () => request<import("../types").RetrievedChunk[]>("/chat/retrieval"),
  getPrompt: () => request<import("../types").PromptData>("/chat/prompt"),
  updateSystemPrompt: (system_prompt: string) =>
    request<{ updated: boolean }>("/chat/system-prompt", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ system_prompt }),
    }),

  // Metrics
  getSessionMetrics: () => request<import("../types").SessionMetrics>("/metrics/session"),
  resetAll: () => request<{ reset: boolean }>("/data/reset", { method: "DELETE" }),
};

export function streamChat(
  query: string,
  topK: number,
  onToken: (token: string) => void,
  onDone: () => void,
  systemPrompt?: string,
) {
  const ctrl = new AbortController();
  fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK, system_prompt: systemPrompt }),
    signal: ctrl.signal,
  }).then(async (res) => {
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const lines = decoder.decode(value).split("\n");
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const token = line.slice(6);
          if (token === "[DONE]") {
            onDone();
            return;
          }
          onToken(token);
        }
      }
    }
    onDone();
  });
  return () => ctrl.abort();
}
```

- [ ] **Step 2: Utwórz `frontend/src/components/layout/Header.tsx`**

```tsx
import { Brain } from "lucide-react";
import { SessionMetrics } from "../../types";

interface HeaderProps {
  metrics: SessionMetrics | null;
}

export function Header({ metrics }: HeaderProps) {
  return (
    <header className="h-14 border-b border-border bg-white flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-2">
        <Brain className="w-5 h-5 text-primary" />
        <span className="font-semibold text-sm">RAG Learning Lab</span>
      </div>
      {metrics && (
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>Queries: <strong>{metrics.total_queries}</strong></span>
          <span>Tokens: <strong>{metrics.total_tokens.toLocaleString()}</strong></span>
          <span>Cost: <strong>${metrics.total_cost_usd.toFixed(4)}</strong></span>
        </div>
      )}
    </header>
  );
}
```

- [ ] **Step 3: Utwórz `frontend/src/components/layout/Sidebar.tsx`**

```tsx
import { FileText, Layers, Scatter3D, MessageSquare, BarChart2 } from "lucide-react";
import { Panel } from "../../types";

const NAV = [
  { id: "documents" as Panel, label: "Documents", icon: FileText },
  { id: "chunks" as Panel, label: "Chunking Lab", icon: Layers },
  { id: "embeddings" as Panel, label: "Embeddings", icon: Scatter3D },
  { id: "chat" as Panel, label: "Chat", icon: MessageSquare },
  { id: "metrics" as Panel, label: "Metrics", icon: BarChart2 },
];

interface SidebarProps {
  active: Panel;
  onChange: (panel: Panel) => void;
}

export function Sidebar({ active, onChange }: SidebarProps) {
  return (
    <nav className="w-48 border-r border-border bg-white flex flex-col pt-4 shrink-0">
      {NAV.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
            active === id
              ? "bg-primary/10 text-primary font-medium"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          }`}
        >
          <Icon className="w-4 h-4" />
          {label}
        </button>
      ))}
    </nav>
  );
}
```

- [ ] **Step 4: Utwórz `frontend/src/components/layout/Footer.tsx`**

```tsx
interface FooterProps {
  lastQueryMs?: number;
}

export function Footer({ lastQueryMs }: FooterProps) {
  return (
    <footer className="h-8 border-t border-border bg-white flex items-center px-6 shrink-0">
      <span className="text-xs text-muted-foreground">
        RAG Learning Lab — educational single-user app
        {lastQueryMs != null && ` · Last query: ${lastQueryMs.toFixed(0)}ms`}
      </span>
    </footer>
  );
}
```

- [ ] **Step 5: Utwórz `frontend/src/App.tsx`**

```tsx
import { useState, useEffect } from "react";
import { Header } from "./components/layout/Header";
import { Sidebar } from "./components/layout/Sidebar";
import { Footer } from "./components/layout/Footer";
import { Panel, SessionMetrics } from "./types";
import { api } from "./api/client";

// Lazy panel components (placeholders — implemented in next tasks)
function PanelContent({ panel }: { panel: Panel }) {
  return (
    <div className="flex-1 p-6 text-sm text-muted-foreground">
      Panel: <strong>{panel}</strong> — coming soon
    </div>
  );
}

export default function App() {
  const [activePanel, setActivePanel] = useState<Panel>("documents");
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);

  useEffect(() => {
    api.getSessionMetrics().then(setMetrics).catch(() => {});
    const interval = setInterval(() => {
      api.getSessionMetrics().then(setMetrics).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header metrics={metrics} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar active={activePanel} onChange={setActivePanel} />
        <main className="flex-1 overflow-auto bg-muted/30">
          <PanelContent panel={activePanel} />
        </main>
      </div>
      <Footer />
    </div>
  );
}
```

- [ ] **Step 6: Sprawdź w przeglądarce**

```bash
cd frontend && npm run dev
```

Oczekiwany wynik: Widoczny layout z headerem, sidebarem i stopką.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat: frontend layout — header, sidebar, footer, API client"
```

---

## Faza 7: Frontend — Panele UI

### Task 13: Panel Document Manager

**Files:**
- Create: `frontend/src/components/documents/DocumentManager.tsx`
- Create: `frontend/src/components/documents/UploadZone.tsx`
- Create: `frontend/src/components/documents/DocumentList.tsx`

- [ ] **Step 1: Utwórz `frontend/src/components/documents/UploadZone.tsx`**

```tsx
import { useState, useRef } from "react";
import { Upload } from "lucide-react";
import { api } from "../../api/client";
import { DocumentMeta } from "../../types";

interface UploadZoneProps {
  onUploaded: (doc: DocumentMeta) => void;
}

export function UploadZone({ onUploaded }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setLoading(true);
    setError(null);
    try {
      const doc = await api.uploadDocument(file);
      onUploaded(doc);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files[0];
        if (f) handleFile(f);
      }}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
      />
      <Upload className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
      {loading ? (
        <p className="text-sm text-muted-foreground">Uploading...</p>
      ) : (
        <>
          <p className="text-sm font-medium">Drop file here or click to upload</p>
          <p className="text-xs text-muted-foreground mt-1">PDF, DOCX, TXT</p>
        </>
      )}
      {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 2: Utwórz `frontend/src/components/documents/DocumentList.tsx`**

```tsx
import { Trash2, FileText, Eye } from "lucide-react";
import { DocumentMeta } from "../../types";

interface DocumentListProps {
  documents: DocumentMeta[];
  selectedId: string | null;
  onSelect: (doc: DocumentMeta) => void;
  onDelete: (id: string) => void;
}

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

export function DocumentList({ documents, selectedId, onSelect, onDelete }: DocumentListProps) {
  if (documents.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No documents uploaded yet.</p>;
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className={`border rounded-lg p-3 flex items-start gap-3 cursor-pointer transition-colors ${
            selectedId === doc.id ? "border-primary bg-primary/5" : "border-border hover:border-primary/30"
          }`}
          onClick={() => onSelect(doc)}
        >
          <FileText className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{doc.name}</p>
            <p className="text-xs text-muted-foreground">
              {formatBytes(doc.size_bytes)} · {doc.char_count.toLocaleString()} chars
              {doc.page_count != null && ` · ${doc.page_count} pages`}
            </p>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(doc.id); }}
            className="p-1 rounded hover:bg-red-50 hover:text-red-500 text-muted-foreground"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Utwórz `frontend/src/components/documents/DocumentManager.tsx`**

```tsx
import { useState, useEffect } from "react";
import { DocumentMeta, DocumentDetail } from "../../types";
import { api } from "../../api/client";
import { UploadZone } from "./UploadZone";
import { DocumentList } from "./DocumentList";

export function DocumentManager() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  useEffect(() => {
    api.listDocuments().then(setDocuments).catch(console.error);
  }, []);

  async function handleSelect(doc: DocumentMeta) {
    setLoadingPreview(true);
    try {
      const detail = await api.getDocument(doc.id);
      setSelected(detail);
    } finally {
      setLoadingPreview(false);
    }
  }

  async function handleDelete(id: string) {
    await api.deleteDocument(id);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    if (selected?.id === id) setSelected(null);
  }

  return (
    <div className="p-6 h-full flex gap-6">
      <div className="w-80 shrink-0 space-y-4">
        <h2 className="font-semibold text-sm">Upload Document</h2>
        <UploadZone onUploaded={(doc) => setDocuments((prev) => [doc, ...prev])} />
        <h2 className="font-semibold text-sm">Documents ({documents.length})</h2>
        <DocumentList
          documents={documents}
          selectedId={selected?.id ?? null}
          onSelect={handleSelect}
          onDelete={handleDelete}
        />
      </div>
      <div className="flex-1 border rounded-lg bg-white p-4 overflow-auto">
        {loadingPreview && <p className="text-sm text-muted-foreground">Loading...</p>}
        {!loadingPreview && selected && (
          <>
            <h3 className="font-semibold text-sm mb-3">{selected.name} — Raw Text</h3>
            <pre className="text-xs whitespace-pre-wrap font-mono text-muted-foreground leading-relaxed">
              {selected.raw_text}
            </pre>
          </>
        )}
        {!loadingPreview && !selected && (
          <p className="text-sm text-muted-foreground">Select a document to preview its extracted text.</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/documents/
git commit -m "feat: Document Manager panel — upload, list, preview, delete"
```

---

### Task 14: Panel Chunking Lab

**Files:**
- Create: `frontend/src/components/chunks/ChunkingLab.tsx`
- Create: `frontend/src/components/chunks/StrategySelector.tsx`
- Create: `frontend/src/components/chunks/ChunkViewer.tsx`

- [ ] **Step 1: Utwórz `frontend/src/components/chunks/StrategySelector.tsx`**

```tsx
import { ChunkRequest } from "../../types";

interface StrategySelectorProps {
  value: ChunkRequest;
  onChange: (v: ChunkRequest) => void;
  documentId: string;
}

export function StrategySelector({ value, onChange, documentId }: StrategySelectorProps) {
  const strategies = [
    { id: "fixed", label: "Fixed Size" },
    { id: "recursive", label: "Recursive" },
    { id: "semantic", label: "Semantic" },
  ] as const;

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Strategy</label>
        <div className="flex gap-2 mt-1.5">
          {strategies.map((s) => (
            <button
              key={s.id}
              onClick={() => onChange({ ...value, strategy: s.id, document_id: documentId })}
              className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                value.strategy === s.id
                  ? "border-primary bg-primary text-white"
                  : "border-border hover:border-primary/50"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {(value.strategy === "fixed" || value.strategy === "recursive") && (
        <>
          <div>
            <label className="text-xs font-medium text-muted-foreground">
              Chunk Size: <strong>{value.chunk_size}</strong> chars
            </label>
            <input
              type="range" min={100} max={2000} step={50}
              value={value.chunk_size}
              onChange={(e) => onChange({ ...value, chunk_size: Number(e.target.value) })}
              className="w-full mt-1"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">
              Overlap: <strong>{value.overlap}</strong> chars
            </label>
            <input
              type="range" min={0} max={200} step={10}
              value={value.overlap}
              onChange={(e) => onChange({ ...value, overlap: Number(e.target.value) })}
              className="w-full mt-1"
            />
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Utwórz `frontend/src/components/chunks/ChunkViewer.tsx`**

```tsx
import { Chunk, ChunkStats } from "../../types";

interface ChunkViewerProps {
  chunks: Chunk[];
  stats: ChunkStats | null;
}

export function ChunkViewer({ chunks, stats }: ChunkViewerProps) {
  if (chunks.length === 0) {
    return <p className="text-sm text-muted-foreground">No chunks generated yet.</p>;
  }

  const COLORS = ["bg-blue-100", "bg-green-100", "bg-yellow-100", "bg-purple-100", "bg-pink-100"];

  return (
    <div className="space-y-4">
      {stats && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Count", value: stats.count },
            { label: "Avg length", value: `${stats.avg_length.toFixed(0)} chars` },
            { label: "Min/Max", value: `${stats.min_length}/${stats.max_length}` },
            { label: "Overlap", value: `${stats.overlap_pct} chars` },
          ].map(({ label, value }) => (
            <div key={label} className="border rounded-lg p-3 bg-white text-center">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-sm font-semibold mt-0.5">{value}</p>
            </div>
          ))}
        </div>
      )}
      <div className="space-y-2 max-h-[500px] overflow-auto">
        {chunks.map((chunk, i) => (
          <div
            key={chunk.id}
            className={`rounded-lg p-3 ${COLORS[i % COLORS.length]}`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground">
                Chunk {chunk.index + 1}
              </span>
              <span className="text-xs text-muted-foreground">
                {chunk.char_count} chars · {chunk.token_count} tokens
              </span>
            </div>
            <p className="text-xs leading-relaxed">{chunk.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Utwórz `frontend/src/components/chunks/ChunkingLab.tsx`**

```tsx
import { useState, useEffect } from "react";
import { DocumentMeta, ChunkRequest, ChunkResponse } from "../../types";
import { api } from "../../api/client";
import { StrategySelector } from "./StrategySelector";
import { ChunkViewer } from "./ChunkViewer";

export function ChunkingLab() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [chunkReq, setChunkReq] = useState<ChunkRequest>({
    document_id: "",
    strategy: "fixed",
    chunk_size: 500,
    overlap: 50,
  });
  const [response, setResponse] = useState<ChunkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDocuments().then((docs) => {
      setDocuments(docs);
      if (docs.length > 0) {
        setSelectedDocId(docs[0].id);
        setChunkReq((prev) => ({ ...prev, document_id: docs[0].id }));
      }
    });
  }, []);

  async function generate() {
    if (!selectedDocId) return;
    setLoading(true);
    setError(null);
    try {
      const req = { ...chunkReq, document_id: selectedDocId };
      const res = await api.generateChunks(req);
      setResponse(res);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 h-full flex gap-6">
      <div className="w-72 shrink-0 space-y-4">
        <h2 className="font-semibold text-sm">Chunking Lab</h2>
        <div>
          <label className="text-xs font-medium text-muted-foreground">Document</label>
          <select
            className="w-full mt-1 text-sm border border-border rounded-md px-2 py-1.5"
            value={selectedDocId}
            onChange={(e) => {
              setSelectedDocId(e.target.value);
              setChunkReq((prev) => ({ ...prev, document_id: e.target.value }));
            }}
          >
            {documents.map((d) => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
        <StrategySelector
          value={chunkReq}
          onChange={setChunkReq}
          documentId={selectedDocId}
        />
        <button
          onClick={generate}
          disabled={loading || !selectedDocId}
          className="w-full py-2 bg-primary text-white text-sm rounded-md hover:bg-primary/90 disabled:opacity-50"
        >
          {loading ? "Generating..." : "Generate Chunks"}
        </button>
        {error && <p className="text-xs text-red-500">{error}</p>}
      </div>
      <div className="flex-1 overflow-auto">
        <ChunkViewer
          chunks={response?.chunks ?? []}
          stats={response?.stats ?? null}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chunks/
git commit -m "feat: Chunking Lab panel — strategy selector, params, chunk viewer"
```

---

### Task 15: Panel Embedding Explorer

**Files:**
- Create: `frontend/src/components/embeddings/EmbeddingExplorer.tsx`
- Create: `frontend/src/components/embeddings/ScatterPlot.tsx`

- [ ] **Step 1: Utwórz `frontend/src/components/embeddings/ScatterPlot.tsx`**

```tsx
import { ScatterChart, Scatter, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { EmbeddingPoint } from "../../types";

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"];

interface ScatterPlotProps {
  points: EmbeddingPoint[];
  selectedA: string | null;
  selectedB: string | null;
  onSelect: (id: string) => void;
}

function getDocColor(docId: string, allDocIds: string[]): string {
  const idx = allDocIds.indexOf(docId);
  return COLORS[idx % COLORS.length];
}

export function ScatterPlot({ points, selectedA, selectedB, onSelect }: ScatterPlotProps) {
  const docIds = [...new Set(points.map((p) => p.document_id))];

  if (points.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 border rounded-lg bg-white">
        <p className="text-sm text-muted-foreground">Generate embeddings to see the visualization.</p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg bg-white p-4">
      <ResponsiveContainer width="100%" height={350}>
        <ScatterChart>
          <XAxis dataKey="x" type="number" domain={["auto", "auto"]} tick={{ fontSize: 10 }} />
          <YAxis dataKey="y" type="number" domain={["auto", "auto"]} tick={{ fontSize: 10 }} />
          <Tooltip
            content={({ payload }) => {
              if (!payload?.[0]) return null;
              const p = payload[0].payload as EmbeddingPoint;
              return (
                <div className="bg-white border rounded shadow-sm p-2 max-w-xs">
                  <p className="text-xs font-medium truncate">{p.content_preview}</p>
                  <p className="text-xs text-muted-foreground">Doc: {p.document_name}</p>
                </div>
              );
            }}
          />
          <Scatter
            data={points}
            onClick={(d) => onSelect(d.chunk_id)}
          >
            {points.map((p) => (
              <Cell
                key={p.chunk_id}
                fill={getDocColor(p.document_id, docIds)}
                opacity={selectedA === p.chunk_id || selectedB === p.chunk_id ? 1 : 0.7}
                stroke={selectedA === p.chunk_id || selectedB === p.chunk_id ? "#1e40af" : "none"}
                strokeWidth={2}
                r={selectedA === p.chunk_id || selectedB === p.chunk_id ? 7 : 5}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-2 flex-wrap">
        {docIds.map((id, i) => (
          <div key={id} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
            <span className="text-xs text-muted-foreground">{id.slice(0, 8)}...</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Utwórz `frontend/src/components/embeddings/EmbeddingExplorer.tsx`**

```tsx
import { useState, useEffect } from "react";
import { DocumentMeta, EmbeddingPoint } from "../../types";
import { api } from "../../api/client";
import { ScatterPlot } from "./ScatterPlot";

export function EmbeddingExplorer() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string>("");
  const [points, setPoints] = useState<EmbeddingPoint[]>([]);
  const [selectedA, setSelectedA] = useState<string | null>(null);
  const [selectedB, setSelectedB] = useState<string | null>(null);
  const [similarity, setSimilarity] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDocuments().then((docs) => {
      setDocuments(docs);
      if (docs.length) setSelectedDoc(docs[0].id);
    });
    api.getVisualization().then(setPoints).catch(() => {});
  }, []);

  async function handleEmbed() {
    if (!selectedDoc) return;
    setLoading(true);
    setError(null);
    try {
      await api.generateEmbeddings(selectedDoc);
      const viz = await api.getVisualization();
      setPoints(viz);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelect(chunkId: string) {
    if (!selectedA) {
      setSelectedA(chunkId);
      setSimilarity(null);
    } else if (!selectedB && chunkId !== selectedA) {
      setSelectedB(chunkId);
      try {
        const result = await api.getSimilarity(selectedA, chunkId);
        setSimilarity(result.cosine_similarity);
      } catch (e) {
        setSimilarity(null);
      }
    } else {
      setSelectedA(chunkId);
      setSelectedB(null);
      setSimilarity(null);
    }
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="font-semibold text-sm">Embedding Explorer</h2>
        <select
          className="text-sm border border-border rounded-md px-2 py-1.5"
          value={selectedDoc}
          onChange={(e) => setSelectedDoc(e.target.value)}
        >
          {documents.map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
        <button
          onClick={handleEmbed}
          disabled={loading || !selectedDoc}
          className="px-3 py-1.5 bg-primary text-white text-sm rounded-md hover:bg-primary/90 disabled:opacity-50"
        >
          {loading ? "Embedding..." : "Generate Embeddings"}
        </button>
        {error && <span className="text-xs text-red-500">{error}</span>}
      </div>

      {selectedA && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">
            {selectedB
              ? `Similarity between selected chunks:`
              : `Selected: ${selectedA.slice(0, 8)}... — click another point to compare`}
          </span>
          {similarity != null && (
            <span className="font-semibold text-primary">
              cosine = {similarity.toFixed(4)}
            </span>
          )}
        </div>
      )}

      <ScatterPlot
        points={points}
        selectedA={selectedA}
        selectedB={selectedB}
        onSelect={handleSelect}
      />

      <p className="text-xs text-muted-foreground">
        Visualization uses PCA (2D projection). Click a point to select it, click another to compare cosine similarity.
      </p>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/embeddings/
git commit -m "feat: Embedding Explorer — scatter plot, similarity calculator"
```

---

### Task 16: Panel Chat Interface

**Files:**
- Create: `frontend/src/components/chat/ChatInterface.tsx`
- Create: `frontend/src/components/chat/RetrievalPanel.tsx`
- Create: `frontend/src/components/chat/PromptBuilderPanel.tsx`

- [ ] **Step 1: Utwórz `frontend/src/components/chat/RetrievalPanel.tsx`**

```tsx
import { RetrievedChunk } from "../../types";

interface RetrievalPanelProps {
  chunks: RetrievedChunk[];
  topK: number;
  onTopKChange: (k: number) => void;
}

export function RetrievalPanel({ chunks, topK, onTopKChange }: RetrievalPanelProps) {
  return (
    <div className="border rounded-lg bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Retrieved Chunks</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">top-k:</span>
          <input
            type="number" min={1} max={20} value={topK}
            onChange={(e) => onTopKChange(Number(e.target.value))}
            className="w-12 text-xs border border-border rounded px-1.5 py-0.5 text-center"
          />
        </div>
      </div>

      {chunks.length === 0 ? (
        <p className="text-xs text-muted-foreground">Ask a question to see retrieved chunks.</p>
      ) : (
        <div className="space-y-2 max-h-[300px] overflow-auto">
          {chunks.map((chunk) => (
            <div key={chunk.chunk_id} className="border border-border rounded p-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">#{chunk.rank}</span>
                <span className="text-xs font-medium text-primary">
                  score: {chunk.score.toFixed(4)}
                </span>
              </div>
              <p className="text-xs leading-relaxed line-clamp-3">{chunk.content}</p>
              <p className="text-xs text-muted-foreground mt-1">
                doc: {chunk.document_name || chunk.document_id.slice(0, 8)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Utwórz `frontend/src/components/chat/PromptBuilderPanel.tsx`**

```tsx
import { useState, useEffect } from "react";
import { PromptData } from "../../types";
import { api } from "../../api/client";

interface PromptBuilderPanelProps {
  promptData: PromptData | null;
  onSystemPromptChange: (p: string) => void;
}

export function PromptBuilderPanel({ promptData, onSystemPromptChange }: PromptBuilderPanelProps) {
  const [editing, setEditing] = useState(false);
  const [sysPrompt, setSysPrompt] = useState("");

  useEffect(() => {
    if (promptData?.system_message) setSysPrompt(promptData.system_message);
  }, [promptData?.system_message]);

  async function saveSystemPrompt() {
    await api.updateSystemPrompt(sysPrompt);
    onSystemPromptChange(sysPrompt);
    setEditing(false);
  }

  return (
    <div className="border rounded-lg bg-white p-4 space-y-3">
      <h3 className="text-sm font-semibold">Prompt Builder</h3>

      {promptData ? (
        <>
          <div className="grid grid-cols-4 gap-2">
            {[
              { label: "System", value: promptData.token_counts.system },
              { label: "Context", value: promptData.token_counts.context },
              { label: "Query", value: promptData.token_counts.query },
              { label: "Total", value: promptData.token_counts.total },
            ].map(({ label, value }) => (
              <div key={label} className="text-center border rounded p-2">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="text-sm font-semibold">{value}</p>
              </div>
            ))}
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground uppercase">System prompt</span>
              <button
                onClick={() => setEditing(!editing)}
                className="text-xs text-primary hover:underline"
              >
                {editing ? "Cancel" : "Edit"}
              </button>
            </div>
            {editing ? (
              <div className="space-y-1">
                <textarea
                  value={sysPrompt}
                  onChange={(e) => setSysPrompt(e.target.value)}
                  rows={4}
                  className="w-full text-xs border border-border rounded p-2 font-mono resize-none"
                />
                <button
                  onClick={saveSystemPrompt}
                  className="text-xs bg-primary text-white px-2 py-1 rounded"
                >
                  Save
                </button>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground line-clamp-2 font-mono">
                {promptData.system_message}
              </p>
            )}
          </div>

          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase mb-1">Full prompt</p>
            <pre className="text-xs bg-muted/50 rounded p-2 overflow-auto max-h-32 whitespace-pre-wrap font-mono">
              {promptData.full_prompt}
            </pre>
          </div>
        </>
      ) : (
        <p className="text-xs text-muted-foreground">Ask a question to see the assembled prompt.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Utwórz `frontend/src/components/chat/ChatInterface.tsx`**

```tsx
import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { RetrievedChunk, PromptData } from "../../types";
import { streamChat, api } from "../../api/client";
import { RetrievalPanel } from "./RetrievalPanel";
import { PromptBuilderPanel } from "./PromptBuilderPanel";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(5);
  const [retrieval, setRetrieval] = useState<RetrievedChunk[]>([]);
  const [promptData, setPromptData] = useState<PromptData | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const query = input.trim();
    if (!query || loading) return;
    setInput("");
    setLoading(true);

    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    streamChat(
      query,
      topK,
      (token) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: updated[updated.length - 1].content + token,
          };
          return updated;
        });
      },
      async () => {
        setLoading(false);
        try {
          const [ret, prompt] = await Promise.all([api.getRetrieval(), api.getPrompt()]);
          setRetrieval(ret);
          setPromptData(prompt);
        } catch {}
      },
    );
  }

  return (
    <div className="h-full flex gap-4 p-6">
      {/* Chat */}
      <div className="flex-1 flex flex-col border rounded-lg bg-white overflow-hidden">
        <div className="flex-1 overflow-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground text-center mt-8">
              Ask a question about your uploaded documents.
            </p>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === "user"
                    ? "bg-primary text-white"
                    : "bg-muted text-foreground"
                }`}
              >
                {msg.content || (loading && i === messages.length - 1 ? "▋" : "")}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        <div className="border-t p-3 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Ask a question..."
            className="flex-1 text-sm border border-border rounded-md px-3 py-1.5 outline-none focus:border-primary"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="p-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Right panels */}
      <div className="w-80 flex flex-col gap-4 overflow-auto">
        <RetrievalPanel chunks={retrieval} topK={topK} onTopKChange={setTopK} />
        <PromptBuilderPanel
          promptData={promptData}
          onSystemPromptChange={() => {}}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/chat/
git commit -m "feat: Chat Interface — SSE streaming, retrieval panel, prompt builder"
```

---

### Task 17: Panel Metrics & App.tsx finalizacja

**Files:**
- Create: `frontend/src/components/metrics/MetricsPanel.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Utwórz `frontend/src/components/metrics/MetricsPanel.tsx`**

```tsx
import { useState, useEffect } from "react";
import { SessionMetrics } from "../../types";
import { api } from "../../api/client";

export function MetricsPanel() {
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    api.getSessionMetrics().then(setMetrics).catch(console.error);
  }, []);

  async function handleReset() {
    if (!confirm("Reset all data (documents, chunks, embeddings, metrics)?")) return;
    setResetting(true);
    await api.resetAll();
    setResetting(false);
    setMetrics(null);
    window.location.reload();
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-sm">Metrics & Logs</h2>
        <button
          onClick={handleReset}
          disabled={resetting}
          className="text-xs px-3 py-1.5 border border-red-300 text-red-500 rounded-md hover:bg-red-50"
        >
          {resetting ? "Resetting..." : "Clear All Data"}
        </button>
      </div>

      {metrics && (
        <>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Total Queries", value: metrics.total_queries },
              { label: "Total Tokens", value: metrics.total_tokens.toLocaleString() },
              { label: "Total Cost", value: `$${metrics.total_cost_usd.toFixed(4)}` },
            ].map(({ label, value }) => (
              <div key={label} className="border rounded-lg p-4 bg-white text-center">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="text-xl font-semibold mt-1">{value}</p>
              </div>
            ))}
          </div>

          <div className="border rounded-lg bg-white overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-muted/50">
                <tr>
                  {["Query", "Embed ms", "Retrieval ms", "LLM ms", "Tokens", "Cost"].map((h) => (
                    <th key={h} className="text-left px-3 py-2 text-muted-foreground font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metrics.queries.map((q) => (
                  <tr key={q.query_id} className="border-t border-border">
                    <td className="px-3 py-2 max-w-[180px] truncate">{q.query}</td>
                    <td className="px-3 py-2">{q.embedding_ms.toFixed(0)}</td>
                    <td className="px-3 py-2">{q.retrieval_ms.toFixed(0)}</td>
                    <td className="px-3 py-2">{q.llm_ms.toFixed(0)}</td>
                    <td className="px-3 py-2">{q.total_tokens}</td>
                    <td className="px-3 py-2">${q.estimated_cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {metrics.queries.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-4">No queries yet.</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Zaktualizuj `frontend/src/App.tsx`** (finalna wersja z prawdziwymi panelami)

```tsx
import { useState, useEffect } from "react";
import { Header } from "./components/layout/Header";
import { Sidebar } from "./components/layout/Sidebar";
import { Footer } from "./components/layout/Footer";
import { DocumentManager } from "./components/documents/DocumentManager";
import { ChunkingLab } from "./components/chunks/ChunkingLab";
import { EmbeddingExplorer } from "./components/embeddings/EmbeddingExplorer";
import { ChatInterface } from "./components/chat/ChatInterface";
import { MetricsPanel } from "./components/metrics/MetricsPanel";
import { Panel, SessionMetrics } from "./types";
import { api } from "./api/client";

export default function App() {
  const [activePanel, setActivePanel] = useState<Panel>("documents");
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);

  useEffect(() => {
    api.getSessionMetrics().then(setMetrics).catch(() => {});
    const interval = setInterval(() => {
      api.getSessionMetrics().then(setMetrics).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header metrics={metrics} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar active={activePanel} onChange={setActivePanel} />
        <main className="flex-1 overflow-auto bg-[#F9FAFB]">
          {activePanel === "documents" && <DocumentManager />}
          {activePanel === "chunks" && <ChunkingLab />}
          {activePanel === "embeddings" && <EmbeddingExplorer />}
          {activePanel === "chat" && <ChatInterface />}
          {activePanel === "metrics" && <MetricsPanel />}
        </main>
      </div>
      <Footer />
    </div>
  );
}
```

- [ ] **Step 3: Sprawdź TypeScript build**

```bash
cd frontend
npx tsc --noEmit
npm run dev
```

Usuń wszelkie błędy TypeScript przed commitem.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: all UI panels — metrics, complete App routing"
```

---

## Faza 8: Finalizacja i weryfikacja

### Task 18: Plik `.env`, README i uruchomienie end-to-end

**Files:**
- Create: `backend/.env` (na podstawie `.env.example`, nie commitować)
- Create: `.gitignore`

- [ ] **Step 1: Utwórz `.gitignore` w root projektu**

```
backend/.venv/
backend/__pycache__/
backend/**/__pycache__/
backend/.env
backend/chroma_data/
frontend/node_modules/
frontend/dist/
*.pyc
.DS_Store
```

- [ ] **Step 2: Utwórz `backend/.env` z prawdziwym kluczem API**

```
OPENAI_API_KEY=sk-...twój_klucz...
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4o-mini
CHROMA_PERSIST_DIR=./chroma_data
```

- [ ] **Step 3: Uruchom kompletny pipeline e2e**

Terminal 1 (backend):
```bash
cd backend
source .venv/Scripts/activate
uvicorn main:app --reload --port 8000
```

Terminal 2 (frontend):
```bash
cd frontend
npm run dev
```

- [ ] **Step 4: Przetestuj pełny pipeline**

1. Otwórz `http://localhost:5173`
2. **Documents**: wgraj plik `.txt` lub `.pdf`
3. **Chunking Lab**: wybierz dokument → Generate Chunks (fixed/recursive/semantic)
4. **Embeddings**: wybierz dokument → Generate Embeddings → sprawdź scatter plot → kliknij 2 punkty → sprawdź cosine similarity
5. **Chat**: zadaj pytanie → sprawdź streamed response → Retrieval Panel → Prompt Builder
6. **Metrics**: sprawdź tabele z czasami i kosztami

- [ ] **Step 5: Uruchom wszystkie testy backendu**

```bash
cd backend
pytest tests/ -v
```

Oczekiwany wynik: wszystkie testy pass.

- [ ] **Step 6: Final commit**

```bash
git add .gitignore backend/.env.example
git commit -m "chore: gitignore, env example — project complete"
```

---

## Checklist pokrycia wymagań PRD

| Wymaganie | Task |
|---|---|
| ST-101 Upload PDF/DOCX/TXT | Task 5 |
| ST-102 Preview raw text | Task 13 |
| ST-103 Delete document | Task 5, 13 |
| ST-201 Chunking strategies | Task 6, 7, 8 |
| ST-202 Adjust chunk size/overlap | Task 8, 14 |
| ST-203 Chunk boundaries highlight | Task 14 (color bands) |
| ST-204 Chunk statistics | Task 8, 14 |
| ST-205 Side-by-side comparison | *not in scope — future feature* |
| ST-301 2D embedding visualization | Task 9, 15 |
| ST-302 Cosine similarity between chunks | Task 9, 15 |
| ST-303 Token count per chunk | Task 8 |
| ST-401 Full RAG pipeline | Task 11, 16 |
| ST-402 Retrieved chunks with scores | Task 11, 16 |
| ST-403 Top-k parameter | Task 11, 16 |
| ST-404 Full assembled prompt | Task 10, 16 |
| ST-405 Editable system prompt | Task 11, 16 |
| ST-406 Token count breakdown | Task 10, 16 |
| ST-501 Pipeline stage timing | Task 11, 17 |
| ST-502 Token usage + cost | Task 11, 17 |
| ST-503 Cumulative session stats | Task 11, 17 |
| ST-601 ChromaDB persistence | Task 9 |
| ST-602 Clear all data | Task 11, 17 |
