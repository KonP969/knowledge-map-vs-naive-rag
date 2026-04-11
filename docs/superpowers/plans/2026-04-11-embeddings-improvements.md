# Embeddings Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two bugs (Clear All not erasing ChromaDB embeddings, legend showing IDs) and add multi-generate, per-document status badges, and per-document delete to the Embeddings panel.

**Architecture:** Backend gets one bug fix in `reset_collection()` and two new endpoints; frontend gets a redesigned `EmbeddingExplorer` with a document-list table and sequential batch generation.

**Tech Stack:** Python 3.9, FastAPI, ChromaDB PersistentClient, React 18, TypeScript, Recharts, Tailwind CSS

---

## File Map

| File | Change |
|------|--------|
| `backend/services/vector_store.py` | Fix `reset_collection()` |
| `backend/api/embeddings.py` | Add `GET /status` and `DELETE /by-document/{doc_id}` |
| `backend/tests/test_embeddings_logic.py` | New: unit tests for status helper and reset logic |
| `frontend/src/types/index.ts` | Add `EmbeddingStatus` interface |
| `frontend/src/api/client.ts` | Add `getEmbeddingStatus`, `deleteEmbeddingsByDocument` |
| `frontend/src/components/embeddings/EmbeddingExplorer.tsx` | Full redesign |
| `frontend/src/components/embeddings/ScatterPlot.tsx` | Add "Źródła:" label to legend |

---

## Task 1: Fix `reset_collection()` in vector_store.py

**Files:**
- Modify: `backend/services/vector_store.py`
- Test: `backend/tests/test_embeddings_logic.py` (new file)

**Context:**  
`reset_collection()` has a guard `if _client is not None`. If the server just started and no embeddings endpoint was called, `_client` is `None` — the deletion is skipped and `_get_collection()` loads old data from `./chroma_data/` on disk.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_embeddings_logic.py`:

```python
from services.vector_store import reset_collection, add_chunks, get_all_embeddings
import pytest


def test_reset_collection_clears_data():
    """reset_collection() must remove all previously added data."""
    add_chunks(
        chunk_ids=["test-id-1"],
        embeddings=[[0.1, 0.2, 0.3]],
        documents=["test document"],
        metadatas=[{"document_id": "doc-1", "document_name": "test.txt", "index": 0, "char_count": 13}],
    )
    data_before = get_all_embeddings()
    assert "test-id-1" in data_before["ids"]

    reset_collection()

    data_after = get_all_embeddings()
    assert data_after["ids"] == []


def test_reset_collection_works_when_called_before_any_add():
    """reset_collection() must not crash and must return empty store even if called cold."""
    reset_collection()  # called with _client potentially None
    data = get_all_embeddings()
    assert data["ids"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend
python -m pytest tests/test_embeddings_logic.py -v
```

`test_reset_collection_clears_data` may pass or fail depending on current state. `test_reset_collection_works_when_called_before_any_add` should pass (no crash, but data might not be empty if old data exists on disk).

Note which fail — proceed to the fix regardless.

- [ ] **Step 3: Fix `reset_collection()` in `backend/services/vector_store.py`**

Replace the current function (lines 66–74):

```python
def reset_collection() -> None:
    global _client, _collection
    _collection = None
    _get_collection()  # initialise _client from disk so we can delete
    try:
        _client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    _collection = None
    _get_collection()  # recreate empty collection
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend
python -m pytest tests/test_embeddings_logic.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/vector_store.py backend/tests/test_embeddings_logic.py
git commit -m "fix: reset_collection always clears ChromaDB data from disk"
```

---

## Task 2: Add `GET /api/embeddings/status` endpoint

**Files:**
- Modify: `backend/api/embeddings.py`
- Test: `backend/tests/test_embeddings_logic.py`

**Context:**  
Returns which document_ids currently have embeddings and how many chunks each has. Needed by the frontend to show status badges.

- [ ] **Step 1: Add the test**

Append to `backend/tests/test_embeddings_logic.py`:

```python
from services.vector_store import delete_by_document


def test_get_status_returns_doc_counts():
    """Status should list each document_id with its chunk count."""
    reset_collection()
    add_chunks(
        chunk_ids=["c1", "c2", "c3"],
        embeddings=[[0.1] * 3, [0.2] * 3, [0.3] * 3],
        documents=["chunk one", "chunk two", "chunk three"],
        metadatas=[
            {"document_id": "doc-A", "document_name": "a.txt", "index": 0, "char_count": 9},
            {"document_id": "doc-A", "document_name": "a.txt", "index": 1, "char_count": 9},
            {"document_id": "doc-B", "document_name": "b.txt", "index": 0, "char_count": 11},
        ],
    )

    from api.embeddings import _compute_status
    status = _compute_status()
    by_doc = {s["document_id"]: s["chunk_count"] for s in status}
    assert by_doc["doc-A"] == 2
    assert by_doc["doc-B"] == 1


def test_get_status_empty():
    reset_collection()
    from api.embeddings import _compute_status
    assert _compute_status() == []
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
python -m pytest tests/test_embeddings_logic.py::test_get_status_returns_doc_counts -v
```

Expected: FAIL — `_compute_status` not defined.

- [ ] **Step 3: Add `_compute_status` helper and the endpoint to `backend/api/embeddings.py`**

First, modify the existing import on line 3 from:
```python
from typing import List
```
to:
```python
from typing import List, Dict
```

Then add this helper function and new route after the existing `EmbeddingPoint` and `SimilarityRequest` models (before `@router.post("/generate")`):

```python
class EmbeddingStatus(BaseModel):
    document_id: str
    chunk_count: int


def _compute_status() -> List[Dict]:
    data = get_all_embeddings()
    counts: Dict[str, int] = {}
    for meta in data["metadatas"]:
        doc_id = meta.get("document_id", "")
        counts[doc_id] = counts.get(doc_id, 0) + 1
    return [{"document_id": doc_id, "chunk_count": count} for doc_id, count in counts.items()]


@router.get("/status", response_model=List[EmbeddingStatus])
def get_embedding_status():
    return _compute_status()
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend
python -m pytest tests/test_embeddings_logic.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/api/embeddings.py backend/tests/test_embeddings_logic.py
git commit -m "feat: add GET /api/embeddings/status endpoint"
```

---

## Task 3: Add `DELETE /api/embeddings/by-document/{document_id}` endpoint

**Files:**
- Modify: `backend/api/embeddings.py`
- Test: `backend/tests/test_embeddings_logic.py`

**Context:**  
Deletes all embeddings for a single document from ChromaDB. The service function `delete_by_document` already exists in `vector_store.py`.

- [ ] **Step 1: Add the test**

Append to `backend/tests/test_embeddings_logic.py`:

```python
def test_delete_by_document_removes_only_target():
    """Deleting doc-A embeddings must not touch doc-B embeddings."""
    reset_collection()
    add_chunks(
        chunk_ids=["d1", "d2", "d3"],
        embeddings=[[0.1] * 3, [0.2] * 3, [0.3] * 3],
        documents=["a1", "a2", "b1"],
        metadatas=[
            {"document_id": "doc-A", "document_name": "a.txt", "index": 0, "char_count": 2},
            {"document_id": "doc-A", "document_name": "a.txt", "index": 1, "char_count": 2},
            {"document_id": "doc-B", "document_name": "b.txt", "index": 0, "char_count": 2},
        ],
    )
    delete_by_document("doc-A")

    from api.embeddings import _compute_status
    status = _compute_status()
    ids = [s["document_id"] for s in status]
    assert "doc-A" not in ids
    assert "doc-B" in ids
```

- [ ] **Step 2: Run test to verify it fails (or passes — verify either way)**

```
cd backend
python -m pytest tests/test_embeddings_logic.py::test_delete_by_document_removes_only_target -v
```

- [ ] **Step 3: Add delete endpoint to `backend/api/embeddings.py`**

First, modify the vector_store import line (line 8) from:
```python
from services.vector_store import add_chunks, get_all_embeddings, query_chunks
```
to:
```python
from services.vector_store import add_chunks, get_all_embeddings, query_chunks, delete_by_document
```

Then add the route after `get_embedding_status()`:

```python
@router.delete("/by-document/{document_id}")
def delete_embeddings_by_document(document_id: str):
    delete_by_document(document_id)
    return {"deleted": document_id}
```

- [ ] **Step 4: Run all tests**

```
cd backend
python -m pytest tests/test_embeddings_logic.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/api/embeddings.py backend/tests/test_embeddings_logic.py
git commit -m "feat: add DELETE /api/embeddings/by-document/{document_id} endpoint"
```

---

## Task 4: Add frontend types and API client methods

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add `EmbeddingStatus` to `frontend/src/types/index.ts`**

After the `EmbeddingPoint` interface (after line 53):

```typescript
export interface EmbeddingStatus {
  document_id: string;
  chunk_count: number;
}
```

- [ ] **Step 2: Add two methods to the `api` object in `frontend/src/api/client.ts`**

After the `getSimilarity` line (after line 46):

```typescript
  getEmbeddingStatus: () =>
    request<import("../types").EmbeddingStatus[]>("/embeddings/status"),
  deleteEmbeddingsByDocument: (documentId: string) =>
    request<{ deleted: string }>(`/embeddings/by-document/${documentId}`, {
      method: "DELETE",
    }),
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add EmbeddingStatus type and API client methods"
```

---

## Task 5: Redesign `EmbeddingExplorer` component

**Files:**
- Modify: `frontend/src/components/embeddings/EmbeddingExplorer.tsx`

**Context:**  
Replace the current single-document dropdown + button with:
1. A table of all documents with status badges, checkboxes (for docs without embeddings), and delete buttons (for docs with embeddings)
2. A "Generate Selected (N)" button with inline progress
3. Scatter plot and similarity comparison below (unchanged logic)

- [ ] **Step 1: Replace the full content of `frontend/src/components/embeddings/EmbeddingExplorer.tsx`**

```typescript
import { useState, useEffect } from "react";
import type { DocumentMeta, EmbeddingPoint, EmbeddingStatus } from "../../types";
import { api } from "../../api/client";
import { ScatterPlot } from "./ScatterPlot";

interface EmbedProgress {
  current: number;
  total: number;
  currentName: string;
}

export function EmbeddingExplorer() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus[]>([]);
  const [points, setPoints] = useState<EmbeddingPoint[]>([]);
  const [selectedForEmbed, setSelectedForEmbed] = useState<Set<string>>(new Set());
  const [embedProgress, setEmbedProgress] = useState<EmbedProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedA, setSelectedA] = useState<string | null>(null);
  const [selectedB, setSelectedB] = useState<string | null>(null);
  const [similarity, setSimilarity] = useState<number | null>(null);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    try {
      const [docs, status, viz] = await Promise.all([
        api.listDocuments(),
        api.getEmbeddingStatus(),
        api.getVisualization(),
      ]);
      setDocuments(docs);
      setEmbeddingStatus(status);
      setPoints(viz);
    } catch {
      /* ignore on mount */
    }
  }

  function hasEmbeddings(docId: string): boolean {
    return embeddingStatus.some((s) => s.document_id === docId);
  }

  function getChunkCount(docId: string): number {
    return embeddingStatus.find((s) => s.document_id === docId)?.chunk_count ?? 0;
  }

  function toggleSelect(docId: string) {
    setSelectedForEmbed((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) next.delete(docId);
      else next.add(docId);
      return next;
    });
  }

  async function handleGenerateSelected() {
    const toEmbed = documents.filter(
      (d) => selectedForEmbed.has(d.id) && !hasEmbeddings(d.id)
    );
    if (!toEmbed.length) return;
    setError(null);
    setSelectedForEmbed(new Set());

    for (let i = 0; i < toEmbed.length; i++) {
      const doc = toEmbed[i];
      setEmbedProgress({ current: i + 1, total: toEmbed.length, currentName: doc.name });
      try {
        await api.generateEmbeddings(doc.id);
        const [status, viz] = await Promise.all([
          api.getEmbeddingStatus(),
          api.getVisualization(),
        ]);
        setEmbeddingStatus(status);
        setPoints(viz);
      } catch (e: unknown) {
        setError(
          `Błąd przy "${doc.name}": ${e instanceof Error ? e.message : "unknown error"}`
        );
      }
    }
    setEmbedProgress(null);
  }

  async function handleDelete(docId: string) {
    setError(null);
    try {
      await api.deleteEmbeddingsByDocument(docId);
      const [status, viz] = await Promise.all([
        api.getEmbeddingStatus(),
        api.getVisualization(),
      ]);
      setEmbeddingStatus(status);
      setPoints(viz);
      if (selectedA && points.find((p) => p.document_id === docId && p.chunk_id === selectedA)) {
        setSelectedA(null);
        setSelectedB(null);
        setSimilarity(null);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
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
      } catch {
        setSimilarity(null);
      }
    } else {
      setSelectedA(chunkId);
      setSelectedB(null);
      setSimilarity(null);
    }
  }

  const selectedCount = [...selectedForEmbed].filter((id) => !hasEmbeddings(id)).length;

  return (
    <div className="p-6 space-y-4">
      {/* Document source list */}
      <div className="border rounded-lg bg-white overflow-hidden">
        <div className="px-4 py-3 border-b flex items-center justify-between gap-4">
          <h2 className="font-semibold text-sm shrink-0">Źródła embeddingów</h2>
          <div className="flex items-center gap-3 min-w-0">
            {embedProgress && (
              <span className="text-xs text-muted-foreground truncate">
                Embeduję {embedProgress.current}/{embedProgress.total}: {embedProgress.currentName}…
              </span>
            )}
            <button
              onClick={handleGenerateSelected}
              disabled={selectedCount === 0 || !!embedProgress}
              className="shrink-0 px-3 py-1.5 bg-primary text-white text-sm rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              Generate Selected ({selectedCount})
            </button>
          </div>
        </div>

        {error && (
          <div className="px-4 py-2 text-xs text-red-500 bg-red-50 border-b">{error}</div>
        )}

        {documents.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            Brak dokumentów. Wgraj pliki w zakładce Documents.
          </p>
        ) : (
          <table className="w-full text-xs">
            <tbody>
              {documents.map((doc) => {
                const embedded = hasEmbeddings(doc.id);
                const count = getChunkCount(doc.id);
                const checked = selectedForEmbed.has(doc.id);
                return (
                  <tr key={doc.id} className="border-t border-border hover:bg-muted/30 transition-colors">
                    <td className="pl-4 pr-2 py-2.5 w-8">
                      {!embedded && (
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleSelect(doc.id)}
                          disabled={!!embedProgress}
                          className="rounded accent-primary"
                        />
                      )}
                    </td>
                    <td className="px-2 py-2.5 font-medium max-w-xs truncate" title={doc.name}>
                      {doc.name}
                    </td>
                    <td className="px-4 py-2.5 w-44">
                      {embedded ? (
                        <span className="inline-flex items-center gap-1 text-emerald-600 font-medium">
                          <span>✓</span>
                          <span>{count} chunków</span>
                        </span>
                      ) : (
                        <span className="text-muted-foreground">— brak embeddingów</span>
                      )}
                    </td>
                    <td className="px-4 py-2.5 w-16 text-right">
                      {embedded && (
                        <button
                          onClick={() => handleDelete(doc.id)}
                          disabled={!!embedProgress}
                          className="text-red-400 hover:text-red-600 disabled:opacity-40 transition-colors"
                          title="Usuń embeddingi dla tego dokumentu"
                        >
                          Usuń
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Similarity comparison */}
      {selectedA && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">
            {selectedB
              ? "Podobieństwo między zaznaczonymi chunkami:"
              : `Zaznaczono: ${selectedA.slice(0, 8)}… — kliknij drugi punkt aby porównać`}
          </span>
          {similarity != null && (
            <span className="font-semibold text-primary">cosine = {similarity.toFixed(4)}</span>
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
        Wizualizacja używa PCA (rzut 2D). Kliknij punkt aby go zaznaczyć, kliknij drugi aby porównać podobieństwo cosinusowe.
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles without errors**

```
cd frontend
npm run build 2>&1 | head -30
```

Expected: no TypeScript errors related to `EmbeddingExplorer.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/embeddings/EmbeddingExplorer.tsx
git commit -m "feat: redesign EmbeddingExplorer with status badges, multi-select, delete"
```

---

## Task 6: Add "Źródła:" label to ScatterPlot legend

**Files:**
- Modify: `frontend/src/components/embeddings/ScatterPlot.tsx`

- [ ] **Step 1: Update the legend section in `ScatterPlot.tsx`**

Replace lines 77–84 (the `<div className="flex gap-4 mt-2 flex-wrap">` block):

```typescript
      <div className="mt-3">
        <p className="text-xs text-muted-foreground font-medium mb-1.5">Źródła:</p>
        <div className="flex gap-4 flex-wrap">
          {docIds.map((id, i) => (
            <div key={id} className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
              <span className="text-xs text-muted-foreground truncate max-w-[200px]" title={docNames[id]}>
                {docNames[id]}
              </span>
            </div>
          ))}
        </div>
      </div>
```

- [ ] **Step 2: Verify TypeScript compiles**

```
cd frontend
npm run build 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/embeddings/ScatterPlot.tsx
git commit -m "fix: add Zrodla label to scatter plot legend"
```

---

## Task 7: Manual smoke test

**No code changes** — verify the full flow works end-to-end.

- [ ] **Step 1: Start backend**

```powershell
cd .worktrees\feature\scaffolding\backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

- [ ] **Step 2: Start frontend**

```powershell
cd .worktrees\feature\scaffolding\frontend
npm run dev
```

- [ ] **Step 3: Test bug #5 fix (Clear All)**

1. Open http://localhost:5173 → Embeddings
2. Upload a document, generate chunks, generate embeddings — confirm points appear in scatter plot
3. Go to Metrics → Clear All Data → confirm page reloads
4. Go back to Embeddings — confirm scatter plot is empty and status badges all show "— brak embeddingów"

- [ ] **Step 4: Test feature #7 (multi-generate, status, delete)**

1. Upload 2 documents, generate chunks for both
2. Go to Embeddings — both docs show "— brak embeddingów", checkboxes visible
3. Check both → "Generate Selected (2)" button activates
4. Click → watch inline progress "Embeduję 1/2: …", then "Embeduję 2/2: …"
5. After completion: both docs show "✓ N chunków", checkboxes gone, "Usuń" buttons visible
6. Click "Usuń" on one doc → it reverts to "— brak embeddingów", scatter plot updates

- [ ] **Step 5: Test bug #6 fix (legend)**

1. With 2 documents embedded, check scatter plot legend under "Źródła:"
2. Confirm both document file names appear (not truncated IDs)

- [ ] **Step 6: Commit final smoke test note (optional)**

```bash
git commit --allow-empty -m "chore: manual smoke test passed for embeddings improvements"
```
