import { useState, useEffect } from "react";
import type { DocumentMeta, EmbeddingPoint } from "../../types";
import { api } from "../../api/client";
import { ScatterPlot } from "./ScatterPlot";

export function EmbeddingExplorer() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<string>("");
  const [points, setPoints] = useState<EmbeddingPoint[]>([]);
  const [selectedA, setSelectedA] = useState<string | null>(null);
  const [selectedB, setSelectedB] = useState<string | null>(null);
  const [similarity, setSimilarity] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listDocuments().then((docs) => {
      setDocuments(docs);
      if (docs.length) setSelectedDoc(docs[0].id);
    }).catch(console.error);
    api.getVisualization().then(setPoints).catch(() => {});
  }, []);

  async function handleEmbed() {
    if (!selectedDoc) return;
    setLoading(true);
    setError(null);
    try {
      await api.generateEmbeddings(selectedDoc);
      const viz = await api.getVisualization();
      setPoints(viz);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Embedding failed");
    } finally {
      setLoading(false);
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

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <h2 className="font-semibold text-sm">Embedding Explorer</h2>
        <select
          className="text-sm border border-border rounded-md px-2 py-1.5 bg-white"
          value={selectedDoc}
          onChange={(e) => setSelectedDoc(e.target.value)}
        >
          {documents.length === 0 && <option value="">No documents</option>}
          {documents.map((d) => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
        <button
          onClick={handleEmbed}
          disabled={loading || !selectedDoc}
          className="px-3 py-1.5 bg-primary text-white text-sm rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
        >
          {loading ? "Embedding..." : "Generate Embeddings"}
        </button>
        {error && <span className="text-xs text-red-500">{error}</span>}
      </div>

      {selectedA && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">
            {selectedB
              ? "Similarity between selected chunks:"
              : `Selected: ${selectedA.slice(0, 8)}\u2026 \u2014 click another point to compare`}
          </span>
          {similarity != null && (
            <span className="font-semibold text-primary">
              cosine = {similarity.toFixed(4)}
            </span>
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
        Visualization uses PCA (2D projection). Click a point to select it, click another to compare cosine similarity.
      </p>
    </div>
  );
}
