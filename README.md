# RAG 2.0 — Karpathy Method

A local, educational web app that implements **Knowledge-Map RAG** — an experiment
inspired by Andrej Karpathy's critique of naive retrieval-augmented generation.
Instead of chunking documents and doing vector search, the system extracts a
structured knowledge graph from every source at ingest time and answers questions
by reasoning over that graph — showing its work at every step.

This is a research/learning project: the point is to make the retrieval pipeline
legible, not to be a production RAG stack.

## Why not naive RAG?

Classic RAG (chunk → embed → vector search → stuff context → LLM) struggles with:

- **Conflicting facts** — two sources disagree; the model gets both and blends them
- **Multi-hop questions** — the answer needs facts connected across several documents
- **Temporal updates** — a newer source contradicts an older one, but the old chunk wins on similarity score

Knowledge-Map RAG extracts structure at ingest time — entities, concepts, claims
(each with provenance), and edges — then retrieves through a 5-stage reasoning
pipeline. Every sentence in an answer traces back to a specific claim.

## Architecture

```
  INGEST                            RETRIEVAL
  ──────                            ─────────
  Source file                      User question
     │                                  │
  1. Parse       (deterministic)    1. Intent Parser     (LLM)
  2. Classify    (LLM)              2. Candidate Filter   (lexical + semantic)
  3. Resolve     (deterministic)    3. Selection          (LLM)
  4. Conflict Detect (LLM)          4. Context Assembly
  5. Save + Reindex                 5. Answer Generator   (LLM)
     │                                  │
  wiki_data/ (Markdown + JSONL)     QueryTrace (full audit trail)
```

If retrieval isn't confident, a 10-tool **agent fallback** takes over.

**Storage:** flat files — Markdown pages plus JSONL claim/edge logs. No database,
no vector store service. Portable, readable, diffable.

## Panels

| Panel | What it does |
|---|---|
| **Ingest** | Watch a file move through the 5-stage ingest pipeline. Educational view — use **Sources** to actually add files. |
| **Sources** | Every ingested source with its tags, summary, key takeaways, and generated questions. Upload files or import from a URL. |
| **Wiki Chat** | Ask a question and see the full retrieval trace: intent, scored candidates, LLM selection, assembled context, cited answer. |
| **Knowledge Map** | The graph of entities and concepts. Click a node for its claims, edges, and sources. |
| **Lint** | Integrity checks over the wiki — orphan nodes, missing provenance, contradictions, alias collisions, stale summaries. Some auto-fix. |
| **Metrics** | Session token usage and estimated cost. |
| **Tutorial** | In-app guide to the architecture, plus interactive walkthroughs. |

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI · Python 3.11+ |
| Frontend | React 19 · TypeScript · Vite · Tailwind |
| LLM | OpenAI API (`gpt-4o-mini` and `text-embedding-3-small` by default) |
| Storage | Flat files — Markdown + JSONL |

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI API key

### 1. Backend environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then put your OPENAI_API_KEY in .env
```

### 2. Frontend dependencies

```bash
cd frontend
npm install
```

### 3. Run both

```bash
./dev.sh        # macOS / Linux
.\dev.ps1       # Windows (PowerShell)
```

This starts the API on `http://localhost:8000` (Swagger at `/docs`) and the app on
`http://localhost:5173`. Vite proxies `/api` to the backend, so there's nothing
else to configure. Ctrl+C stops both.

To run them separately:

```bash
cd backend  && uvicorn main:app --port 8000
cd frontend && npm run dev
```

> On some Windows setups `uvicorn --reload` dies after the first reload and serves
> stale code. If you hit that, run without `--reload` and restart manually.

## Try it without ingesting anything

A `wiki_data/default` starts empty. To explore the app with a pre-built graph, point
it at the bundled demo corpus (3 Wikipedia articles on RAG, vector databases, and
word embeddings):

```bash
cd backend
WIKI_DATA_DIR=wiki_data/.example uvicorn main:app --port 8000
```

**Sources**, **Knowledge Map**, and **Lint** work with no API key. **Wiki Chat** and
**Ingest** call OpenAI, so they still need one. See
`backend/wiki_data/.example/README.md`.

Sample questions:

- *What problem with large language models does retrieval-augmented generation address?*
- *How do vector databases find similar records?*
- *How are word embeddings related to vector search?*

## Using your own sources

1. In **Sources**, drop in `.pdf`, `.docx`, `.txt`, or `.md` files, or import from a URL
2. Wait for the ingest pipeline to finish
3. Ask questions in **Wiki Chat** and read the trace
4. Explore relationships in **Knowledge Map**
5. Run **Lint** every few ingests to catch contradictions and gaps

Retrieval works best with specific, factual questions ("Who founded X?", "How does A
differ from B?") over several sources that reinforce each other. Very broad prompts
("tell me everything") work poorly by design.

## Project layout

```
backend/
├── api/                    FastAPI routers
├── models/                 Pydantic models
├── services/
│   ├── ingest_pipeline.py  5-stage ingest
│   ├── retrieval/          5-stage retrieval + agent fallback
│   ├── lint/               integrity checks
│   ├── wiki_store.py       read/write wiki_data/
│   └── wiki_index.py       regenerate 00-Index
├── scripts/                eval + maintenance scripts
├── tests/                  ~465 unit + integration tests
└── wiki_data/
    ├── default/            your knowledge base (git-ignored, starts empty)
    └── .example/           bundled demo corpus

frontend/src/
├── api/client.ts           typed API client
└── components/             one folder per panel
```

## Wiki data structure

```
wiki_data/<name>/
├── raw/                    parsed copies of each source
└── wiki/
    ├── 00-Index/           auto-generated master index
    ├── 10-Concepts/        one Markdown file per concept
    ├── 20-Entities/        one Markdown file per entity
    ├── 30-Sources/         source metadata pages
    ├── claims.jsonl        every extracted claim
    ├── edges.jsonl         every extracted relation
    └── embeddings/         claim vectors for semantic recall
```

## Tests

```bash
cd backend && python -m pytest -q
```

## License

MIT — see [LICENSE](LICENSE). The demo corpus under `backend/wiki_data/.example/`
is text from Wikipedia (CC BY-SA 4.0); see its `ATTRIBUTION.md`.
