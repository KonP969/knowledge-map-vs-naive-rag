# UI Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ulepszyć UI sekcji Documents, Chunking Lab, Embeddings i Tutorial zgodnie ze specyfikacją z 2026-04-25.

**Architecture:** Czysty React/TypeScript frontend bez backendu testowego. Weryfikacja przez `npx tsc -p tsconfig.app.json` (już skonfigurowany z `noEmit: true`). Zmiany są niezależne między sekcjami — każde zadanie commituje działający kod.

**Tech Stack:** React 18, TypeScript (strict), Tailwind CSS, Vite, lucide-react, projektowe tokeny kolorów (`bg-card`, `border-border`, `text-muted-foreground`, etc.)

**Working directory:** `.worktrees/feature/scaffolding/frontend`

**TypeScript check command:** `npx tsc -p tsconfig.app.json`

---

## Mapa plików

| Plik | Akcja |
|------|-------|
| `src/components/shared/DeleteConfirmModal.tsx` | Nowy (wyekstrahowany z `chunks/`) |
| `src/components/chunks/ChunkingLab.tsx` | Modyfikacja — nowy layout z tabami, usunięcie DocPicker |
| `src/components/chunks/DeleteConfirmModal.tsx` | Import zastępiony przez shared/ |
| `src/components/documents/DocumentManager.tsx` | Modyfikacja — search, folder filter, cascade delete, folder modal |
| `src/components/documents/DocumentList.tsx` | Modyfikacja — `onDeleteRequest` zamiast `onDelete` |
| `src/components/documents/FolderAssignModal.tsx` | Nowy komponent |
| `src/components/embeddings/EmbeddingExplorer.tsx` | Modyfikacja — taby, karty zamiast tabeli |
| `src/components/tutorial/TutorialPanel.tsx` | Modyfikacja — zaktualizowane opisy |

---

## Task 1: Przenieś DeleteConfirmModal do shared/

**Files:**
- Create: `src/components/shared/DeleteConfirmModal.tsx`
- Modify: `src/components/chunks/ChunkingLab.tsx` (zmiana importu)

- [ ] **Krok 1: Utwórz `src/components/shared/DeleteConfirmModal.tsx`**

```tsx
import { useEffect, useRef } from "react";
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
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={!isLoading ? onCancel : undefined}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-modal-title"
        className="bg-card border border-border rounded-lg p-5 w-80 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="delete-modal-title" className="text-sm font-semibold mb-2">Usuń dokument</h3>
        <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
          Czy na pewno chcesz usunąć{" "}
          <span className="text-foreground font-medium">„{doc.name}"</span>?
          Zostanie usunięty dokument{chunksText} i embeddingi.
        </p>
        <div className="flex gap-2 justify-end">
          <button
            ref={cancelRef}
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted transition-colors disabled:opacity-50"
          >
            Anuluj
          </button>
          <button
            type="button"
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

- [ ] **Krok 2: Zaktualizuj import w `ChunkingLab.tsx`**

Zmień linię 8 z:
```tsx
import { DeleteConfirmModal } from "./DeleteConfirmModal";
```
na:
```tsx
import { DeleteConfirmModal } from "../shared/DeleteConfirmModal";
```

- [ ] **Krok 3: Usuń stary plik `src/components/chunks/DeleteConfirmModal.tsx`**

```bash
rm src/components/chunks/DeleteConfirmModal.tsx
```

- [ ] **Krok 4: Sprawdź TypeScript**

```bash
npx tsc -p tsconfig.app.json
```
Oczekiwany wynik: brak błędów.

- [ ] **Krok 5: Commit**

```bash
git add src/components/shared/DeleteConfirmModal.tsx \
        src/components/chunks/ChunkingLab.tsx \
        src/components/chunks/DeleteConfirmModal.tsx
git commit -m "refactor: extract DeleteConfirmModal to shared/"
```

---

## Task 2: Documents — kaskadowe usuwanie z potwierdzeniem

**Files:**
- Modify: `src/components/documents/DocumentList.tsx`
- Modify: `src/components/documents/DocumentManager.tsx`

- [ ] **Krok 1: Zastąp `src/components/documents/DocumentList.tsx`**

```tsx
import { Trash2, FileText } from "lucide-react";
import type { DocumentMeta } from "../../types";

interface DocumentListProps {
  documents: DocumentMeta[];
  selectedId: string | null;
  onSelect: (doc: DocumentMeta) => void;
  onDeleteRequest: (doc: DocumentMeta) => void;
}

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

export function DocumentList({ documents, selectedId, onSelect, onDeleteRequest }: DocumentListProps) {
  if (documents.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">Brak dokumentów.</p>;
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
            onClick={(e) => { e.stopPropagation(); onDeleteRequest(doc); }}
            className="p-1 rounded hover:bg-error/20 hover:text-error text-muted-foreground transition-colors"
            title="Usuń dokument (razem z chunkami i embeddingami)"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Krok 2: Zaktualizuj `src/components/documents/DocumentManager.tsx`**

Dodaj importy na początku:
```tsx
import { useState, useEffect, useCallback } from "react";
import type { DocumentMeta, DocumentDetail, EmbeddingStatus, Folder } from "../../types";
import { api } from "../../api/client";
import { UploadZone } from "./UploadZone";
import { DocumentList } from "./DocumentList";
import { CrawlPanel } from "./CrawlPanel";
import { KnowledgeBaseHealth } from "./KnowledgeBaseHealth";
import { DeleteConfirmModal } from "../shared/DeleteConfirmModal";
```

Dodaj nowe stany i handlery (zastępując poprzednią treść komponentu):
```tsx
export function DocumentManager() {
  const [tab, setTab] = useState<Tab>("upload");
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);

  // Delete state
  const [docToDelete, setDocToDelete] = useState<DocumentMeta | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    api.listDocuments().then(setDocuments).catch(console.error);
    api.getEmbeddingStatus().then(setEmbeddingStatus).catch(() => {});
    api.getFolders().then(setFolders).catch(() => {});
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

  const handleDeleteRequest = useCallback((doc: DocumentMeta) => {
    setDocToDelete(doc);
  }, []);

  const handleDeleteCancel = useCallback(() => {
    setDocToDelete(null);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!docToDelete) return;
    setDeleteLoading(true);
    const id = docToDelete.id;
    try {
      await api.deleteChunks(id).catch(() => {});
      await api.deleteEmbeddingsByDocument(id).catch(() => {});
      await api.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      if (selected?.id === id) setSelected(null);
    } finally {
      setDeleteLoading(false);
      setDocToDelete(null);
    }
  }, [docToDelete, selected]);

  function handleCrawled(added: DocumentMeta[]) {
    if (added.length > 0) {
      setDocuments((prev) => [...added, ...prev]);
    }
  }

  const embeddedDocs = embeddingStatus.length;
  const totalChunks = embeddingStatus.reduce((sum, s) => sum + s.chunk_count, 0);
  const totalChars = documents.reduce((sum, d) => sum + d.char_count, 0);

  return (
    <div className="p-6 h-full flex gap-6">
      <div className="w-80 shrink-0 space-y-4">
        {/* Tabs */}
        <div className="flex border-b">
          {(["upload", "crawl"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                tab === t
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "upload" ? "Upload File" : "From URL"}
            </button>
          ))}
        </div>

        {tab === "upload" && (
          <UploadZone onUploaded={(doc) => setDocuments((prev) => [doc, ...prev])} />
        )}
        {tab === "crawl" && (
          <CrawlPanel onDocumentsAdded={handleCrawled} />
        )}

        <h2 className="font-semibold text-sm">Documents ({documents.length})</h2>
        <DocumentList
          documents={documents}
          selectedId={selected?.id ?? null}
          onSelect={handleSelect}
          onDeleteRequest={handleDeleteRequest}
        />
      </div>

      <div className="flex-1 border rounded-lg bg-card border-border p-4 overflow-auto">
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
          <p className="text-sm text-muted-foreground">Wybierz dokument aby zobaczyć podgląd.</p>
        )}
      </div>

      <div className="w-52 shrink-0">
        <KnowledgeBaseHealth
          totalDocs={documents.length}
          embeddedDocs={embeddedDocs}
          totalChunks={totalChunks}
          totalChars={totalChars}
        />
      </div>

      {docToDelete && (
        <DeleteConfirmModal
          doc={docToDelete}
          chunkCount={null}
          isLoading={deleteLoading}
          onConfirm={handleDeleteConfirm}
          onCancel={handleDeleteCancel}
        />
      )}
    </div>
  );
}
```

Pamiętaj o zachowaniu deklaracji `type Tab = "upload" | "crawl";` nad komponentem.

- [ ] **Krok 3: Sprawdź TypeScript**

```bash
npx tsc -p tsconfig.app.json
```
Oczekiwany wynik: brak błędów.

- [ ] **Krok 4: Commit**

```bash
git add src/components/documents/DocumentList.tsx \
        src/components/documents/DocumentManager.tsx
git commit -m "feat(documents): cascade delete with confirmation modal"
```

---

## Task 3: Documents — wyszukiwarka i filtr po folderze

**Files:**
- Modify: `src/components/documents/DocumentManager.tsx`

- [ ] **Krok 1: Dodaj stany i logikę filtrowania w `DocumentManager`**

Dodaj nowe stany po istniejących:
```tsx
const [searchQuery, setSearchQuery] = useState("");
const [activeFolderId, setActiveFolderId] = useState<"all" | string | null>("all");
```

Dodaj obliczenie filtrowanej listy (przed `return`):
```tsx
const filteredDocuments = documents
  .filter((d) => {
    if (activeFolderId === "all") return true;
    if (activeFolderId === null) return !d.folder_id;
    return d.folder_id === activeFolderId;
  })
  .filter((d) =>
    searchQuery === "" || d.name.toLowerCase().includes(searchQuery.toLowerCase())
  );
```

- [ ] **Krok 2: Dodaj UI wyszukiwarki i chipów folderów w JSX**

Zastąp sekcję `<h2 className="font-semibold text-sm">Documents ({documents.length})</h2>` następującym blokiem:

```tsx
{/* Folder filter chips */}
{folders.length > 0 && (
  <div className="flex flex-wrap gap-1.5">
    {[
      { id: "all" as const, label: "Wszystkie", count: documents.length },
      ...folders.map((f) => ({
        id: f.id,
        label: f.name,
        count: documents.filter((d) => d.folder_id === f.id).length,
      })),
      {
        id: null as null,
        label: "Bez folderu",
        count: documents.filter((d) => !d.folder_id).length,
      },
    ].map(({ id, label, count }) => (
      <button
        key={id ?? "__none"}
        onClick={() => setActiveFolderId(id)}
        className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
          activeFolderId === id
            ? "bg-primary/15 border-primary/60 text-primary"
            : "border-border text-muted-foreground hover:border-primary/40 hover:text-foreground"
        }`}
      >
        {label} <span className="opacity-60">{count}</span>
      </button>
    ))}
  </div>
)}

{/* Search */}
<div className="relative">
  <input
    type="text"
    placeholder="Szukaj dokumentów…"
    value={searchQuery}
    onChange={(e) => setSearchQuery(e.target.value)}
    className="w-full text-sm border border-border rounded-md px-3 py-1.5 bg-muted text-foreground outline-none focus:border-primary placeholder:text-muted-foreground"
  />
</div>

<h2 className="font-semibold text-sm">Documents ({filteredDocuments.length})</h2>
```

- [ ] **Krok 3: Przekaż `filteredDocuments` do `DocumentList`**

Zmień:
```tsx
<DocumentList
  documents={documents}
```
na:
```tsx
<DocumentList
  documents={filteredDocuments}
```

- [ ] **Krok 4: Sprawdź TypeScript**

```bash
npx tsc -p tsconfig.app.json
```
Oczekiwany wynik: brak błędów.

- [ ] **Krok 5: Commit**

```bash
git add src/components/documents/DocumentManager.tsx
git commit -m "feat(documents): add search bar and folder filter chips"
```

---

## Task 4: Documents — FolderAssignModal po uploadzie i crawlu

**Files:**
- Create: `src/components/documents/FolderAssignModal.tsx`
- Modify: `src/components/documents/DocumentManager.tsx`

- [ ] **Krok 1: Utwórz `src/components/documents/FolderAssignModal.tsx`**

```tsx
import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import type { DocumentMeta, Folder } from "../../types";

interface FolderAssignModalProps {
  docs: DocumentMeta[];
  folders: Folder[];
  onAssign: (folderId: string | null) => Promise<void>;
  onSkip: () => void;
  onCreateFolder: (name: string) => Promise<Folder>;
}

export function FolderAssignModal({
  docs,
  folders,
  onAssign,
  onSkip,
  onCreateFolder,
}: FolderAssignModalProps) {
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(
    folders[0]?.id ?? null
  );
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [loading, setLoading] = useState(false);
  const newFolderRef = useRef<HTMLInputElement>(null);
  const skipRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    skipRef.current?.focus();
  }, []);

  useEffect(() => {
    if (creatingFolder) newFolderRef.current?.focus();
  }, [creatingFolder]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !loading) onSkip();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onSkip, loading]);

  async function handleConfirm() {
    setLoading(true);
    try {
      await onAssign(selectedFolderId);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateFolder() {
    const name = newFolderName.trim();
    if (!name) return;
    setLoading(true);
    try {
      const folder = await onCreateFolder(name);
      setSelectedFolderId(folder.id);
      setCreatingFolder(false);
      setNewFolderName("");
    } finally {
      setLoading(false);
    }
  }

  const title =
    docs.length === 1
      ? `Przypisz „${docs[0].name}" do folderu?`
      : `Przypisz ${docs.length} dokumentów do folderu?`;

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={!loading ? onSkip : undefined}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="bg-card border border-border rounded-lg p-5 w-80 shadow-2xl space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-sm font-semibold">{title}</h3>

        <div className="space-y-2">
          <select
            value={selectedFolderId ?? ""}
            onChange={(e) => setSelectedFolderId(e.target.value || null)}
            disabled={loading}
            className="w-full text-sm border border-border rounded-md px-3 py-1.5 bg-muted text-foreground outline-none focus:border-primary disabled:opacity-50"
          >
            <option value="">— Bez folderu</option>
            {folders.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>

          {creatingFolder ? (
            <div className="flex gap-2">
              <input
                ref={newFolderRef}
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreateFolder();
                  if (e.key === "Escape") { setCreatingFolder(false); setNewFolderName(""); }
                }}
                placeholder="Nazwa folderu"
                disabled={loading}
                className="flex-1 text-sm border border-primary/50 rounded-md px-2.5 py-1 bg-muted text-foreground outline-none disabled:opacity-50"
              />
              <button
                onClick={handleCreateFolder}
                disabled={loading || !newFolderName.trim()}
                className="px-3 py-1 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                Utwórz
              </button>
            </div>
          ) : (
            <button
              onClick={() => setCreatingFolder(true)}
              disabled={loading}
              className="text-xs text-primary hover:underline disabled:opacity-50"
            >
              + Nowy folder
            </button>
          )}
        </div>

        <div className="flex gap-2 justify-end">
          <button
            ref={skipRef}
            type="button"
            onClick={onSkip}
            disabled={loading}
            className="px-3 py-1.5 text-xs border border-border rounded-md hover:bg-muted transition-colors disabled:opacity-50"
          >
            Pomiń
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={loading}
            className="px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {loading ? "Przypisuję…" : "Potwierdź"}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
```

- [ ] **Krok 2: Zintegruj `FolderAssignModal` w `DocumentManager`**

Dodaj import:
```tsx
import { FolderAssignModal } from "./FolderAssignModal";
```

Dodaj stany:
```tsx
const [docsToAssign, setDocsToAssign] = useState<DocumentMeta[]>([]);
const [showFolderModal, setShowFolderModal] = useState(false);
```

Zaktualizuj `UploadZone.onUploaded`:
```tsx
<UploadZone
  onUploaded={(doc) => {
    setDocuments((prev) => [doc, ...prev]);
    setDocsToAssign([doc]);
    setShowFolderModal(true);
  }}
/>
```

Zaktualizuj `handleCrawled`:
```tsx
function handleCrawled(added: DocumentMeta[]) {
  if (added.length > 0) {
    setDocuments((prev) => [...added, ...prev]);
    setDocsToAssign(added);
    setShowFolderModal(true);
  }
}
```

Dodaj handler `handleFolderAssign`:
```tsx
const handleFolderAssign = useCallback(async (folderId: string | null) => {
  await Promise.all(
    docsToAssign.map((doc) => api.assignDocumentToFolder(doc.id, folderId))
  );
  setDocuments((prev) =>
    prev.map((d) =>
      docsToAssign.some((da) => da.id === d.id) ? { ...d, folder_id: folderId } : d
    )
  );
  setShowFolderModal(false);
  setDocsToAssign([]);
}, [docsToAssign]);
```

Dodaj handler `handleFolderSkip`:
```tsx
const handleFolderSkip = useCallback(() => {
  setShowFolderModal(false);
  setDocsToAssign([]);
}, []);
```

Dodaj handler `handleCreateFolder`:
```tsx
const handleCreateFolder = useCallback(async (name: string): Promise<Folder> => {
  const folder = await api.createFolder(name);
  setFolders((prev) => [...prev, folder]);
  return folder;
}, []);
```

Dodaj modal na końcu JSX (po `DeleteConfirmModal`):
```tsx
{showFolderModal && docsToAssign.length > 0 && (
  <FolderAssignModal
    docs={docsToAssign}
    folders={folders}
    onAssign={handleFolderAssign}
    onSkip={handleFolderSkip}
    onCreateFolder={handleCreateFolder}
  />
)}
```

Dodaj import `Folder` do typów (jeśli nie ma):
```tsx
import type { DocumentMeta, DocumentDetail, EmbeddingStatus, Folder } from "../../types";
```

- [ ] **Krok 3: Sprawdź TypeScript**

```bash
npx tsc -p tsconfig.app.json
```
Oczekiwany wynik: brak błędów.

- [ ] **Krok 4: Commit**

```bash
git add src/components/documents/FolderAssignModal.tsx \
        src/components/documents/DocumentManager.tsx
git commit -m "feat(documents): folder assignment modal after upload and crawl"
```

---

## Task 5: Chunking Lab — reorganizacja z tabami Kolejka / Przeglądaj

**Files:**
- Modify: `src/components/chunks/ChunkingLab.tsx`

Całkowite przepisanie `ChunkingLab.tsx`. Usuwa: DocPicker, obsługę folderów, obsługę usuwania dokumentów. Dodaje: taby Kolejka / Przeglądaj, per-doc chunk buttons.

- [ ] **Krok 1: Zastąp `src/components/chunks/ChunkingLab.tsx`**

```tsx
import { useState, useEffect, useRef } from "react";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import type { DocumentMeta, ChunkRequest, ChunkResponse } from "../../types";
import { api } from "../../api/client";
import { StrategySelector } from "./StrategySelector";
import { ChunkViewer } from "./ChunkViewer";
import { DeleteConfirmModal } from "../shared/DeleteConfirmModal";

type LabTab = "queue" | "browse";

interface BulkResult {
  docId: string;
  name: string;
  status: "ok" | "error";
  chunkCount?: number;
  error?: string;
}

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

export function ChunkingLab() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [chunkReq, setChunkReq] = useState<ChunkRequest>({
    document_id: "",
    strategy: "fixed",
    chunk_size: 1000,
    overlap: 100,
  });
  const [chunkCounts, setChunkCounts] = useState<Record<string, number>>({});
  const [tab, setTab] = useState<LabTab>("queue");

  // Queue tab state
  const [singleLoading, setSingleLoading] = useState<Set<string>>(new Set());
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkProgress, setBulkProgress] = useState<{ current: number; total: number } | null>(null);
  const [bulkResults, setBulkResults] = useState<BulkResult[]>([]);

  // Browse tab state
  const [browseDocId, setBrowseDocId] = useState<string>("");
  const [browseResponse, setBrowseResponse] = useState<ChunkResponse | null>(null);
  const [browseLoading, setBrowseLoading] = useState(false);
  const [deleteChunksDoc, setDeleteChunksDoc] = useState<DocumentMeta | null>(null);
  const [deleteChunksLoading, setDeleteChunksLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const initialLoadDone = useRef(false);

  useEffect(() => {
    async function load() {
      const docs = await api.listDocuments();
      setDocuments(docs);

      const settled = await Promise.allSettled(docs.map((d) => api.getChunks(d.id)));
      const counts: Record<string, number> = {};
      settled.forEach((r, i) => {
        if (r.status === "fulfilled") counts[docs[i].id] = r.value.chunks.length;
      });
      setChunkCounts(counts);
      initialLoadDone.current = true;
    }
    load().catch(console.error);
  }, []);

  // Load chunks for browse tab when browseDocId changes
  useEffect(() => {
    if (!browseDocId || !initialLoadDone.current) {
      if (!browseDocId) setBrowseResponse(null);
      return;
    }
    setBrowseLoading(true);
    api.getChunks(browseDocId)
      .then(setBrowseResponse)
      .catch(() => setBrowseResponse(null))
      .finally(() => setBrowseLoading(false));
  }, [browseDocId]);

  const unchunkedDocs = documents.filter((d) => !(chunkCounts[d.id] > 0));
  const chunkedDocs = documents.filter((d) => (chunkCounts[d.id] ?? 0) > 0);

  async function chunkSingle(docId: string) {
    setError(null);
    setSingleLoading((prev) => new Set([...prev, docId]));
    try {
      const res = await api.generateChunks({ ...chunkReq, document_id: docId });
      setChunkCounts((prev) => ({ ...prev, [docId]: res.chunks.length }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setSingleLoading((prev) => {
        const next = new Set(prev);
        next.delete(docId);
        return next;
      });
    }
  }

  async function chunkQueue() {
    const queue = [...unchunkedDocs];
    if (queue.length === 0) return;
    setBulkRunning(true);
    setBulkResults([]);
    setBulkProgress({ current: 0, total: queue.length });
    setError(null);

    const results: BulkResult[] = [];
    for (let i = 0; i < queue.length; i++) {
      const doc = queue[i];
      setBulkProgress({ current: i + 1, total: queue.length });
      try {
        const res = await api.generateChunks({ ...chunkReq, document_id: doc.id });
        results.push({ docId: doc.id, name: doc.name, status: "ok", chunkCount: res.chunks.length });
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

  const handleDeleteChunksRequest = (doc: DocumentMeta) => {
    setDeleteChunksDoc(doc);
  };

  const handleDeleteChunksCancel = () => {
    setDeleteChunksDoc(null);
  };

  const handleDeleteChunksConfirm = async () => {
    if (!deleteChunksDoc) return;
    setDeleteChunksLoading(true);
    const id = deleteChunksDoc.id;
    try {
      await api.deleteChunks(id);
      setChunkCounts((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      if (browseDocId === id) {
        setBrowseDocId("");
        setBrowseResponse(null);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleteChunksLoading(false);
      setDeleteChunksDoc(null);
    }
  };

  const bulkOk = bulkResults.filter((r) => r.status === "ok").length;
  const bulkErr = bulkResults.filter((r) => r.status === "error").length;

  return (
    <div className="p-6 h-full flex gap-6">
      {/* Left: Strategy settings */}
      <div className="w-72 shrink-0 space-y-4">
        <h2 className="font-semibold text-sm">Chunking Lab</h2>
        <StrategySelector value={chunkReq} onChange={setChunkReq} documentId="" />
        {error && <p className="text-xs text-error">{error}</p>}
      </div>

      {/* Right: Tabs */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Tab headers */}
        <div className="flex border-b mb-4 shrink-0">
          <button
            onClick={() => setTab("queue")}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === "queue"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Kolejka{unchunkedDocs.length > 0 && ` (${unchunkedDocs.length})`}
          </button>
          <button
            onClick={() => setTab("browse")}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === "browse"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Przeglądaj{chunkedDocs.length > 0 && ` (${chunkedDocs.length})`}
          </button>
        </div>

        {/* Queue tab */}
        {tab === "queue" && (
          <div className="flex-1 overflow-auto space-y-3">
            {unchunkedDocs.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Wszystkie dokumenty mają wygenerowane chunki.
              </p>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">
                    {unchunkedDocs.length} {unchunkedDocs.length === 1 ? "dokument" : "dokumentów"} bez chunków
                  </p>
                  <button
                    onClick={chunkQueue}
                    disabled={bulkRunning}
                    className="px-3 py-1.5 text-xs border border-primary text-primary rounded-md hover:bg-primary/5 disabled:opacity-50 transition-colors"
                  >
                    {bulkRunning
                      ? `Przetwarzam ${bulkProgress?.current}/${bulkProgress?.total}…`
                      : `Chunkuj całą kolejkę (${unchunkedDocs.length})`}
                  </button>
                </div>

                {bulkProgress && (
                  <div className="space-y-1.5">
                    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-300 rounded-full"
                        style={{
                          width: `${Math.round((bulkProgress.current / bulkProgress.total) * 100)}%`,
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

                <div className="space-y-2">
                  {unchunkedDocs.map((doc) => {
                    const isLoading = singleLoading.has(doc.id);
                    const bulkResult = bulkResults.find((r) => r.docId === doc.id);
                    return (
                      <div
                        key={doc.id}
                        className="border border-border rounded-lg p-3 flex items-center gap-3 bg-card"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{doc.name}</p>
                          <p className="text-xs text-muted-foreground">{formatBytes(doc.size_bytes)}</p>
                        </div>
                        {bulkResult && (
                          <span className={`text-xs ${bulkResult.status === "ok" ? "text-success" : "text-error"}`}>
                            {bulkResult.status === "ok" ? `${bulkResult.chunkCount} ch` : "błąd"}
                          </span>
                        )}
                        <button
                          onClick={() => chunkSingle(doc.id)}
                          disabled={isLoading || bulkRunning}
                          className="px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center gap-1.5 shrink-0"
                        >
                          {isLoading && <Loader2 className="w-3 h-3 animate-spin" />}
                          {isLoading ? "Chunkuję…" : "Chunkuj"}
                        </button>
                      </div>
                    );
                  })}
                </div>
              </>
            )}
          </div>
        )}

        {/* Browse tab */}
        {tab === "browse" && (
          <div className="flex-1 flex flex-col min-w-0 overflow-auto gap-4">
            {chunkedDocs.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Brak chunków. Przejdź do zakładki{" "}
                <button className="text-primary underline" onClick={() => setTab("queue")}>Kolejka</button>.
              </p>
            ) : (
              <>
                <div className="flex items-center gap-3 shrink-0">
                  <select
                    value={browseDocId}
                    onChange={(e) => setBrowseDocId(e.target.value)}
                    className="flex-1 text-sm border border-border rounded-md px-3 py-1.5 bg-muted text-foreground outline-none focus:border-primary"
                  >
                    <option value="">Wybierz dokument…</option>
                    {chunkedDocs.map((doc) => (
                      <option key={doc.id} value={doc.id}>
                        {doc.name} ({chunkCounts[doc.id]} chunków)
                      </option>
                    ))}
                  </select>
                  {browseDocId && (
                    <button
                      onClick={() => {
                        const doc = chunkedDocs.find((d) => d.id === browseDocId);
                        if (doc) handleDeleteChunksRequest(doc);
                      }}
                      className="px-3 py-1.5 text-xs text-error border border-error/40 rounded-md hover:bg-error/5 transition-colors shrink-0"
                    >
                      Usuń chunki
                    </button>
                  )}
                </div>
                {browseLoading && (
                  <p className="text-sm text-muted-foreground flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />Ładuję chunki…
                  </p>
                )}
                {!browseLoading && browseResponse && (
                  <ChunkViewer chunks={browseResponse.chunks} stats={browseResponse.stats} />
                )}
                {!browseLoading && !browseDocId && (
                  <p className="text-sm text-muted-foreground">Wybierz dokument aby zobaczyć chunki.</p>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {deleteChunksDoc && (
        <DeleteConfirmModal
          doc={deleteChunksDoc}
          chunkCount={chunkCounts[deleteChunksDoc.id] ?? null}
          isLoading={deleteChunksLoading}
          onConfirm={handleDeleteChunksConfirm}
          onCancel={handleDeleteChunksCancel}
        />
      )}
    </div>
  );
}
```

- [ ] **Krok 2: Sprawdź TypeScript**

```bash
npx tsc -p tsconfig.app.json
```
Oczekiwany wynik: brak błędów.

- [ ] **Krok 3: Commit**

```bash
git add src/components/chunks/ChunkingLab.tsx
git commit -m "feat(chunks): reorganize with Queue and Browse tabs, remove auto-select"
```

---

## Task 6: Embeddings — taby + karty zamiast tabeli

**Files:**
- Modify: `src/components/embeddings/EmbeddingExplorer.tsx`

- [ ] **Krok 1: Zastąp `src/components/embeddings/EmbeddingExplorer.tsx`**

```tsx
import { useState, useEffect } from "react";
import type { DocumentMeta, EmbeddingPoint, EmbeddingStatus } from "../../types";
import { api } from "../../api/client";
import { ScatterPlot } from "./ScatterPlot";
import { Loader2 } from "lucide-react";

type EmbedTab = "generate" | "generated";

interface EmbedProgress {
  current: number;
  total: number;
  currentName: string;
}

export function EmbeddingExplorer() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus[]>([]);
  const [chunkCounts, setChunkCounts] = useState<Record<string, number>>({});
  const [points, setPoints] = useState<EmbeddingPoint[]>([]);
  const [embedProgress, setEmbedProgress] = useState<EmbedProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<EmbedTab>("generate");
  const [selectedA, setSelectedA] = useState<string | null>(null);
  const [selectedB, setSelectedB] = useState<string | null>(null);
  const [similarity, setSimilarity] = useState<number | null>(null);
  const [singleLoading, setSingleLoading] = useState<Set<string>>(new Set());

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

      // Fetch chunk counts for all docs
      const settled = await Promise.allSettled(docs.map((d) => api.getChunks(d.id)));
      const counts: Record<string, number> = {};
      settled.forEach((r, i) => {
        if (r.status === "fulfilled") counts[docs[i].id] = r.value.chunks.length;
      });
      setChunkCounts(counts);
    } catch {
      /* ignore on mount */
    }
  }

  function hasEmbeddings(docId: string): boolean {
    return embeddingStatus.some((s) => s.document_id === docId);
  }

  function getEmbedChunkCount(docId: string): number {
    return embeddingStatus.find((s) => s.document_id === docId)?.chunk_count ?? 0;
  }

  async function embedSingle(doc: DocumentMeta) {
    setError(null);
    setSingleLoading((prev) => new Set([...prev, doc.id]));
    try {
      await api.generateEmbeddings(doc.id);
      const [status, viz] = await Promise.all([
        api.getEmbeddingStatus(),
        api.getVisualization(),
      ]);
      setEmbeddingStatus(status);
      setPoints(viz);
    } catch (e: unknown) {
      setError(`Błąd przy "${doc.name}": ${e instanceof Error ? e.message : "unknown error"}`);
    } finally {
      setSingleLoading((prev) => {
        const next = new Set(prev);
        next.delete(doc.id);
        return next;
      });
    }
  }

  async function embedAll() {
    const toEmbed = docsWithoutEmbeddings;
    if (!toEmbed.length) return;
    setError(null);

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
        setError(`Błąd przy "${doc.name}": ${e instanceof Error ? e.message : "unknown error"}`);
      }
    }
    setEmbedProgress(null);
  }

  async function handleDeleteEmbeddings(docId: string) {
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

  async function handleSelectPoint(chunkId: string) {
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

  const docsWithoutEmbeddings = documents.filter((d) => !hasEmbeddings(d.id));
  const docsWithEmbeddings = documents.filter((d) => hasEmbeddings(d.id));

  return (
    <div className="p-6 h-full flex flex-col gap-4 overflow-auto">
      {/* Tab headers */}
      <div className="flex border-b shrink-0">
        <button
          onClick={() => setTab("generate")}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
            tab === "generate"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Do wygenerowania{docsWithoutEmbeddings.length > 0 && ` (${docsWithoutEmbeddings.length})`}
        </button>
        <button
          onClick={() => setTab("generated")}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
            tab === "generated"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          Wygenerowane{docsWithEmbeddings.length > 0 && ` (${docsWithEmbeddings.length})`}
        </button>
      </div>

      {error && (
        <div className="text-xs text-error bg-error/10 border border-error/20 rounded-md px-3 py-2 shrink-0">
          {error}
        </div>
      )}

      {/* Generate tab */}
      {tab === "generate" && (
        <div className="space-y-3">
          {docsWithoutEmbeddings.length === 0 ? (
            <p className="text-sm text-muted-foreground">Wszystkie dokumenty mają wygenerowane embeddingi.</p>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  {docsWithoutEmbeddings.length} {docsWithoutEmbeddings.length === 1 ? "dokument" : "dokumentów"} bez embeddingów
                </p>
                <button
                  onClick={embedAll}
                  disabled={!!embedProgress}
                  className="px-3 py-1.5 text-xs border border-primary text-primary rounded-md hover:bg-primary/5 disabled:opacity-50 transition-colors"
                >
                  {embedProgress
                    ? `Embeduję ${embedProgress.current}/${embedProgress.total}: ${embedProgress.currentName}…`
                    : `Wygeneruj wszystkie (${docsWithoutEmbeddings.length})`}
                </button>
              </div>

              <div className="space-y-2">
                {docsWithoutEmbeddings.map((doc) => {
                  const isLoading = singleLoading.has(doc.id);
                  const chunks = chunkCounts[doc.id];
                  return (
                    <div
                      key={doc.id}
                      className="border border-border rounded-lg p-3 flex items-center gap-3 bg-card"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{doc.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {chunks !== undefined ? `${chunks} chunków` : "brak chunków"}
                        </p>
                      </div>
                      <button
                        onClick={() => embedSingle(doc)}
                        disabled={isLoading || !!embedProgress || !chunks}
                        className="px-3 py-1.5 text-xs bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors flex items-center gap-1.5 shrink-0"
                        title={!chunks ? "Najpierw wygeneruj chunki" : undefined}
                      >
                        {isLoading && <Loader2 className="w-3 h-3 animate-spin" />}
                        {isLoading ? "Embeduję…" : "Embed"}
                      </button>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}

      {/* Generated tab */}
      {tab === "generated" && (
        <div className="space-y-4">
          {docsWithEmbeddings.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              Brak wygenerowanych embeddingów. Przejdź do zakładki{" "}
              <button className="text-primary underline" onClick={() => setTab("generate")}>
                Do wygenerowania
              </button>.
            </p>
          ) : (
            <div className="space-y-2">
              {docsWithEmbeddings.map((doc) => (
                <div
                  key={doc.id}
                  className="border border-border rounded-lg p-3 flex items-center gap-3 bg-card"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{doc.name}</p>
                    <p className="text-xs text-success">{getEmbedChunkCount(doc.id)} chunków osadzonych</p>
                  </div>
                  <button
                    onClick={() => handleDeleteEmbeddings(doc.id)}
                    className="px-3 py-1.5 text-xs text-error border border-error/40 rounded-md hover:bg-error/5 transition-colors shrink-0"
                  >
                    Usuń
                  </button>
                </div>
              ))}
            </div>
          )}

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
            onSelect={handleSelectPoint}
          />

          <p className="text-xs text-muted-foreground">
            Wizualizacja używa PCA (rzut 2D). Kliknij punkt aby go zaznaczyć, kliknij drugi aby porównać podobieństwo cosinusowe.
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Krok 2: Sprawdź TypeScript**

```bash
npx tsc -p tsconfig.app.json
```
Oczekiwany wynik: brak błędów.

- [ ] **Krok 3: Commit**

```bash
git add src/components/embeddings/EmbeddingExplorer.tsx
git commit -m "feat(embeddings): add generate/generated tabs with card layout"
```

---

## Task 7: Tutorial — aktualizacja treści

**Files:**
- Modify: `src/components/tutorial/TutorialPanel.tsx`

- [ ] **Krok 1: Zaktualizuj `PipelineStep` dla Documents**

Znajdź blok `<PipelineStep icon="📄" panel="Documents" ...>` i zastąp jego zawętrzność:

```tsx
<PipelineStep icon="📄" panel="Documents" title="Wgraj dokument i organizuj bazę wiedzy">
  <ol className="list-decimal list-inside space-y-1 text-sm">
    <li>Przeciągnij plik <Code>.txt</Code>, <Code>.pdf</Code> lub <Code>.docx</Code> na strefę uploadu — lub wklej URL bloga w zakładce "From URL"</li>
    <li>Po wgraniu system zapyta, czy przypisać dokument do folderu — wybierz istniejący, utwórz nowy lub pomiń</li>
    <li>Użyj chipów folderów i pola wyszukiwania aby filtrować listę dokumentów</li>
    <li>Kliknij na dokument — zobaczysz podgląd surowego tekstu po prawej</li>
    <li>Kliknij ikonę kosza aby usunąć dokument — zostaniesz poproszony o potwierdzenie, po którym usunięte zostaną też jego chunki i embeddingi</li>
  </ol>
  <Note>Im bardziej spójny i ustrukturyzowany dokument, tym lepsze wyniki retrieval.</Note>
</PipelineStep>
```

- [ ] **Krok 2: Zaktualizuj `PipelineStep` dla Chunking Lab**

Znajdź blok `<PipelineStep icon="✂️" panel="Chunking Lab" ...>` i zastąp jego zawętrzność:

```tsx
<PipelineStep icon="✂️" panel="Chunking Lab" title="Podziel tekst na fragmenty">
  <ol className="list-decimal list-inside space-y-1 text-sm">
    <li>W lewym panelu ustaw strategię: <strong>Fixed Size</strong>, <strong>Recursive</strong> lub <strong>Semantic</strong>, a także suwaki <strong>Chunk Size</strong> i <strong>Overlap</strong></li>
    <li>Zakładka <strong>Kolejka</strong> pokazuje dokumenty bez chunków — kliknij "Chunkuj" przy wybranym dokumencie lub "Chunkuj całą kolejkę" dla wszystkich</li>
    <li>Zakładka <strong>Przeglądaj</strong> pokazuje dokumenty z chunkami — wybierz dokument z listy aby zobaczyć wygenerowane fragmenty i ich statystyki</li>
  </ol>
  <Note>Zbyt duże chunki = mało precyzyjny retrieval. Overlap zapobiega ucinaniu sensu na granicy.</Note>
</PipelineStep>
```

- [ ] **Krok 3: Zaktualizuj `PipelineStep` dla Embeddings**

Znajdź blok `<PipelineStep icon="🔵" panel="Embeddings" ...>` i zastąp go:

```tsx
<PipelineStep icon="🔵" panel="Embeddings" title="Wygeneruj embeddingi i wizualizuj">
  <ol className="list-decimal list-inside space-y-1 text-sm">
    <li>Zakładka <strong>Do wygenerowania</strong> pokazuje dokumenty bez embeddingów — kliknij "Embed" przy wybranym dokumencie lub "Wygeneruj wszystkie"</li>
    <li>Zakładka <strong>Wygenerowane</strong> pokazuje dokumenty z embeddingami i scatter plot w 2D</li>
    <li>Kliknij punkt na wykresie — zobaczysz treść chunku</li>
    <li>Kliknij dwa punkty kolejno → zobaczysz cosine similarity (0–1)</li>
  </ol>

  <div className="space-y-2 mt-2">
    <p className="font-medium text-foreground text-sm">Co widzę na wykresie?</p>
    <p>Każdy punkt to jeden chunk tekstu. Jego <strong>pozycja</strong> reprezentuje znaczenie — model OpenAI zamienił każdy fragment w wektor 1536 liczb (tzw. embedding), a PCA spłaszczyło to do 2D żebyś mógł to zobaczyć. Punkty blisko siebie = fragmenty o podobnym znaczeniu.</p>
    <p>Przy 2–3 punktach wykres wygląda pusto — dopiero przy 20+ chunków widać skupiska tematyczne.</p>
  </div>

  <div className="space-y-2 mt-2">
    <p className="font-medium text-foreground text-sm">Co oznacza cosine similarity?</p>
    <p>Miara podobieństwa między dwoma fragmentami: <strong>1.0</strong> = identyczne znaczenie, <strong>0.0</strong> = zupełnie różne, <strong>wartości ujemne</strong> = przeciwstawne. Właśnie tym kryterium RAG wybiera najlepsze chunki do odpowiedzi na Twoje pytanie.</p>
  </div>
</PipelineStep>
```

- [ ] **Krok 4: Zaktualizuj tabelę troubleshooting (Część 3)**

Znajdź tablicę wierszy troubleshootingu i zastąp ją:

```tsx
{[
  ["Backend nie startuje — brak modułu", "pip install -r requirements.txt (w aktywowanym venv)"],
  ["\"OPENAI_API_KEY not set\"", "Sprawdź backend/.env — klucz musi zaczynać się od sk-"],
  ["Scatter plot pusty", "Przejdź do zakładki Wygenerowane w sekcji Embeddings — jeśli pusta, najpierw wygeneruj chunki i embeddingi"],
  ["Chat nie odpowiada", "Muszą istnieć embeddingi w ChromaDB — retrieval potrzebuje wektorów"],
  ["Dane po restarcie nadal są", "ChromaDB persystuje w backend/chroma_data/ — użyj Clear All Data"],
  ["Chcę usunąć dokument z bazy", "Kliknij ikonę kosza w sekcji Documents — potwierdzenie usunie dokument razem z chunkami i embeddingami"],
].map(([problem, solution]) => (
  <tr key={problem} className="border-b border-border odd:bg-card even:bg-muted/20">
    <td className="px-3 py-2 border border-border font-medium text-warning">{problem}</td>
    <td className="px-3 py-2 border border-border text-foreground">{solution}</td>
  </tr>
))}
```

- [ ] **Krok 5: Sprawdź TypeScript**

```bash
npx tsc -p tsconfig.app.json
```
Oczekiwany wynik: brak błędów.

- [ ] **Krok 6: Commit**

```bash
git add src/components/tutorial/TutorialPanel.tsx
git commit -m "docs(tutorial): update pipeline steps for new UI (folders, tabs, cascade delete)"
```

---

## Weryfikacja końcowa

Po wykonaniu wszystkich tasków uruchom aplikację i przetestuj:

**Documents:**
- [ ] Upload pliku → pojawia się modal przypisania folderu → potwierdź → dokument dostaje folder_id
- [ ] Crawl URL → modal pojawia się po `done` dla wszystkich artykułów
- [ ] Chip folderów filtruje listę; wyszukiwarka filtruje po nazwie; oba filtry działają jednocześnie
- [ ] Kosz → modal potwierdzenia → dokument + chunki + embeddingi znikają

**Chunking Lab:**
- [ ] Przy wejściu w sekcję: zakładka Kolejka pokazuje dokumenty bez chunków, żaden nie jest auto-wybrany
- [ ] "Chunkuj" przy pojedynczym dokumencie → dokument przenosi się do zakładki Przeglądaj
- [ ] "Chunkuj całą kolejkę" z progress barem
- [ ] Zakładka Przeglądaj: dropdown z chunked docs → ChunkViewer → "Usuń chunki" z potwierdzeniem

**Embeddings:**
- [ ] Zakładka "Do wygenerowania": karty z docs bez embeddingów, "Embed" per doc, "Wygeneruj wszystkie"
- [ ] Po wygenerowaniu dokument przenosi się do "Wygenerowane"
- [ ] Zakładka "Wygenerowane": karty + scatter plot + similarity comparison

**Tutorial:**
- [ ] Kroki Documents, Chunking Lab, Embeddings odzwierciedlają nowy UX
- [ ] Troubleshooting zawiera nowe wiersze

```bash
git log --oneline -8
```
Oczekiwany wynik: 7 commitów (Task 1–7 + spec).
