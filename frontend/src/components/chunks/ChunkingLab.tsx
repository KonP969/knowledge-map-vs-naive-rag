import { useState, useEffect } from "react";
import type { DocumentMeta, ChunkRequest, ChunkResponse } from "../../types";
import { api } from "../../api/client";
import { StrategySelector } from "./StrategySelector";
import { ChunkViewer } from "./ChunkViewer";

export function ChunkingLab() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>("");
  const [chunkReq, setChunkReq] = useState<ChunkRequest>({
    document_id: "",
    strategy: "fixed",
    chunk_size: 500,
    overlap: 50,
  });
  const [response, setResponse] = useState<ChunkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        <button
          onClick={generate}
          disabled={loading || !selectedDocId}
          className="w-full py-2 bg-primary text-white text-sm rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? "Generating..." : "Generate Chunks"}
        </button>
        {error && <p className="text-xs text-red-500">{error}</p>}
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
