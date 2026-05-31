import { useState, useEffect, useRef } from "react";
import { Upload, RefreshCw, FileText, Tag, Clock, Trash2, RotateCcw, Loader, CheckCircle, AlertCircle, ArrowUp, ArrowDown } from "lucide-react";
import { api } from "../../api/client";
import type { WikiSource, IngestResult } from "../../types";

type SortBy = "date" | "title";
type SortDir = "asc" | "desc";

export function SourcesPanel() {
  const [sources, setSources] = useState<WikiSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number }>({ current: 0, total: 0 });
  const [lastResult, setLastResult] = useState<IngestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const [sortBy, setSortBy] = useState<SortBy>("date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetting, setResetting] = useState(false);

  // URL crawl states
  const [crawlUrl, setCrawlUrl] = useState("");
  const [crawlMax, setCrawlMax] = useState(5);
  const [crawling, setCrawling] = useState(false);

  type CrawlItem = { index: number; title: string; url: string; status: "pending" | "ok" | "error"; slug?: string; error?: string };
  const [crawlItems, setCrawlItems] = useState<CrawlItem[]>([]);
  const [crawlTotal, setCrawlTotal] = useState(0);
  const [crawlSummary, setCrawlSummary] = useState<{ ingested: number; failed: number } | null>(null);
  const [crawlFatalError, setCrawlFatalError] = useState<string | null>(null);

  async function fetchSources() {
    setLoading(true);
    try {
      const data = await api.listWikiSources();
      setSources(data);
    } catch {
      setError("Failed to load sources.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSources();
  }, []);

  async function handleFiles(files: FileList | File[]) {
    const fileArray = Array.from(files);
    if (fileArray.length === 0) return;

    setUploading(true);
    setError(null);
    setLastResult(null);
    setUploadProgress({ current: 0, total: fileArray.length });

    let lastIngestResult: IngestResult | null = null;
    let hadSuccess = false;

    for (let i = 0; i < fileArray.length; i++) {
      setUploadProgress({ current: i + 1, total: fileArray.length });
      try {
        const result = await api.ingestSource(fileArray[i]);
        lastIngestResult = result;
        if (result.status !== "error") {
          hadSuccess = true;
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Ingest failed.");
        break;
      }
    }

    setLastResult(lastIngestResult);
    if (hadSuccess) {
      await fetchSources();
    }

    setUploading(false);
    setUploadProgress({ current: 0, total: 0 });
  }

  async function handleReset() {
    setResetting(true);
    setConfirmReset(false);
    setLastResult(null);
    setError(null);
    try {
      await api.resetAll();
      await fetchSources();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Reset failed.");
    } finally {
      setResetting(false);
    }
  }

  async function handleDelete(slug: string) {
    setDeleting(slug);
    setConfirmDelete(null);
    try {
      await api.deleteSource(slug);
      await fetchSources();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed.");
    } finally {
      setDeleting(null);
    }
  }

  async function handleCrawl() {
    if (!crawlUrl.trim() || crawling) return;
    setCrawling(true);
    setCrawlItems([]);
    setCrawlTotal(0);
    setCrawlSummary(null);
    setCrawlFatalError(null);
    try {
      await api.crawlAndIngestStream(crawlUrl.trim(), crawlMax, (evt) => {
        if (evt.event === "fatal_error") {
          setCrawlFatalError(evt.error);
        } else if (evt.event === "articles_found") {
          setCrawlTotal(evt.count);
        } else if (evt.event === "article_start") {
          setCrawlItems((prev) => [...prev, { index: evt.index, title: evt.title, url: evt.url, status: "pending" }]);
        } else if (evt.event === "article_done") {
          setCrawlItems((prev) =>
            prev.map((item) =>
              item.index === evt.index
                ? { ...item, status: evt.status, slug: evt.slug, error: evt.error }
                : item
            )
          );
          if (evt.status === "ok") fetchSources();
        } else if (evt.event === "done") {
          setCrawlSummary({ ingested: evt.ingested, failed: evt.failed });
        }
      });
    } catch (e: unknown) {
      setCrawlFatalError(e instanceof Error ? e.message : "Błąd połączenia");
    } finally {
      setCrawling(false);
    }
  }

  const isMultiFile = uploading && uploadProgress.total > 1;

  const sortedSources = [...sources].sort((a, b) => {
    let cmp: number;
    if (sortBy === "title") {
      cmp = a.title.localeCompare(b.title);
    } else {
      cmp = new Date(a.ingested_at).getTime() - new Date(b.ingested_at).getTime();
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  function toggleSort(field: SortBy) {
    if (sortBy === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortDir(field === "title" ? "asc" : "desc");
    }
  }

  const SortButton = ({ field, label }: { field: SortBy; label: string }) => {
    const active = sortBy === field;
    return (
      <button
        onClick={() => toggleSort(field)}
        className={`flex items-center gap-0.5 text-xs transition-colors ${
          active ? "text-foreground font-medium" : "text-muted-foreground hover:text-foreground"
        }`}
        title={`Sortuj wg ${label.toLowerCase()}`}
      >
        {label}
        {active && (sortDir === "asc" ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />)}
      </button>
    );
  };

  return (
    <div className="p-6 h-full flex gap-6">
      {/* Left panel: upload zone + result */}
      <div className="w-80 shrink-0 space-y-4">
        <h2 className="font-semibold text-sm">Ingest New Source</h2>

        {/* Drop zone */}
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            if (e.dataTransfer.files.length > 0) {
              handleFiles(e.dataTransfer.files);
            }
          }}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            dragging
              ? "border-primary bg-primary/5"
              : uploading && !isMultiFile
              ? "border-primary/50 animate-pulse"
              : "border-border hover:border-primary/50"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            multiple
            className="hidden"
            onChange={(e) => {
              if (e.target.files && e.target.files.length > 0) {
                handleFiles(e.target.files);
                // Reset so the same file(s) can be re-selected
                e.target.value = "";
              }
            }}
          />
          <Upload className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
          {uploading ? (
            <p className="text-sm text-muted-foreground">Ingesting…</p>
          ) : (
            <>
              <p className="text-sm font-medium">Drop files or click to ingest</p>
              <p className="text-xs text-muted-foreground mt-1">PDF, DOCX, TXT</p>
            </>
          )}
        </div>

        {/* URL import section */}
        <details className="border border-border rounded-lg overflow-hidden">
          <summary className="px-3 py-2 text-xs font-medium cursor-pointer hover:bg-muted/50 select-none">
            Importuj z URL / bloga
          </summary>
          <div className="px-3 pb-3 pt-2 space-y-2 border-t border-border">
            <input
              type="url"
              placeholder="https://example.com/blog"
              value={crawlUrl}
              onChange={(e) => setCrawlUrl(e.target.value)}
              className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background focus:outline-none focus:ring-1 focus:ring-primary/40"
            />
            <div className="flex items-center gap-2">
              <label className="text-xs text-muted-foreground shrink-0">Maks. artykułów:</label>
              <input
                type="number"
                min={1}
                max={20}
                value={crawlMax}
                onChange={(e) => setCrawlMax(Number(e.target.value))}
                className="w-16 text-xs border border-border rounded px-2 py-1 bg-background"
              />
            </div>
            <button
              onClick={handleCrawl}
              disabled={!crawlUrl.trim() || crawling}
              className="w-full py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50 hover:bg-primary/90 transition-colors"
            >
              {crawling ? "Importuję…" : "Importuj artykuły"}
            </button>
            {/* SSE crawl progress */}
            {(crawlFatalError || crawlItems.length > 0) && (
              <div className="space-y-1.5 mt-1">
                {crawlFatalError && (
                  <p className="text-xs text-red-600">{crawlFatalError}</p>
                )}
                {crawlTotal > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-muted rounded-full h-1 overflow-hidden">
                      <div
                        className="bg-primary h-1 rounded-full transition-all duration-300"
                        style={{ width: `${(crawlItems.filter((i) => i.status !== "pending").length / crawlTotal) * 100}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-muted-foreground shrink-0">
                      {crawlItems.filter((i) => i.status !== "pending").length}/{crawlTotal}
                    </span>
                  </div>
                )}
                <div className="max-h-36 overflow-auto space-y-0.5">
                  {crawlItems.map((item) => (
                    <div key={item.index} className="flex items-center gap-1.5 text-xs py-0.5">
                      {item.status === "pending" ? (
                        <Loader className="w-3 h-3 animate-spin text-muted-foreground shrink-0" />
                      ) : item.status === "ok" ? (
                        <CheckCircle className="w-3 h-3 text-green-500 shrink-0" />
                      ) : (
                        <AlertCircle className="w-3 h-3 text-red-500 shrink-0" title={item.error} />
                      )}
                      <span className="truncate text-muted-foreground">{item.title}</span>
                    </div>
                  ))}
                </div>
                {crawlSummary && (
                  <p className={`text-xs font-medium ${crawlSummary.failed > 0 ? "text-yellow-600" : "text-green-700"}`}>
                    Zaimportowano {crawlSummary.ingested}/{crawlTotal}
                    {crawlSummary.failed > 0 ? ` (${crawlSummary.failed} błędów)` : ""}
                  </p>
                )}
              </div>
            )}
          </div>
        </details>

        {/* Progress bar */}
        {uploading && (
          <>
            <div className="w-full bg-muted rounded-full h-1.5 mt-2 overflow-hidden">
              <div
                className={`bg-primary h-1.5 rounded-full transition-all duration-300 ${isMultiFile ? "" : "animate-pulse"}`}
                style={{ width: isMultiFile ? `${(uploadProgress.current / uploadProgress.total) * 100}%` : "45%" }}
              />
            </div>
            {isMultiFile && (
              <p className="text-xs text-muted-foreground text-center mt-1">
                Ingesting {uploadProgress.current}/{uploadProgress.total}…
              </p>
            )}
          </>
        )}

        {error && (
          <p className="text-xs text-red-500">{error}</p>
        )}

        {lastResult && (
          <div className={`rounded-lg border p-3 text-xs space-y-1 ${
            lastResult.status === "ok"
              ? "border-green-500/40 bg-green-500/5"
              : "border-red-500/40 bg-red-500/5"
          }`}>
            <p className="font-medium">
              {lastResult.status === "ok" ? "Ingested" : "Error"}: {lastResult.slug}
            </p>
            <p>Entities: +{lastResult.entities_created} created, {lastResult.entities_merged} merged</p>
            <p>Concepts: +{lastResult.concepts_created} created, {lastResult.concepts_merged} merged</p>
            <p>Claims: +{lastResult.claims_added} | Edges: +{lastResult.edges_added}</p>
            <p>LLM calls: {lastResult.llm_calls} | {lastResult.duration_ms.toFixed(0)} ms</p>
            {lastResult.conflicts.length > 0 && (
              <p className="text-yellow-600">
                {lastResult.conflicts.length} conflict(s) detected
              </p>
            )}
            {lastResult.error && (
              <p className="text-red-500">{lastResult.error}</p>
            )}
          </div>
        )}
      </div>

      {/* Right panel: sources list */}
      <div className="flex-1 border rounded-lg bg-card border-border overflow-auto p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm">Sources ({sources.length})</h3>
          <div className="flex items-center gap-3">
            {sources.length > 1 && (
              <div className="flex items-center gap-2 border-r border-border pr-3">
                <span className="text-xs text-muted-foreground">Sort:</span>
                <SortButton field="date" label="Data" />
                <SortButton field="title" label="Tytuł" />
              </div>
            )}
            <button
              onClick={fetchSources}
              disabled={loading}
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
              {loading ? "Refreshing…" : "Refresh"}
            </button>
            {confirmReset ? (
              <span className="flex items-center gap-1">
                <span className="text-xs text-red-500 font-medium">Wyczyścić wszystko?</span>
                <button
                  onClick={handleReset}
                  disabled={resetting}
                  className="text-xs text-red-500 hover:text-red-700 font-medium px-1"
                >
                  Tak
                </button>
                <button
                  onClick={() => setConfirmReset(false)}
                  className="text-xs text-muted-foreground hover:text-foreground px-1"
                >
                  Nie
                </button>
              </span>
            ) : (
              <button
                onClick={() => setConfirmReset(true)}
                disabled={resetting || sources.length === 0}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-red-500 transition-colors disabled:opacity-30"
                title="Usuń wszystkie źródła i dane"
              >
                <RotateCcw className={`w-3 h-3 ${resetting ? "animate-spin" : ""}`} />
                Reset
              </button>
            )}
          </div>
        </div>

        {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

        {!loading && sources.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No sources ingested yet. Upload a file to begin.
          </p>
        )}

        <div className="space-y-2">
          {sortedSources.map((src) => (
            <div
              key={src.id}
              className="border border-border rounded-md p-3 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start gap-2">
                <FileText className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium truncate flex-1">{src.title}</p>
                    {confirmDelete === src.slug ? (
                      <span className="flex items-center gap-1 shrink-0">
                        <span className="text-xs text-muted-foreground">Usuń?</span>
                        <button
                          onClick={() => handleDelete(src.slug)}
                          disabled={deleting === src.slug}
                          className="text-xs text-red-500 hover:text-red-700 font-medium px-1"
                        >
                          Tak
                        </button>
                        <button
                          onClick={() => setConfirmDelete(null)}
                          className="text-xs text-muted-foreground hover:text-foreground px-1"
                        >
                          Nie
                        </button>
                      </span>
                    ) : (
                      <button
                        onClick={() => setConfirmDelete(src.slug)}
                        disabled={deleting === src.slug}
                        className="shrink-0 text-muted-foreground hover:text-red-500 transition-colors disabled:opacity-30"
                        title="Usuń źródło"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{src.summary}</p>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    {src.tags.slice(0, 4).map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-0.5 text-xs bg-muted px-1.5 py-0.5 rounded"
                      >
                        <Tag className="w-2.5 h-2.5" />
                        {tag}
                      </span>
                    ))}
                    <span className="flex items-center gap-0.5 text-xs text-muted-foreground ml-auto">
                      <Clock className="w-2.5 h-2.5" />
                      {new Date(src.ingested_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
