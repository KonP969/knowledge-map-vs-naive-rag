# Embeddings — Improvements Design

**Date:** 2026-04-11  
**Scope:** Bug fixes #5 and #6, feature #7  
**Status:** Approved

---

## Problem Summary

Three issues identified in the Embeddings panel:

1. **Bug #5** — "Clear All Data" does not clear embeddings from ChromaDB persistent storage under certain conditions.
2. **Bug #6** — The scatter plot legend shows truncated document IDs instead of file names (caused by bug #5).
3. **Feature #7** — Embeddings can only be generated one document at a time; no status visibility; no per-document delete in the UI.

---

## Architecture Overview

- **Backend:** FastAPI + ChromaDB PersistentClient
- **Frontend:** React + Recharts
- **Embedding state** lives in ChromaDB (`./chroma_data/`) — persistent across server restarts
- **Document state** lives in `_documents` dict in `api/documents.py` — in-memory only

---

## Bug #5 — Clear All Does Not Erase Embeddings

### Root Cause

`reset_collection()` in `services/vector_store.py` has this guard:

```python
if _client is not None:
    _client.delete_collection(COLLECTION_NAME)
```

If the server has just started and no embeddings endpoint was called, `_client` is `None`. The deletion is skipped. `_get_collection()` then creates a new ChromaDB client from `./chroma_data/` — loading the old persisted data from disk.

### Fix

Remove the `if _client is not None` guard. Always ensure the client is initialized before attempting deletion:

```python
def reset_collection() -> None:
    global _client, _collection
    _collection = None
    col = _get_collection()   # ensures _client is initialized
    try:
        _client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    _collection = None
    _get_collection()         # recreate empty collection
```

### Frontend Refresh After Reset

`EmbeddingExplorer` renders stale `points` state after a reset because its `useEffect` only runs on mount.

~~Fix: `App.tsx` passes a `refreshKey: number` prop to `EmbeddingExplorer`. `MetricsPanel` receives an `onReset` callback that increments `refreshKey`. `EmbeddingExplorer`'s `useEffect` depends on `[refreshKey]` — re-fetches documents and visualization on each reset.~~

**Not implemented — superseded:** `MetricsPanel.handleReset()` already calls `window.location.reload()` after reset, which fully reinitialises all component state. The `refreshKey` mechanism was unnecessary.

---

## Bug #6 — Legend Shows IDs Instead of File Names

### Root Cause

Caused by bug #5. When old embeddings survive a reset, the documents in `_documents` are cleared, so `get_document_name(doc_id)` returns `doc_id[:12]` (fallback). ChromaDB metadata retains the old `document_name` value from embed time, so the name is correct as long as it was stored correctly at generation time.

After fixing bug #5, the legend will display correct names.

### Minor Enhancement

Add a "Źródła:" label before the legend items in `ScatterPlot.tsx` to make the legend more visible and clearly labeled.

---

## Feature #7 — Multi-Generate, Status Visibility, Per-Document Delete

### Backend

#### New: `GET /api/embeddings/status`

Returns which documents currently have embeddings in the vector store.

Response:
```json
[
  { "document_id": "abc123", "chunk_count": 42 },
  { "document_id": "def456", "chunk_count": 18 }
]
```

Implementation: call `get_all_embeddings()`, extract unique `document_id` values from metadatas, count chunks per document.

#### New: `DELETE /api/embeddings/by-document/{document_id}`

Deletes all embeddings for a specific document. Calls existing `delete_by_document(document_id)` from `vector_store.py`.

Response: `{ "deleted": "<document_id>" }`

No new service logic needed — reuses existing `delete_by_document`.

### Frontend — `EmbeddingExplorer` Redesign

The component is split into two areas:

**1. Document Source List (top)**

A table/list of all documents, each row showing:
- Checkbox (enabled only if document has NO embeddings yet)
- Document name
- Status badge: green "✓ N chunków" if has embeddings, gray "—" if not
- "Usuń" button (shown only if has embeddings) — calls `DELETE /embeddings/by-document/{id}`, refreshes status

**2. Batch Generate Controls**

- "Generate Selected (N)" button — active when ≥1 document with no embeddings is checked
- Progress message: "Embeduję 2/3: artykul.txt..."
- On click: iterate `for...of` over selected docs, `await api.generateEmbeddings(id)` for each, update progress inline
- After each successful embed: refresh status list and visualization

**3. Scatter Plot (bottom)**

Unchanged — shows all embeddings from all documents with color-coded legend.

### State Shape (frontend)

```ts
embeddingStatus: Array<{ document_id: string; chunk_count: number }>
selectedForEmbed: Set<string>       // document IDs checked for generation
embedProgress: { current: number; total: number; currentName: string } | null
```

### API Client Additions (`client.ts`)

```ts
getEmbeddingStatus: () => request<EmbeddingStatus[]>("/embeddings/status"),
deleteEmbeddingsByDocument: (documentId: string) =>
  request<{ deleted: string }>(`/embeddings/by-document/${documentId}`, { method: "DELETE" }),
```

### Types Addition (`types/index.ts`)

```ts
export interface EmbeddingStatus {
  document_id: string;
  chunk_count: number;
}
```

---

## Files Changed

### Backend
| File | Change |
|------|--------|
| `services/vector_store.py` | Fix `reset_collection()` |
| `api/embeddings.py` | Add `GET /status` and `DELETE /by-document/{id}` endpoints |

### Frontend
| File | Change |
|------|--------|
| `src/types/index.ts` | Add `EmbeddingStatus` interface |
| `src/api/client.ts` | Add `getEmbeddingStatus`, `deleteEmbeddingsByDocument` |
| `src/components/embeddings/EmbeddingExplorer.tsx` | Full redesign — document list, status badges, multi-select, progress |
| `src/components/embeddings/ScatterPlot.tsx` | Add "Źródła:" label to legend |
| `src/App.tsx` | Add `refreshKey` state + `onReset` callback wiring |

---

## Out of Scope

- Parallel embedding generation (sequential is sufficient and safer for OpenAI rate limits)
- Re-generating embeddings for documents that already have them (separate UX decision)
- Persisting document state across server restarts (in-memory by design)
