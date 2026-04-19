# Chunking Lab UX Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the broken `<select>` with a full-width overlay document picker, add cascade delete with confirmation, fix orphaned parent store entries, and add tooltips to strategy buttons.

**Architecture:** DocPicker is a new component that renders a trigger button in place of the old `<select>`, and a React portal overlay spanning the full viewport width when open. DeleteConfirmModal is a separate portal component. ChunkingLab wires them together and manages cascade delete. StrategySelector gets per-button tooltips using CSS group-hover. Backend gets a new DELETE endpoint for chunks and a fix for orphaned _parent_store entries.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, FastAPI/Python 3.9, lucide-react icons, React createPortal

---

## File Map

| File | Action |
|---|---|
| `backend/api/chunks.py` | Add DELETE endpoint + fix orphaned _parent_store |
| `frontend/src/api/client.ts` | Add `deleteChunks` method |
| `frontend/src/components/chunks/DocPicker.tsx` | New — trigger + portal overlay + DocTile |
| `frontend/src/components/chunks/DeleteConfirmModal.tsx` | New — portal confirmation modal |
| `frontend/src/components/chunks/ChunkingLab.tsx` | Replace select, integrate DocPicker, cascade delete, chunk counts |
| `frontend/src/components/chunks/StrategySelector.tsx` | Add tooltips |

> **SYNC CONVENTION:** This project has two copies of every file:
> - **Worktree** (running dev server): `.worktrees/feature/scaffolding/backend/` and `.worktrees/feature/scaffolding/frontend/`
> - **Tracked copy** (committed to git): `backend/` and `frontend/`
>
> Every task that modifies a file ends with a sync step:
> ```bash
> cp .worktrees/feature/scaffolding/backend/api/chunks.py backend/api/chunks.py
> # or for frontend:
> cp .worktrees/feature/scaffolding/frontend/src/components/chunks/DocPicker.tsx frontend/src/components/chunks/DocPicker.tsx
> ```
> Always edit the **worktree** first (live reload), then sync to tracked copy before committing.

---

### Task 1: Backend — DELETE /api/chunks/{doc_id} + fix orphaned _parent_store

**Files:**
- Modify: `.worktrees/feature/scaffolding/backend/api/chunks.py`
- Sync: `backend/api/chunks.py`

- [ ] **Step 1: Open the file and locate `generate_chunks` function (line ~86)**

File: `.worktrees/feature/scaffolding/backend/api/chunks.py`

- [ ] **Step 2: Add orphan cleanup at the top of `generate_chunks`, before `_build_chunk_response` is called**

Find this block (around line 99):
```python
    response = _build_chunk_response(raw, req.document_id, overlap=req.overlap, chunk_size=req.chunk_size)
    _chunks_store[req.document_id] = response
```

Insert BEFORE `response = _build_chunk_response(...)`:
```python
    # Clear orphaned parent store entries from previous generation
    if req.document_id in _chunks_store:
        old_ids = {c.id for c in _chunks_store[req.document_id].chunks}
        for old_id in old_ids:
            _parent_store.pop(old_id, None)
```

- [ ] **Step 3: Add the DELETE endpoint at the end of the router section (after `get_chunks`, before `get_chunks_for_document`)**

Add after line ~114 (`return _chunks_store[document_id]`):

```python
@router.delete("/{document_id}")
def delete_chunks(document_id: str):
    if document_id not in _chunks_store:
        return {"deleted": document_id, "count": 0}
    chunk_ids = {c.id for c in _chunks_store[document_id].chunks}
    for cid in chunk_ids:
        _parent_store.pop(cid, None)
    del _chunks_store[document_id]
    _persist()
    return {"deleted": document_id, "count": len(chunk_ids)}
```

- [ ] **Step 4: Verify the final state of chunks.py**

The file should now have, in order:
1. `generate_chunks` with orphan cleanup at the top (before `_build_chunk_response`)
2. `get_chunks` returning from `_chunks_store`
3. `delete_chunks` (new endpoint)
4. `get_chunks_for_document` helper
5. `get_parent_content` helper

- [ ] **Step 5: Verify backend restarts cleanly**

The uvicorn server (`--reload`) should auto-restart. Check terminal — no import errors.

Test the endpoint exists:
```bash
curl -s -X DELETE http://localhost:8000/api/chunks/nonexistent-id
```
Expected: `{"deleted":"nonexistent-id","count":0}`

- [ ] **Step 6: Sync to tracked copy and commit**

```bash
cp .worktrees/feature/scaffolding/backend/api/chunks.py backend/api/chunks.py
git add backend/api/chunks.py
git commit -m "feat: add DELETE /api/chunks/{doc_id} + fix orphaned _parent_store on re-generate"
```

---

### Task 2: Frontend API client — add deleteChunks

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/api/client.ts`
- Sync: `frontend/src/api/client.ts`

- [ ] **Step 1: Add `deleteChunks` to the `api` object**

In `.worktrees/feature/scaffolding/frontend/src/api/client.ts`, find the Chunks section:
```typescript
  // Chunks
  generateChunks: ...
  getChunks: ...
```

Add after `getChunks`:
```typescript
  deleteChunks: (documentId: string) =>
    request<{ deleted: string; count: number }>(`/chunks/${documentId}`, { method: "DELETE" }),
```

- [ ] **Step 2: Sync and commit**

```bash
cp .worktrees/feature/scaffolding/frontend/src/api/client.ts frontend/src/api/client.ts
git add frontend/src/api/client.ts
git commit -m "feat: add api.deleteChunks client method"
```

---

### Task 3: DocPicker component

**Files:**
- Create: `.worktrees/feature/scaffolding/frontend/src/components/chunks/DocPicker.tsx`
- Sync: `frontend/src/components/chunks/DocPicker.tsx`

- [ ] **Step 1: Create the file with the full component**

`.worktrees/feature/scaffolding/frontend/src/components/chunks/DocPicker.tsx`:

```tsx
import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, ChevronUp, Search } from "lucide-react";
import type { DocumentMeta, EmbeddingStatus } from "../../types";

interface DocPickerProps {
  documents: DocumentMeta[];
  chunkCounts: Record<string, number>;
  embeddingStatus: EmbeddingStatus[];
  selectedDocId: string;
  onSelect: (docId: string) => void;
  onDelete: (doc: DocumentMeta) => void;
}

export function DocPicker({
  documents,
  chunkCounts,
  embeddingStatus,
  selectedDocId,
  onSelect,
  onDelete,
}: DocPickerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [overlayTop, setOverlayTop] = useState(0);
  const [overlayLeft, setOverlayLeft] = useState(0);

  const embeddedDocIds = new Set(embeddingStatus.map((s) => s.document_id));
  const selectedDoc = documents.find((d) => d.id === selectedDocId);
  const selectedChunkCount =
    selectedDocId !== "" ? chunkCounts[selectedDocId] : undefined;

  const filtered = documents.filter((d) =>
    d.name.toLowerCase().includes(search.toLowerCase())
  );

  function open() {
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setOverlayTop(rect.bottom + 4);
      setOverlayLeft(rect.left);
    }
    setIsOpen(true);
  }

  function close() {
    setIsOpen(false);
    setSearch("");
  }

  useEffect(() => {
    if (isOpen && searchRef.current) {
      searchRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen]);

  return (
    <div className="relative mt-1">
      <button
        ref={triggerRef}
        onClick={() => (isOpen ? close() : open())}
        className="w-full flex items-center gap-2 px-2.5 py-1.5 text-xs bg-muted border border-border rounded-md hover:border-primary/50 transition-colors text-left"
      >
        <span className="flex-1 truncate text-foreground">
          {selectedDoc ? selectedDoc.name : "Wybierz dokument"}
        </span>
        {selectedChunkCount !== undefined && (
          <span className="text-muted-foreground text-[10px] shrink-0">
            {selectedChunkCount} ch
          </span>
        )}
        {isOpen ? (
          <ChevronUp className="w-3 h-3 text-muted-foreground shrink-0" />
        ) : (
          <ChevronDown className="w-3 h-3 text-muted-foreground shrink-0" />
        )}
      </button>

      {isOpen &&
        createPortal(
          <>
            {/* Invisible backdrop */}
            <div className="fixed inset-0 z-40" onClick={close} />

            {/* Overlay panel */}
            <div
              className="fixed z-50 bg-card border border-border rounded-lg shadow-2xl overflow-hidden"
              style={{ top: overlayTop, left: overlayLeft, right: 16 }}
            >
              {/* Search header */}
              <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
                <Search className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                <input
                  ref={searchRef}
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Szukaj dokumentu…"
                  className="flex-1 text-xs bg-transparent outline-none text-foreground placeholder:text-muted-foreground"
                />
                <span className="text-[10px] text-muted-foreground shrink-0">
                  {filtered.length} doc{filtered.length !== 1 ? "s" : ""}
                </span>
              </div>

              {/* Document grid */}
              <div
                className="p-3 grid gap-2 overflow-y-auto max-h-72"
                style={{
                  gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
                }}
              >
                {filtered.length === 0 && (
                  <p className="col-span-full text-xs text-muted-foreground text-center py-4">
                    Brak dokumentów pasujących do „{search}"
                  </p>
                )}
                {filtered.map((doc) => (
                  <DocTile
                    key={doc.id}
                    doc={doc}
                    chunkCount={chunkCounts[doc.id] ?? null}
                    hasEmbeddings={embeddedDocIds.has(doc.id)}
                    isActive={doc.id === selectedDocId}
                    onSelect={() => {
                      onSelect(doc.id);
                      close();
                    }}
                    onDelete={() => {
                      onDelete(doc);
                      close();
                    }}
                  />
                ))}
              </div>
            </div>
          </>,
          document.body
        )}
    </div>
  );
}

interface DocTileProps {
  doc: DocumentMeta;
  chunkCount: number | null;
  hasEmbeddings: boolean;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

function DocTile({
  doc,
  chunkCount,
  hasEmbeddings,
  isActive,
  onSelect,
  onDelete,
}: DocTileProps) {
  return (
    <div
      onClick={onSelect}
      className={`group relative cursor-pointer rounded-md border px-2.5 py-2 transition-colors ${
        isActive
          ? "border-primary bg-primary/10"
          : "border-border bg-muted hover:border-primary/40"
      }`}
    >
      <p
        className={`text-[11px] font-medium truncate pr-4 ${
          isActive ? "text-primary" : "text-foreground"
        }`}
      >
        {doc.name}
      </p>
      <p className="text-[10px] text-muted-foreground mt-0.5">
        {chunkCount !== null ? `${chunkCount} ch` : "—"}
        {hasEmbeddings && (
          <span className="text-success/70 ml-1">· emb</span>
        )}
      </p>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="absolute top-1 right-1.5 text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-error transition-opacity leading-none"
        title="Usuń dokument"
      >
        ✕
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Verify it compiles — open browser at http://localhost:5173 and check the console for TypeScript errors**

No errors expected at this point (component isn't used yet).

- [ ] **Step 3: Sync and commit**

```bash
cp .worktrees/feature/scaffolding/frontend/src/components/chunks/DocPicker.tsx frontend/src/components/chunks/DocPicker.tsx
git add frontend/src/components/chunks/DocPicker.tsx
git commit -m "feat: add DocPicker component with full-width overlay and tile grid"
```

---

### Task 4: DeleteConfirmModal component

**Files:**
- Create: `.worktrees/feature/scaffolding/frontend/src/components/chunks/DeleteConfirmModal.tsx`
- Sync: `frontend/src/components/chunks/DeleteConfirmModal.tsx`

- [ ] **Step 1: Create the file**

`.worktrees/feature/scaffolding/frontend/src/components/chunks/DeleteConfirmModal.tsx`:

```tsx
import { useEffect } from "react";
import { createPortal } from "react-dom";
import type { DocumentMeta } from "../../types";

interface DeleteConfirmModalProps {
  doc: DocumentMeta;
  chunkCount: number | null;
  isLoading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function DeleteConfirmModal({
  doc,
  chunkCount,
  isLoading,
  onConfirm,
  onCancel,
}: DeleteConfirmModalProps) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !isLoading) onCancel();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel, isLoading]);

  const chunksText =
    chunkCount !== null && chunkCount > 0 ? `, ${chunkCount} chunków` : "";

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-card border border-border rounded-lg p-5 w-80 shadow-2xl">
        <h3 className="text-sm font-semibold mb-2">Usuń dokument</h3>
        <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
          Czy na pewno chcesz usunąć{" "}
          <span className="text-foreground font-medium">„{doc.name}"</span>?
          Zostanie usunięty dokument{chunksText} i embeddingi.
        </p>
        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted transition-colors disabled:opacity-50"
          >
            Anuluj
          </button>
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs bg-error text-white rounded-md hover:bg-error/90 transition-colors disabled:opacity-50"
          >
            {isLoading ? "Usuwam…" : "Usuń"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
```

- [ ] **Step 2: Verify no TypeScript errors in browser console**

- [ ] **Step 3: Sync and commit**

```bash
cp .worktrees/feature/scaffolding/frontend/src/components/chunks/DeleteConfirmModal.tsx frontend/src/components/chunks/DeleteConfirmModal.tsx
git add frontend/src/components/chunks/DeleteConfirmModal.tsx
git commit -m "feat: add DeleteConfirmModal portal component"
```

---

### Task 5: ChunkingLab — integrate DocPicker, cascade delete, chunk counts

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/chunks/ChunkingLab.tsx`
- Sync: `frontend/src/components/chunks/ChunkingLab.tsx`

- [ ] **Step 1: Replace the entire file content**

`.worktrees/feature/scaffolding/frontend/src/components/chunks/ChunkingLab.tsx`:

```tsx
import { useState, useEffect, useCallback } from "react";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import type { DocumentMeta, ChunkRequest, ChunkResponse, EmbeddingStatus } from "../../types";
import { api } from "../../api/client";
import { StrategySelector } from "./StrategySelector";
import { ChunkViewer } from "./ChunkViewer";
import { DocPicker } from "./DocPicker";
import { DeleteConfirmModal } from "./DeleteConfirmModal";

interface BulkResult {
  docId: string;
  name: string;
  status: "ok" | "error";
  chunkCount?: number;
  error?: string;
}

export function ChunkingLab() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [chunkReq, setChunkReq] = useState<ChunkRequest>({
    document_id: "",
    strategy: "fixed",
    chunk_size: 1000,
    overlap: 100,
  });
  const [response, setResponse] = useState<ChunkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Document picker state
  const [chunkCounts, setChunkCounts] = useState<Record<string, number>>({});
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus[]>([]);

  // Delete state
  const [docToDelete, setDocToDelete] = useState<DocumentMeta | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Bulk state
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkProgress, setBulkProgress] = useState<{ current: number; total: number } | null>(null);
  const [bulkResults, setBulkResults] = useState<BulkResult[]>([]);

  useEffect(() => {
    async function load() {
      const docs = await api.listDocuments();
      setDocuments(docs);
      if (docs.length > 0) {
        setSelectedDocId(docs[0].id);
        setChunkReq((prev) => ({ ...prev, document_id: docs[0].id }));
      }

      // Chunk counts for all docs in parallel
      const settled = await Promise.allSettled(docs.map((d) => api.getChunks(d.id)));
      const counts: Record<string, number> = {};
      settled.forEach((r, i) => {
        if (r.status === "fulfilled") counts[docs[i].id] = r.value.chunks.length;
      });
      setChunkCounts(counts);

      // Embedding status
      const status = await api.getEmbeddingStatus();
      setEmbeddingStatus(status);
    }
    load().catch(console.error);
  }, []);

  // Load chunks for selected doc when selection changes
  useEffect(() => {
    if (!selectedDocId) {
      setResponse(null);
      return;
    }
    api.getChunks(selectedDocId)
      .then(setResponse)
      .catch(() => setResponse(null));
  }, [selectedDocId]);

  async function generate() {
    if (!selectedDocId) return;
    setLoading(true);
    setError(null);
    try {
      const req = { ...chunkReq, document_id: selectedDocId };
      const res = await api.generateChunks(req);
      setResponse(res);
      setChunkCounts((prev) => ({ ...prev, [selectedDocId]: res.chunks.length }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  }

  async function generateAll() {
    if (documents.length === 0) return;
    setBulkRunning(true);
    setBulkResults([]);
    setBulkProgress({ current: 0, total: documents.length });

    const results: BulkResult[] = [];
    for (let i = 0; i < documents.length; i++) {
      const doc = documents[i];
      setBulkProgress({ current: i + 1, total: documents.length });
      try {
        const res = await api.generateChunks({ ...chunkReq, document_id: doc.id });
        results.push({ docId: doc.id, name: doc.name, status: "ok", chunkCount: res.chunks.length });
        setResponse(res);
        setSelectedDocId(doc.id);
        setChunkCounts((prev) => ({ ...prev, [doc.id]: res.chunks.length }));
      } catch (e: unknown) {
        results.push({
          docId: doc.id,
          name: doc.name,
          status: "error",
          error: e instanceof Error ? e.message : "Failed",
        });
      }
      setBulkResults([...results]);
    }
    setBulkRunning(false);
  }

  const handleDeleteRequest = useCallback((doc: DocumentMeta) => {
    setDocToDelete(doc);
  }, []);

  async function handleDeleteConfirm() {
    if (!docToDelete) return;
    setDeleteLoading(true);
    const id = docToDelete.id;
    try {
      await api.deleteChunks(id);
      await api.deleteEmbeddingsByDocument(id);
      await api.deleteDocument(id);

      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setChunkCounts((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      setEmbeddingStatus((prev) => prev.filter((s) => s.document_id !== id));

      if (selectedDocId === id) {
        setSelectedDocId("");
        setResponse(null);
        setChunkReq((prev) => ({ ...prev, document_id: "" }));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleteLoading(false);
      setDocToDelete(null);
    }
  }

  const bulkOk = bulkResults.filter((r) => r.status === "ok").length;
  const bulkErr = bulkResults.filter((r) => r.status === "error").length;

  return (
    <div className="p-6 h-full flex gap-6">
      <div className="w-72 shrink-0 space-y-4">
        <h2 className="font-semibold text-sm">Chunking Lab</h2>

        <div>
          <label className="text-xs font-medium text-muted-foreground">Document</label>
          <DocPicker
            documents={documents}
            chunkCounts={chunkCounts}
            embeddingStatus={embeddingStatus}
            selectedDocId={selectedDocId}
            onSelect={(docId) => {
              setSelectedDocId(docId);
              setChunkReq((prev) => ({ ...prev, document_id: docId }));
            }}
            onDelete={handleDeleteRequest}
          />
        </div>

        <StrategySelector
          value={chunkReq}
          onChange={setChunkReq}
          documentId={selectedDocId}
        />

        <button
          onClick={generate}
          disabled={loading || bulkRunning || !selectedDocId}
          className="w-full py-2 bg-primary text-primary-foreground text-sm rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? "Generating..." : "Generate Chunks"}
        </button>

        <button
          onClick={generateAll}
          disabled={loading || bulkRunning || documents.length === 0}
          className="w-full py-2 border border-primary text-primary text-sm rounded-md hover:bg-primary/5 disabled:opacity-50 transition-colors"
        >
          {bulkRunning
            ? `Przetwarzam ${bulkProgress?.current}/${bulkProgress?.total}…`
            : `Generate All (${documents.length})`}
        </button>

        {error && <p className="text-xs text-error">{error}</p>}

        {bulkProgress && (
          <div className="space-y-1.5">
            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300 rounded-full"
                style={{
                  width: `${Math.round(
                    (bulkProgress.current / bulkProgress.total) * 100
                  )}%`,
                }}
              />
            </div>
            <div className="flex gap-3 text-xs">
              {bulkOk > 0 && (
                <span className="text-success flex items-center gap-1">
                  <CheckCircle className="w-3 h-3" />{bulkOk} ok
                </span>
              )}
              {bulkErr > 0 && (
                <span className="text-error flex items-center gap-1">
                  <XCircle className="w-3 h-3" />{bulkErr} błędy
                </span>
              )}
              {bulkRunning && (
                <span className="text-muted-foreground flex items-center gap-1">
                  <Loader2 className="w-3 h-3 animate-spin" />w toku
                </span>
              )}
            </div>
          </div>
        )}

        {bulkResults.length > 0 && (
          <div className="border border-border rounded-md divide-y divide-border max-h-48 overflow-y-auto bg-card">
            {bulkResults.map((r) => (
              <div key={r.docId} className="flex items-start gap-2 px-2.5 py-1.5">
                {r.status === "ok" ? (
                  <CheckCircle className="w-3 h-3 text-success mt-0.5 shrink-0" />
                ) : (
                  <XCircle className="w-3 h-3 text-error mt-0.5 shrink-0" />
                )}
                <div className="min-w-0">
                  <p className="text-xs truncate">{r.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {r.status === "ok" ? `${r.chunkCount} chunków` : r.error}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-auto">
        <ChunkViewer
          chunks={response?.chunks ?? []}
          stats={response?.stats ?? null}
        />
      </div>

      {docToDelete && (
        <DeleteConfirmModal
          doc={docToDelete}
          chunkCount={chunkCounts[docToDelete.id] ?? null}
          isLoading={deleteLoading}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDocToDelete(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Open http://localhost:5173 → Chunking Lab and verify:**
  - Trigger button appears where select was, shows first doc name
  - Clicking trigger opens overlay with document tiles
  - Tiles show name + chunk count (or "—") + "· emb" badge if embedded
  - Search field filters tiles as you type
  - Clicking a tile selects it + closes overlay + loads chunks in viewer
  - Escape closes overlay without changing selection
  - Clicking outside overlay closes it
  - ✕ button appears on tile hover
  - Clicking ✕ closes overlay and shows confirmation modal
  - "Anuluj" closes modal without action
  - "Usuń" runs cascade delete: document disappears from list, chunk viewer clears if it was selected

- [ ] **Step 3: Sync and commit**

```bash
cp .worktrees/feature/scaffolding/frontend/src/components/chunks/ChunkingLab.tsx frontend/src/components/chunks/ChunkingLab.tsx
git add frontend/src/components/chunks/ChunkingLab.tsx
git commit -m "feat: integrate DocPicker and cascade delete into ChunkingLab"
```

---

### Task 6: StrategySelector — tooltips

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/chunks/StrategySelector.tsx`
- Sync: `frontend/src/components/chunks/StrategySelector.tsx`

- [ ] **Step 1: Replace the entire file content**

`.worktrees/feature/scaffolding/frontend/src/components/chunks/StrategySelector.tsx`:

```tsx
import type { ChunkRequest } from "../../types";

interface StrategySelectorProps {
  value: ChunkRequest;
  onChange: (v: ChunkRequest) => void;
  documentId: string;
}

const STRATEGY_INFO = {
  fixed: {
    label: "Fixed Size",
    description: "Dzieli tekst na równe fragmenty o zadanej liczbie znaków z zachowaniem overlap.",
    when: "Dobra dla dokumentów o równomiernej gęstości informacji: raporty, artykuły, transkrypcje.",
  },
  recursive: {
    label: "Recursive",
    description: "Próbuje dzielić po naturalnych granicach: akapity → zdania → słowa.",
    when: "Dobra dla dokumentów z wyraźną strukturą: dokumentacja, tutoriale, README.",
  },
  semantic: {
    label: "Semantic",
    description: "Grupuje zdania o zbliżonej tematyce w jeden chunk. Najwolniejsza, najlepsza jakość semantyczna.",
    when: "Dobra gdy treść jest zróżnicowana i zależy Ci na spójności znaczeniowej chunków.",
  },
} as const;

export function StrategySelector({ value, onChange, documentId }: StrategySelectorProps) {
  const strategies = (["fixed", "recursive", "semantic"] as const);

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Strategy
        </label>
        <div className="flex gap-2 mt-1.5">
          {strategies.map((id) => {
            const info = STRATEGY_INFO[id];
            return (
              <div key={id} className="relative group">
                <button
                  onClick={() => onChange({ ...value, strategy: id, document_id: documentId })}
                  className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                    value.strategy === id
                      ? "border-primary bg-primary text-white"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  {info.label}
                </button>

                {/* Tooltip */}
                <div className="absolute bottom-full left-0 mb-2 z-50 w-52 p-2.5 bg-card border border-border rounded-lg shadow-xl invisible group-hover:visible pointer-events-none">
                  <p className="text-[11px] font-semibold text-foreground mb-1">
                    {info.label}
                  </p>
                  <p className="text-[11px] text-muted-foreground leading-relaxed mb-1.5">
                    {info.description}
                  </p>
                  <p className="text-[11px] text-primary/80 leading-relaxed">
                    {info.when}
                  </p>
                </div>
              </div>
            );
          })}
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
              value={value.chunk_size ?? 500}
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
              value={value.overlap ?? 50}
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

- [ ] **Step 2: Open http://localhost:5173 → Chunking Lab and verify:**
  - Hover over each of the three strategy buttons
  - Tooltip appears above the button with: bold title, description in muted color, "when to use" in primary color
  - Tooltip disappears when cursor leaves
  - Strategy selection still works (click changes active button)
  - Chunk Size and Overlap sliders still appear for Fixed and Recursive

- [ ] **Step 3: Sync and commit**

```bash
cp .worktrees/feature/scaffolding/frontend/src/components/chunks/StrategySelector.tsx frontend/src/components/chunks/StrategySelector.tsx
git add frontend/src/components/chunks/StrategySelector.tsx
git commit -m "feat: add hover tooltips to strategy selector buttons"
```
