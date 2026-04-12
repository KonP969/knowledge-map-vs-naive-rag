import { useState, useEffect } from "react";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import type { DocumentMeta, ChunkRequest, ChunkResponse } from "../../types";
import { api } from "../../api/client";
import { StrategySelector } from "./StrategySelector";
import { ChunkViewer } from "./ChunkViewer";

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

  // Bulk state
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkProgress, setBulkProgress] = useState<{ current: number; total: number } | null>(null);
  const [bulkResults, setBulkResults] = useState<BulkResult[]>([]);

  useEffect(() => {
    api.listDocuments().then((docs) => {
      setDocuments(docs);
      if (docs.length > 0) {
        setSelectedDocId(docs[0].id);
        setChunkReq((prev) => ({ ...prev, document_id: docs[0].id }));
      }
    }).catch(console.error);
  }, []);

  async function generate() {
    if (!selectedDocId) return;
    setLoading(true);
    setError(null);
    try {
      const req = { ...chunkReq, document_id: selectedDocId };
      const res = await api.generateChunks(req);
      setResponse(res);
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
        // Show last successful result in viewer
        setResponse(res);
        setSelectedDocId(doc.id);
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

  const bulkOk = bulkResults.filter((r) => r.status === "ok").length;
  const bulkErr = bulkResults.filter((r) => r.status === "error").length;

  return (
    <div className="p-6 h-full flex gap-6">
      <div className="w-72 shrink-0 space-y-4">
        <h2 className="font-semibold text-sm">Chunking Lab</h2>
        <div>
          <label className="text-xs font-medium text-muted-foreground">Document</label>
          <select
            className="w-full mt-1 text-sm border border-border rounded-md px-2 py-1.5 bg-white"
            value={selectedDocId}
            onChange={(e) => {
              setSelectedDocId(e.target.value);
              setChunkReq((prev) => ({ ...prev, document_id: e.target.value }));
            }}
          >
            {documents.length === 0 && <option value="">No documents</option>}
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

        {/* Single doc */}
        <button
          onClick={generate}
          disabled={loading || bulkRunning || !selectedDocId}
          className="w-full py-2 bg-primary text-white text-sm rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? "Generating..." : "Generate Chunks"}
        </button>

        {/* All docs */}
        <button
          onClick={generateAll}
          disabled={loading || bulkRunning || documents.length === 0}
          className="w-full py-2 border border-primary text-primary text-sm rounded-md hover:bg-primary/5 disabled:opacity-50 transition-colors"
        >
          {bulkRunning
            ? `Przetwarzam ${bulkProgress?.current}/${bulkProgress?.total}…`
            : `Generate All (${documents.length})`}
        </button>

        {error && <p className="text-xs text-red-500">{error}</p>}

        {/* Bulk progress bar */}
        {bulkProgress && (
          <div className="space-y-1.5">
            <div className="h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300 rounded-full"
                style={{ width: `${Math.round((bulkProgress.current / bulkProgress.total) * 100)}%` }}
              />
            </div>
            <div className="flex gap-3 text-xs">
              {bulkOk > 0 && <span className="text-green-600 flex items-center gap-1"><CheckCircle className="w-3 h-3" />{bulkOk} ok</span>}
              {bulkErr > 0 && <span className="text-red-500 flex items-center gap-1"><XCircle className="w-3 h-3" />{bulkErr} błędy</span>}
              {bulkRunning && <span className="text-muted-foreground flex items-center gap-1"><Loader2 className="w-3 h-3 animate-spin" />w toku</span>}
            </div>
          </div>
        )}

        {/* Bulk results list */}
        {bulkResults.length > 0 && (
          <div className="border rounded-md divide-y max-h-48 overflow-y-auto">
            {bulkResults.map((r) => (
              <div key={r.docId} className="flex items-start gap-2 px-2.5 py-1.5">
                {r.status === "ok"
                  ? <CheckCircle className="w-3 h-3 text-green-500 mt-0.5 shrink-0" />
                  : <XCircle className="w-3 h-3 text-red-400 mt-0.5 shrink-0" />}
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
    </div>
  );
}
