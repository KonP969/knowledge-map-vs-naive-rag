# Chunking Lab UX Improvements

**Date:** 2026-04-19
**Feature:** Document picker overlay, cascade delete, chunk regeneration fix, strategy tooltips

## Problem

1. `<select>` dropdown for document selection is unusable with 20+ documents.
2. No way to delete a document from Chunking Lab — and no cascade to chunks/embeddings.
3. Re-generating chunks leaves orphaned `_parent_store` entries from previous chunk IDs.
4. Strategy buttons (Fixed / Recursive / Semantic) have no explanation — users don't know when to pick which.

## Goals

- Replace `<select>` with a searchable full-width overlay grid picker
- Add cascade delete (document + chunks + embeddings) with confirmation modal
- Fix orphaned `_parent_store` entries on re-generate
- Add tooltips to strategy buttons: short description + when to use

## Decisions

- **Overlay scope:** Spans the entire Chunking Lab width (sidebar + viewer), not just the sidebar column
- **Overlay columns:** CSS `grid-template-columns: repeat(auto-fill, minmax(130px, 1fr))` — fills width automatically
- **Delete order:** chunks first → embeddings → document (avoids orphans)
- **Tooltip trigger:** `title` attribute is not sufficient — use a small absolute-positioned tooltip div on hover
- **No new backend endpoint for chunks delete** — add `DELETE /api/chunks/{document_id}` (missing from current API)
- **Re-generate fix:** In `generate_chunks`, clear old `_parent_store` entries for all previous chunk IDs before building new parent map

## Architecture

```
ChunkingLab
  — replaces <select> with <DocPicker>
  — adds deleteDocument(id) handler (3-step cascade + modal)
  — layout unchanged otherwise

<DocPicker>                         (new component)
  — trigger button: selected doc name + chunk count + chevron
  — isOpen state
  — full-width overlay (position: absolute, left:0 right:0, z-50)
    — search input (filters by doc name)
    — doc grid: <DocTile> per document
    — click outside / Escape → close
  — on tile click: calls onSelect(docId), closes

<DocTile>                           (new component, inside DocPicker)
  — shows: name (truncated), chunk count or "—", embedding badge
  — active state (selected doc)
  — ✕ button on hover → calls onDelete(docId)

<DeleteConfirmModal>                (new component)
  — props: { doc: DocumentMeta; chunkCount: number; onConfirm; onCancel }
  — React portal → document.body
  — message: "Usuń [name]? Zostanie usunięty dokument, [N] chunków i embeddingi."
  — two buttons: Anuluj / Usuń

<StrategySelector>                  (modified)
  — each strategy button gets a <StrategyTooltip> on hover
  — tooltip: description + "Używaj gdy:" hint
```

## Data Flow

```
User clicks trigger button
  → isOpen = true
  → overlay renders with current documents + embedding status

User types in search
  → filters doc list by name (case-insensitive substring)

User clicks DocTile
  → onSelect(docId) called in ChunkingLab
  → isOpen = false
  → ChunkingLab loads chunks for new doc

User clicks ✕ on DocTile
  → ChunkingLab shows <DeleteConfirmModal>
  → on confirm:
      1. DELETE /api/chunks/{docId}        ← new backend endpoint
      2. DELETE /api/embeddings/by-document/{docId}
      3. DELETE /api/documents/{docId}
  → remove doc from local state
  → if deleted doc was selected: clear selectedDocId

Re-generate chunks (existing flow)
  → backend: clear _parent_store entries for old chunk IDs first
  → then build new parent map and update
```

## Components

### `DocPicker`

```
Props: {
  documents: DocumentMeta[];
  embeddingStatus: EmbeddingStatus[];
  selectedDocId: string;
  onSelect: (docId: string) => void;
  onDelete: (docId: string) => void;
}

State: isOpen, searchQuery

Render:
  - trigger button: selected doc name (truncated) · chunk count · chevron ▾/▴
  - when isOpen:
    - invisible full-screen backdrop (z-40, onClick → close)
    - overlay div: position absolute, left:0 right:0 top:[trigger height], z-50
      - search input (autoFocus)
      - doc grid: auto-fill columns, minmax(130px, 1fr)
      - filtered docs mapped to <DocTile>
  - Escape listener via useEffect (cleanup on unmount)
```

### `DocTile`

```
Props: {
  doc: DocumentMeta;
  chunkCount: number | null;    // null = no chunks yet
  hasEmbeddings: boolean;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

Render:
  - tile: bg-card border border-border rounded, cursor-pointer
  - active: border-primary bg-primary/8
  - name: text-xs font-semibold truncate, pr-4 (room for ✕)
  - meta line: chunkCount !== null ? `${chunkCount} ch` : "—"
    + hasEmbeddings ? " · emb" (text-success/60) : ""
  - ✕ button: absolute top-1 right-1, opacity-0 group-hover:opacity-100
    onClick: e.stopPropagation() + onDelete()
```

### `DeleteConfirmModal`

```
Props: { doc: DocumentMeta; chunkCount: number | null; onConfirm: () => void; onCancel: () => void }

Render: React portal (document.body)
  - backdrop: fixed inset-0 bg-black/50 z-50
  - modal: fixed centered, bg-card border border-border rounded-lg p-5, w-80
  - title: "Usuń dokument"
  - body: "Czy na pewno chcesz usunąć „[name]"?
           Zostanie usunięty dokument[, [N] chunków][i embeddingi]."
  - buttons: Anuluj (outline) / Usuń (bg-error)
  - Escape closes (calls onCancel)
```

### `StrategySelector` — tooltip content

```
Fixed Size:
  Opis: "Dzieli tekst na równe fragmenty o zadanej liczbie znaków z zachowaniem overlap."
  Kiedy: "Dobra dla dokumentów o równomiernej gęstości informacji: raporty, artykuły, transkrypcje."

Recursive:
  Opis: "Próbuje dzielić po naturalnych granicach: akapity → zdania → słowa."
  Kiedy: "Dobra dla dokumentów z wyraźną strukturą: dokumentacja, tutoriale, README."

Semantic:
  Opis: "Grupuje zdania o zbliżonej tematyce w jeden chunk. Najwolniejsza, najlepsza jakość semantyczna."
  Kiedy: "Dobra gdy treść jest zróżnicowana i zależy Ci na spójności znaczeniowej chunków."

Tooltip render: small div, absolute, z-50, bg-card border border-border rounded p-2
  — appears on button hover (group/peer pattern or local state)
  — max-w-52, text-xs
```

## Backend Changes

### New endpoint: `DELETE /api/chunks/{document_id}`

```python
@router.delete("/{document_id}")
def delete_chunks(document_id: str):
    if document_id not in _chunks_store:
        return {"deleted": document_id, "count": 0}
    chunk_ids = {c.id for c in _chunks_store[document_id].chunks}
    # Remove parent store entries for these chunk IDs
    for cid in chunk_ids:
        _parent_store.pop(cid, None)
    del _chunks_store[document_id]
    _persist()
    return {"deleted": document_id, "count": len(chunk_ids)}
```

### Fix orphaned `_parent_store` on re-generate

In `generate_chunks`, before building new parent map:

```python
# Clear old parent entries for previous chunks of this document
if req.document_id in _chunks_store:
    old_ids = {c.id for c in _chunks_store[req.document_id].chunks}
    for old_id in old_ids:
        _parent_store.pop(old_id, None)
```

## Frontend API Client additions

```typescript
deleteChunks: (documentId: string) =>
  request<{ deleted: string; count: number }>(`/chunks/${documentId}`, { method: "DELETE" }),
```

## Error Handling

| Scenario | Behavior |
|---|---|
| Delete fails mid-cascade | Show error toast; document remains in list; partial state visible on reload |
| No chunks for deleted doc | Skip `deleteChunks` call (or backend returns `{count: 0}` safely) |
| Overlay open, doc deleted externally | On close, list refreshes from state (no stale tile) |
| Search returns no results | Show "Brak dokumentów pasujących do „query"" in grid area |
| Selected doc deleted | Clear selectedDocId, clear chunk viewer |

## Chunk counts for all documents

DocPicker needs chunk counts for all documents (not just the selected one) to show in tiles. Use the existing `GET /api/chunks/{document_id}` endpoint — on initial load, ChunkingLab fetches counts for all docs in parallel:

```typescript
// in ChunkingLab, after loading documents:
const counts = await Promise.allSettled(docs.map(d => api.getChunks(d.id)));
const chunkCounts: Record<string, number> = {};
counts.forEach((r, i) => {
  if (r.status === "fulfilled") chunkCounts[docs[i].id] = r.value.chunks.length;
});
```

After generate/delete, update `chunkCounts` in state locally (no full re-fetch needed).

## Files Changed

| File | Action |
|---|---|
| `frontend/src/components/chunks/DocPicker.tsx` | New — trigger button + overlay + DocTile |
| `frontend/src/components/chunks/DeleteConfirmModal.tsx` | New — portal modal |
| `frontend/src/components/chunks/ChunkingLab.tsx` | Replace `<select>` with `<DocPicker>`; add delete handler; fetch embedding status |
| `frontend/src/components/chunks/StrategySelector.tsx` | Add tooltip per strategy button |
| `frontend/src/api/client.ts` | Add `deleteChunks` method |
| `backend/api/chunks.py` | Add `DELETE /{document_id}` endpoint; fix orphaned `_parent_store` on re-generate |

## Out of Scope

- Bulk delete (select multiple + delete all)
- Drag-and-drop reordering
- Document rename
- Pagination / virtual scroll in overlay (auto-fill grid + scroll is sufficient)
