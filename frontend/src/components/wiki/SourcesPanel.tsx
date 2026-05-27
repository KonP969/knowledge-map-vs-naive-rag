import { useState, useEffect, useRef } from "react";
import { Upload, RefreshCw, FileText, Tag, Clock } from "lucide-react";
import { api } from "../../api/client";
import type { WikiSource, IngestResult } from "../../types";

export function SourcesPanel() {
  const [sources, setSources] = useState<WikiSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ current: number; total: number }>({ current: 0, total: 0 });
  const [lastResult, setLastResult] = useState<IngestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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

  const isMultiFile = uploading && uploadProgress.total > 1;

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

        {/* Multi-file progress bar */}
        {isMultiFile && (
          <>
            <div className="w-full bg-muted rounded-full h-1.5 mt-2">
              <div
                className="bg-primary h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground text-center mt-1">
              Ingesting {uploadProgress.current}/{uploadProgress.total}…
            </p>
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
          <button
            onClick={fetchSources}
            disabled={loading}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>

        {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

        {!loading && sources.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No sources ingested yet. Upload a file to begin.
          </p>
        )}

        <div className="space-y-2">
          {sources.map((src) => (
            <div
              key={src.id}
              className="border border-border rounded-md p-3 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start gap-2">
                <FileText className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{src.title}</p>
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
