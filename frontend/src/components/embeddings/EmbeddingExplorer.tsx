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
      <div className="border border-border rounded-lg bg-card overflow-hidden">
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
              className="shrink-0 px-3 py-1.5 bg-primary text-primary-foreground text-sm rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              Generate Selected ({selectedCount})
            </button>
          </div>
        </div>

        {error && (
          <div className="px-4 py-2 text-xs text-error bg-error/10 border-b border-error/20">{error}</div>
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
                        <span className="inline-flex items-center gap-1 text-success font-medium">
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
                          className="text-error/70 hover:text-error disabled:opacity-40 transition-colors"
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
