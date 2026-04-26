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
