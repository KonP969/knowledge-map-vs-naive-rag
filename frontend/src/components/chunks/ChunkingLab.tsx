import { useState, useEffect, useCallback, useRef } from "react";
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

  const initialLoadDone = useRef(false);

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
      initialLoadDone.current = true;

      // Load chunks for the initially selected document
      if (docs.length > 0 && counts[docs[0].id] !== undefined) {
        api.getChunks(docs[0].id).then(setResponse).catch(() => setResponse(null));
      }
    }
    load().catch(console.error);
  }, []);

  // Load chunks for selected doc when selection changes
  useEffect(() => {
    if (!selectedDocId || !initialLoadDone.current) {
      if (!selectedDocId) setResponse(null);
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

  const handleDeleteCancel = useCallback(() => {
    setDocToDelete(null);
    setError(null);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!docToDelete) return;
    setDeleteLoading(true);
    setError(null);
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
      // Chunks may have been deleted even if a later step failed — clear stale count
      setChunkCounts((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
    } finally {
      setDeleteLoading(false);
      setDocToDelete(null);
    }
  }, [docToDelete]);

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
          onCancel={handleDeleteCancel}
        />
      )}
    </div>
  );
}
