import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { CheckCircle, XCircle, Loader2, Folder as FolderIcon, X } from "lucide-react";
import type { DocumentMeta, ChunkRequest, ChunkResponse, EmbeddingStatus, Folder } from "../../types";
import { api } from "../../api/client";
import { StrategySelector } from "./StrategySelector";
import { ChunkViewer } from "./ChunkViewer";
import { DocPicker } from "./DocPicker";
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

interface FolderMenuButtonProps {
  docId: string;
  folderId: string | null | undefined;
  folders: Folder[];
  onAssign: (docId: string, folderId: string | null) => Promise<void>;
}

function FolderMenuButton({ docId, folderId, folders, onAssign }: FolderMenuButtonProps) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, right: 0 });
  const btnRef = useRef<HTMLButtonElement>(null);

  function openMenu() {
    if (btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      setPos({ top: rect.bottom + 4, right: window.innerWidth - rect.right });
    }
    setOpen(true);
  }

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  const assignedFolder = folders.find((f) => f.id === folderId);

  return (
    <>
      <button
        ref={btnRef}
        onClick={openMenu}
        className={`p-1.5 rounded transition-colors shrink-0 ${
          assignedFolder
            ? "text-primary hover:bg-primary/10"
            : "text-muted-foreground hover:text-primary hover:bg-muted"
        }`}
        title={assignedFolder ? `Folder: ${assignedFolder.name}` : "Przypisz do folderu"}
      >
        <FolderIcon className="w-3.5 h-3.5" />
      </button>
      {open && createPortal(
        <>
          <div className="fixed inset-0 z-[59]" onClick={() => setOpen(false)} />
          <div
            className="fixed z-[60] bg-card border border-border rounded-md shadow-xl py-1 min-w-[160px]"
            style={{ top: pos.top, right: pos.right }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-3 py-1.5 text-[10px] text-muted-foreground font-medium uppercase tracking-wide border-b border-border">
              Przypisz folder
            </div>
            <button
              className="w-full text-left px-3 py-1.5 text-[11px] text-muted-foreground hover:bg-muted transition-colors"
              onClick={() => { onAssign(docId, null); setOpen(false); }}
            >
              — Bez folderu
            </button>
            {folders.map((f) => (
              <button
                key={f.id}
                className={`w-full text-left px-3 py-1.5 text-[11px] transition-colors hover:bg-muted flex items-center gap-2 ${
                  folderId === f.id ? "text-primary" : "text-foreground"
                }`}
                onClick={() => { onAssign(docId, f.id); setOpen(false); }}
              >
                <FolderIcon className="w-3 h-3 text-muted-foreground shrink-0" />
                {f.name}
              </button>
            ))}
          </div>
        </>,
        document.body
      )}
    </>
  );
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
  const [deleteDocDoc, setDeleteDocDoc] = useState<DocumentMeta | null>(null);
  const [deleteDocLoading, setDeleteDocLoading] = useState(false);
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);

  const [error, setError] = useState<string | null>(null);
  const initialLoadDone = useRef(false);

  useEffect(() => {
    async function load() {
      const [docs, embStatus, folderList] = await Promise.all([
        api.listDocuments(),
        api.getEmbeddingStatus(),
        api.getFolders(),
      ]);
      setDocuments(docs);
      setEmbeddingStatus(embStatus);
      setFolders(folderList);

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

  async function handleDeleteDocConfirm() {
    if (!deleteDocDoc) return;
    setDeleteDocLoading(true);
    const id = deleteDocDoc.id;
    try {
      await api.deleteChunks(id).catch(() => {});
      await api.deleteEmbeddingsByDocument(id).catch(() => {});
      await api.deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setChunkCounts((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleteDocLoading(false);
      setDeleteDocDoc(null);
    }
  }

  async function handleCreateFolder(name: string) {
    const folder = await api.createFolder(name);
    setFolders((prev) => [...prev, folder]);
  }

  async function handleAssignFolder(docId: string, folderId: string | null) {
    await api.assignDocumentToFolder(docId, folderId);
    setDocuments((prev) =>
      prev.map((d) => (d.id === docId ? { ...d, folder_id: folderId } : d))
    );
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
                          <p className="text-xs text-muted-foreground">
                            {formatBytes(doc.size_bytes)}
                            {doc.folder_id && folders.length > 0 && (
                              <span className="ml-1 text-primary/70">
                                · {folders.find((f) => f.id === doc.folder_id)?.name}
                              </span>
                            )}
                          </p>
                        </div>
                        {bulkResult && (
                          <span className={`text-xs ${bulkResult.status === "ok" ? "text-success" : "text-error"}`}>
                            {bulkResult.status === "ok" ? `${bulkResult.chunkCount} ch` : "błąd"}
                          </span>
                        )}
                        <FolderMenuButton
                          docId={doc.id}
                          folderId={doc.folder_id}
                          folders={folders}
                          onAssign={handleAssignFolder}
                        />
                        <button
                          onClick={() => setDeleteDocDoc(doc)}
                          disabled={isLoading || bulkRunning}
                          className="p-1.5 rounded text-muted-foreground hover:text-error hover:bg-error/10 disabled:opacity-50 transition-colors shrink-0"
                          title="Usuń dokument"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
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
                <div className="flex items-center gap-2 shrink-0">
                  <div className="flex-1 min-w-0">
                    <DocPicker
                      documents={documents}
                      chunkCounts={chunkCounts}
                      embeddingStatus={embeddingStatus}
                      selectedDocId={browseDocId}
                      onSelect={setBrowseDocId}
                      onDelete={handleDeleteChunksRequest}
                      folders={folders}
                      onCreateFolder={handleCreateFolder}
                      onAssignFolder={handleAssignFolder}
                      lockedChunkFilter="ready"
                    />
                  </div>
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
      {deleteDocDoc && (
        <DeleteConfirmModal
          doc={deleteDocDoc}
          chunkCount={chunkCounts[deleteDocDoc.id] ?? null}
          isLoading={deleteDocLoading}
          onConfirm={handleDeleteDocConfirm}
          onCancel={() => setDeleteDocDoc(null)}
        />
      )}
    </div>
  );
}
