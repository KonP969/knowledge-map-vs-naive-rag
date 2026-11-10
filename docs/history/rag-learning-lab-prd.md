> **Historical document.** This is the original PRD for *RAG Learning Lab*, the classic
> chunk → embed → vector-search RAG app this repository started as. The project has since
> become Knowledge-Map RAG, which deliberately replaces that pipeline with a knowledge graph
> — see the [README](../../README.md) for what the app does today. Kept for context only.

```markdown
<PRD>

# RAG Learning Lab — Product Requirements Document

## a. Introduction

This document defines the product requirements for **RAG Learning Lab** — a personal, educational web application designed to help the developer (single user) learn and understand the full Retrieval-Augmented Generation (RAG) pipeline hands-on. The application provides a transparent, glass-box experience: every stage of the RAG process — from document ingestion through chunking, embedding, retrieval, prompt assembly, to LLM response — is fully visible and inspectable via dedicated UI panels.

This PRD is intended to be used as a scoped plan for an AI coding tool to build the application from scratch.

---

## b. Product overview

- **Product name:** RAG Learning Lab
- **One-sentence description:** A personal educational web app that lets you chat with your documents while seeing exactly what happens at every stage of the RAG pipeline — chunking, embeddings, retrieval scoring, prompt assembly, and LLM response.
- **Platform:** Web application (local development, single user)
- **Core value:** Full transparency into the RAG pipeline for learning purposes — no black boxes.

---

## c. Goals and objectives

1. **Learn by doing:** Provide a hands-on environment to experiment with every component of a RAG system.
2. **Full transparency:** Expose the inner workings of each pipeline stage through dedicated, interactive panels.
3. **Experimentation:** Allow the user to change chunking strategies, observe how embeddings cluster, see which chunks are retrieved and why, and inspect the final prompt sent to the LLM.
4. **Minimal overhead:** No authentication, no Docker, no multi-user complexity — just a clean, fast local tool.
5. **Extensibility:** Architecture should allow future integration of alternative LLM providers (e.g., Ollama for local open-source models).

---

## d. Target audience

- **Primary user:** The developer themselves (Konrad) — a single user learning RAG concepts.
- **Technical level:** Intermediate — comfortable with Python, APIs, and web development; learning data engineering and AI/ML pipeline concepts.
- **Use context:** Local development machine, personal learning sessions with sample documents (product catalogs, brand guidelines, etc.).

---

## e. Features and requirements

### E1. Document upload and management

- Upload documents in PDF, DOCX, and TXT formats.
- Display a list of uploaded documents with metadata (name, size, page count, upload date).
- Preview raw extracted text from each document.
- Delete documents and their associated embeddings from the vector store.

### E2. Chunking panel (educational)

- Visualize how a document is split into chunks.
- Support multiple chunking strategies the user can switch between:
  - **Fixed-size** (with configurable chunk size and overlap)
  - **Recursive character splitting** (with configurable separators)
  - **Semantic chunking** (sentence-boundary aware)
- Side-by-side comparison of chunk outputs from different strategies.
- Display chunk count, average chunk length, and overlap statistics.
- Highlight chunk boundaries within the original document text.

### E3. Embeddings panel (educational)

- Show embedding vectors (truncated/summarized) for each chunk.
- 2D visualization of embedding space (t-SNE or UMAP projection) — chunks plotted as dots, colored by source document.
- Display cosine similarity between selected chunks.
- Show which embedding model is being used and token count per chunk.

### E4. Chat interface

- Simple chat input where the user types a question.
- Streamed LLM responses with source attribution (which chunks contributed to the answer).
- Conversation history within the current session (in-memory, no persistence required).

### E5. Retrieval panel (educational)

- After each query, display:
  - The list of retrieved chunks, ranked by similarity score.
  - The similarity score for each chunk.
  - A snippet of the chunk content.
  - Which document each chunk came from.
- Allow the user to adjust the number of chunks retrieved (top-k parameter).

### E6. Prompt builder panel (educational)

- Show the fully assembled prompt sent to the LLM, including:
  - System message
  - Retrieved context (chunks)
  - User query
- Editable system prompt template so the user can experiment with different instructions.
- Token count breakdown: system message tokens, context tokens, query tokens, total tokens.

### E7. Logs and metrics panel

- Processing time for each pipeline stage (chunking, embedding, retrieval, LLM call).
- Token usage per API call (prompt tokens, completion tokens, total).
- Estimated cost per API call (based on OpenAI pricing).
- Cumulative session stats (total queries, total tokens, total cost).

---

## f. User stories and acceptance criteria

### Document management

| ID | User story | Acceptance criteria |
|---|---|---|
| ST-101 | As a user, I want to upload PDF, DOCX, and TXT files so I can use them as my RAG knowledge base. | File upload accepts .pdf, .docx, .txt. Files are parsed and raw text is extracted. Uploaded files appear in the document list with metadata. |
| ST-102 | As a user, I want to preview the raw extracted text from a document so I can verify the extraction quality. | Clicking a document shows its full extracted text in a scrollable panel. |
| ST-103 | As a user, I want to delete a document and all its associated data (chunks, embeddings) so I can start fresh. | Deleting a document removes it from the list, deletes chunks from vector store, and confirms deletion. |

### Chunking

| ID | User story | Acceptance criteria |
|---|---|---|
| ST-201 | As a user, I want to select a chunking strategy (fixed-size, recursive, semantic) so I can compare how each one splits my document. | A dropdown or toggle lets the user switch strategies. Chunks are regenerated on strategy change. |
| ST-202 | As a user, I want to adjust chunk size and overlap parameters so I can experiment with different configurations. | Sliders or inputs for chunk size (100–2000 chars) and overlap (0–50%). Chunks update on parameter change. |
| ST-203 | As a user, I want to see chunk boundaries highlighted in the original text so I can understand where splits happen. | Original text view shows colored highlights or separators at chunk boundaries. |
| ST-204 | As a user, I want to see chunk statistics (count, avg length, overlap) so I can compare strategies quantitatively. | Stats bar shows chunk count, average chunk length, min/max length, and overlap percentage. |
| ST-205 | As a user, I want to compare two chunking strategies side by side so I can see the differences visually. | A split-view mode shows chunks from two selected strategies next to each other. |

### Embeddings

| ID | User story | Acceptance criteria |
|---|---|---|
| ST-301 | As a user, I want to see a 2D visualization of my chunk embeddings so I can understand how they cluster. | A scatter plot (t-SNE or UMAP) renders after embedding, with dots colored by source document. |
| ST-302 | As a user, I want to see the cosine similarity between two selected chunks so I can understand vector distances. | Clicking two chunks in the visualization shows their cosine similarity score. |
| ST-303 | As a user, I want to see the token count for each chunk so I can understand tokenization overhead. | Each chunk in the list displays its token count (via tiktoken). |

### Chat and retrieval

| ID | User story | Acceptance criteria |
|---|---|---|
| ST-401 | As a user, I want to type a question and receive an answer generated from my documents so I can test the RAG pipeline end-to-end. | Typing a question and pressing Enter triggers the full pipeline: embed query → retrieve chunks → build prompt → call LLM → display answer. |
| ST-402 | As a user, I want to see which chunks were retrieved for my query, with their similarity scores, so I can evaluate retrieval quality. | The retrieval panel shows a ranked list of chunks with scores, snippets, and source document names. |
| ST-403 | As a user, I want to adjust the top-k parameter so I can control how many chunks are included in context. | A slider or input lets the user set top-k (1–20). Changing it re-runs retrieval for the last query. |
| ST-404 | As a user, I want to see the full assembled prompt sent to the LLM so I can understand prompt engineering in context. | The prompt builder panel shows the complete prompt with system message, context block, and user query clearly separated. |
| ST-405 | As a user, I want to edit the system prompt template so I can experiment with different instructions. | A text area allows editing the system prompt. Changes take effect on the next query. |
| ST-406 | As a user, I want to see the token count breakdown (system, context, query, total) so I can manage context window usage. | Token counts are displayed per section and as a total, updated after each query. |

### Logs and metrics

| ID | User story | Acceptance criteria |
|---|---|---|
| ST-501 | As a user, I want to see processing time for each pipeline stage so I can identify bottlenecks. | A timeline or table shows duration for: chunking, embedding, retrieval, LLM call. |
| ST-502 | As a user, I want to see token usage and estimated cost per API call so I can track spending. | Each query logs prompt tokens, completion tokens, total tokens, and estimated USD cost. |
| ST-503 | As a user, I want to see cumulative session stats so I can track total usage over a learning session. | A summary bar shows total queries, total tokens, and total estimated cost for the session. |

### Database and vector store

| ID | User story | Acceptance criteria |
|---|---|---|
| ST-601 | As a user, I want my document chunks and embeddings stored in a local vector database so I can query them without re-processing. | ChromaDB collection persists chunks and embeddings locally. Re-uploading the same document does not create duplicates. |
| ST-602 | As a user, I want to clear the entire vector store so I can reset the system completely. | A "Clear all data" button wipes ChromaDB and the document list, with a confirmation dialog. |

---

## g. Technical requirements / stack

### Frontend

| Technology | Purpose |
|---|---|
| **React** (Vite) | SPA framework |
| **TypeScript** | Type safety |
| **TailwindCSS** | Utility-first styling |
| **shadcn/ui** | Component library (light, minimal theme) |
| **Lucide Icons** | Icon system |
| **React Hook Form** | Form handling (upload, settings) |
| **Recharts** or **D3.js** | Embedding visualization (scatter plots) |

### Backend

| Technology | Purpose |
|---|---|
| **Python 3.11+** | Backend runtime |
| **FastAPI** | REST API framework |
| **Uvicorn** | ASGI server |
| **PyPDF2** | PDF text extraction |
| **python-docx** | DOCX text extraction |
| **tiktoken** | Token counting (OpenAI tokenizer) |
| **scikit-learn** (UMAP/t-SNE) | Dimensionality reduction for embedding visualization |
| **ChromaDB** | Local vector store |
| **OpenAI Python SDK** | LLM and embedding API calls |

### Architecture notes

- **No Docker** — run directly with `npm run dev` (frontend) and `uvicorn` (backend).
- **No authentication** — single-user local app.
- **No external database** — ChromaDB handles all vector storage locally (file-based persistence).
- **Chunking is implemented manually** (no LangChain) — custom Python modules for each strategy, maximizing learning value.
- **API communication** — React frontend communicates with FastAPI backend via REST endpoints.
- **Streaming** — LLM responses streamed to frontend via Server-Sent Events (SSE).

### API endpoints (suggested)

```
POST   /api/documents/upload        — Upload and parse a document
GET    /api/documents                — List all documents
GET    /api/documents/{id}           — Get document details and raw text
DELETE /api/documents/{id}           — Delete document and associated data

POST   /api/chunks/generate          — Generate chunks with given strategy/params
GET    /api/chunks/{document_id}     — Get chunks for a document

POST   /api/embeddings/generate      — Generate and store embeddings for chunks
GET    /api/embeddings/visualize     — Get 2D projection data for scatter plot
GET    /api/embeddings/similarity    — Get cosine similarity between two chunks

POST   /api/chat                     — Send query, run full RAG pipeline (SSE stream)
GET    /api/chat/retrieval           — Get retrieval details for last query
GET    /api/chat/prompt              — Get assembled prompt for last query

GET    /api/metrics/session          — Get cumulative session metrics

DELETE /api/data/reset               — Clear all data (vector store + documents)
```

---

## h. Design and user interface

### Design principles

- **Light, minimalist theme** — white/light gray background, clean typography, subtle borders.
- **Panel-based layout** — the main view is divided into functional panels that the user can navigate between.
- **Educational focus** — every panel is designed to teach, not just display. Use labels, tooltips, and inline explanations.

### Layout structure

```
┌─────────────────────────────────────────────────────┐
│  Header: RAG Learning Lab  [Session Stats]          │
├──────────┬──────────────────────────────────────────┤
│          │                                          │
│ Sidebar  │  Main Content Area                       │
│          │                                          │
│ • Docs   │  (Switches based on active panel)        │
│ • Chunks │                                          │
│ • Embed  │  - Document Manager                      │
│ • Chat   │  - Chunking Lab                          │
│ • Logs   │  - Embedding Explorer                    │
│          │  - Chat + Retrieval + Prompt Builder      │
│          │  - Metrics & Logs                         │
│          │                                          │
├──────────┴──────────────────────────────────────────┤
│  Footer: Token usage | Cost | Pipeline timing       │
└─────────────────────────────────────────────────────┘
```

### Panel details

1. **Document Manager** — Upload area (drag & drop), document list with cards, raw text preview.
2. **Chunking Lab** — Strategy selector, parameter sliders, chunk list with highlighted boundaries, side-by-side comparison mode, stats bar.
3. **Embedding Explorer** — 2D scatter plot (interactive, zoomable), chunk detail on hover/click, similarity calculator.
4. **Chat Interface** — Split into three sub-panels:
   - Left: Chat conversation (messages + streamed responses)
   - Right-top: Retrieval panel (ranked chunks with scores)
   - Right-bottom: Prompt builder (full assembled prompt, token breakdown)
5. **Metrics & Logs** — Timeline of pipeline stages per query, per-query cost/token table, cumulative session summary.

### Visual style

- **Colors:** White background (#FFFFFF), light gray panels (#F9FAFB), subtle borders (#E5E7EB), primary accent blue (#3B82F6) for interactive elements.
- **Typography:** System font stack (Inter or similar), clear hierarchy with font size and weight.
- **Components:** shadcn/ui defaults with light theme — cards, tabs, sliders, tooltips, badges.
- **Icons:** Lucide Icons throughout for consistent, minimal iconography.

---

## Future feature ideas

- **Ollama integration** — connect local open-source models (Llama, Mistral) and compare responses side-by-side with OpenAI.
- **A/B chunking comparison** — automated side-by-side evaluation of chunking strategies on the same query.
- **Multi-model comparison** — run the same query against GPT-4o, GPT-4o-mini, and local models, compare quality and speed.
- **Experiment history** — save and replay past experiments (chunking configs, queries, results) for comparison over time.
- **Export to CSV/Excel** — export retrieval results, metrics, and experiment data for offline analysis.
- **Benchmarking suite** — automated evaluation of answer quality (faithfulness, relevance, hallucination detection).
- **Hybrid search** — combine vector similarity with keyword search (BM25) and visualize the difference.

</PRD>
```
