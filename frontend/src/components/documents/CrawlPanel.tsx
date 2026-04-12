import { useState, useRef } from "react";
import { Globe, CheckCircle, XCircle, Loader2, StopCircle, AlertCircle } from "lucide-react";
import { crawlUrl } from "../../api/client";
import type { CrawlEvent } from "../../api/client";
import type { DocumentMeta } from "../../types";

interface Props {
  onDocumentsAdded: (docs: DocumentMeta[]) => void;
}

interface ArticleEntry {
  title: string;
  url: string;
  docId: string;
}

interface ErrorEntry {
  url: string;
}

export function CrawlPanel({ onDocumentsAdded }: Props) {
  const [url, setUrl] = useState("");
  const [maxArticles, setMaxArticles] = useState(50);
  const [running, setRunning] = useState(false);
  const [status, setStatus] = useState<"idle" | "connecting" | "running" | "done" | "error">("idle");
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);
  const [articles, setArticles] = useState<ArticleEntry[]>([]);
  const [errors, setErrors] = useState<ErrorEntry[]>([]);
  const [fatalMessage, setFatalMessage] = useState<string | null>(null);
  const abortRef = useRef<(() => void) | null>(null);
  const addedDocsRef = useRef<DocumentMeta[]>([]);

  function start() {
    if (!url.trim()) return;
    setStatus("connecting");
    setRunning(true);
    setProgress(null);
    setArticles([]);
    setErrors([]);
    setFatalMessage(null);
    addedDocsRef.current = [];

    abortRef.current = crawlUrl(
      url.trim(),
      maxArticles,
      (event: CrawlEvent) => {
        if (event.type === "connecting") {
          setStatus("connecting");
        } else if (event.type === "start") {
          setStatus("running");
          setProgress({ current: 0, total: event.total! });
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
          setArticles((prev) => [...prev, { title: event.title!, url: event.url!, docId: event.doc_id! }]);
        } else if (event.type === "error") {
          setProgress((p) => p ? { ...p, current: event.current! } : null);
          setErrors((prev) => [...prev, { url: event.url ?? "unknown" }]);
        } else if (event.type === "error_fatal") {
          setFatalMessage(event.message ?? "Błąd krytyczny");
          setStatus("error");
        } else if (event.type === "done") {
          setStatus("done");
          onDocumentsAdded(addedDocsRef.current);
        }
      },
      () => setRunning(false),
    );
  }

  function stop() {
    abortRef.current?.();
    setRunning(false);
    setStatus("done");
    onDocumentsAdded(addedDocsRef.current);
  }

  const pct = progress ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <div className="space-y-3">
      {/* URL + controls */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-muted-foreground">URL bloga</label>
        <div className="relative">
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
        <div className="flex items-center gap-3">
          <label className="text-xs text-muted-foreground whitespace-nowrap">
            Max artykułów: <span className="font-medium text-foreground">{maxArticles}</span>
          </label>
          <input
            type="range" min={5} max={200} step={5} value={maxArticles}
            onChange={(e) => setMaxArticles(Number(e.target.value))}
            disabled={running}
            className="flex-1"
          />
        </div>
      </div>

      {/* Action button */}
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

      {/* Connecting state */}
      {status === "connecting" && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          Szukam artykułów na stronie…
        </div>
      )}

      {/* Fatal error */}
      {status === "error" && fatalMessage && (
        <div className="flex items-start gap-2 text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded-md p-2">
          <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
          {fatalMessage}
        </div>
      )}

      {/* Progress bar + counters */}
      {progress && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1 text-green-600 font-medium">
                <CheckCircle className="w-3 h-3" />
                {articles.length} dodano
              </span>
              {errors.length > 0 && (
                <span className="flex items-center gap-1 text-red-500">
                  <XCircle className="w-3 h-3" />
                  {errors.length} błędów
                </span>
              )}
            </div>
            <span className="text-muted-foreground">
              {progress.current} / {progress.total} · {pct}%
            </span>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300 rounded-full"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* Done summary */}
      {status === "done" && articles.length > 0 && (
        <div className="text-xs text-muted-foreground">
          Zakończono — <span className="text-green-600 font-medium">{articles.length} artykułów</span> dodano
          {errors.length > 0 && <>, <span className="text-red-500">{errors.length} nie udało się</span></>}.
        </div>
      )}

      {/* Article list */}
      {articles.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Pobrane artykuły</p>
          <div className="border rounded-md divide-y max-h-52 overflow-y-auto">
            {articles.map((a) => (
              <div key={a.docId} className="flex items-start gap-2 px-2.5 py-1.5">
                <CheckCircle className="w-3 h-3 text-green-500 mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <p className="text-xs font-medium truncate">{a.title}</p>
                  <p className="text-xs text-muted-foreground truncate">{a.url}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error list */}
      {errors.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-red-500">Nieudane ({errors.length})</p>
          <div className="border border-red-200 rounded-md divide-y divide-red-100 max-h-28 overflow-y-auto">
            {errors.map((e, i) => (
              <div key={i} className="flex items-start gap-2 px-2.5 py-1.5">
                <XCircle className="w-3 h-3 text-red-400 mt-0.5 shrink-0" />
                <p className="text-xs text-muted-foreground truncate">{e.url}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
