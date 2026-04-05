import { useState, useRef } from "react";
import { Globe, CheckCircle, XCircle, Loader2, StopCircle } from "lucide-react";
import { crawlUrl } from "../../api/client";
import type { CrawlEvent } from "../../api/client";
import type { DocumentMeta } from "../../types";

interface Props {
  onDocumentsAdded: (docs: DocumentMeta[]) => void;
}

interface LogEntry {
  type: "ok" | "error" | "info";
  label: string;
  url?: string;
}

export function CrawlPanel({ onDocumentsAdded }: Props) {
  const [url, setUrl] = useState("");
  const [maxArticles, setMaxArticles] = useState(50);
  const [running, setRunning] = useState(false);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);
  const abortRef = useRef<(() => void) | null>(null);
  const addedDocsRef = useRef<DocumentMeta[]>([]);

  function start() {
    if (!url.trim()) return;
    setLog([{ type: "info", label: `Szukam artykułów na ${url}…` }]);
    setProgress(null);
    setRunning(true);
    addedDocsRef.current = [];

    abortRef.current = crawlUrl(
      url.trim(),
      maxArticles,
      (event: CrawlEvent) => {
        if (event.type === "start") {
          setProgress({ current: 0, total: event.total! });
          setLog((prev) => [
            ...prev,
            { type: "info", label: `Znaleziono ${event.total} artykułów. Pobieranie…` },
          ]);
        } else if (event.type === "article") {
          setProgress({ current: event.current!, total: event.total! });
          const meta: DocumentMeta = {
            id: event.doc_id!,
            name: event.title!,
            size_bytes: 0,
            page_count: null,
            upload_date: new Date().toISOString(),
            char_count: 0,
          };
          addedDocsRef.current = [...addedDocsRef.current, meta];
          setLog((prev) => [
            ...prev,
            { type: "ok", label: event.title!, url: event.url },
          ]);
        } else if (event.type === "error") {
          setProgress((p) => p ? { ...p, current: event.current! } : null);
          setLog((prev) => [
            ...prev,
            { type: "error", label: event.url ?? "unknown", url: event.url },
          ]);
        } else if (event.type === "error_fatal") {
          setLog((prev) => [
            ...prev,
            { type: "error", label: event.message ?? "Błąd krytyczny" },
          ]);
        } else if (event.type === "done") {
          setLog((prev) => [
            ...prev,
            {
              type: "info",
              label: `Gotowe — dodano ${event.added} artykułów, błędy: ${event.failed}`,
            },
          ]);
          onDocumentsAdded(addedDocsRef.current);
        }
      },
      () => setRunning(false),
    );
  }

  function stop() {
    abortRef.current?.();
    setRunning(false);
    setLog((prev) => [...prev, { type: "info", label: "Przerwano przez użytkownika." }]);
    onDocumentsAdded(addedDocsRef.current);
  }

  const pct = progress ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <label className="text-xs font-medium text-muted-foreground">URL bloga</label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Globe className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-muted-foreground" />
            <input
              type="url"
              placeholder="https://twoj-blog.pl"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={running}
              className="w-full pl-8 pr-3 py-2 text-sm border rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs text-muted-foreground whitespace-nowrap">
            Max artykułów: <span className="font-medium text-foreground">{maxArticles}</span>
          </label>
          <input
            type="range"
            min={5}
            max={200}
            step={5}
            value={maxArticles}
            onChange={(e) => setMaxArticles(Number(e.target.value))}
            disabled={running}
            className="flex-1"
          />
        </div>
      </div>

      <div className="flex gap-2">
        {!running ? (
          <button
            onClick={start}
            disabled={!url.trim()}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Globe className="w-3.5 h-3.5" />
            Crawl
          </button>
        ) : (
          <button
            onClick={stop}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors"
          >
            <StopCircle className="w-3.5 h-3.5" />
            Stop
          </button>
        )}
      </div>

      {progress && (
        <div className="space-y-1">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{progress.current} / {progress.total}</span>
            <span>{pct}%</span>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300 rounded-full"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {log.length > 0 && (
        <div className="border rounded-md bg-zinc-950 p-3 max-h-56 overflow-y-auto space-y-1">
          {log.map((entry, i) => (
            <div key={i} className="flex items-start gap-1.5 text-xs">
              {entry.type === "ok" && <CheckCircle className="w-3 h-3 text-green-400 mt-0.5 shrink-0" />}
              {entry.type === "error" && <XCircle className="w-3 h-3 text-red-400 mt-0.5 shrink-0" />}
              {entry.type === "info" && <Loader2 className={`w-3 h-3 text-zinc-400 mt-0.5 shrink-0 ${running && i === log.length - 1 ? "animate-spin" : ""}`} />}
              <span className={
                entry.type === "ok" ? "text-green-300" :
                entry.type === "error" ? "text-red-300" :
                "text-zinc-400"
              }>
                {entry.label}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
