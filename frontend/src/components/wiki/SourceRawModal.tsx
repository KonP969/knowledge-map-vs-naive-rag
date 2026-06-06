import { useEffect, useState } from "react";
import { X, FileText, Loader2 } from "lucide-react";
import { api } from "../../api/client";

interface SourceRawModalProps {
  slug: string;
  title: string;
  onClose: () => void;
}

export function SourceRawModal({ slug, title, onClose }: SourceRawModalProps) {
  const [rawText, setRawText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setRawText(null);
    api
      .getSourceRaw(slug)
      .then((res) => {
        if (!cancelled) setRawText(res.raw_text);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Nie udało się wczytać oryginału");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl max-h-[85vh] flex flex-col rounded-lg border border-border bg-card shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="w-4 h-4 shrink-0 text-muted-foreground" />
            <span className="text-sm font-medium truncate" title={title}>
              {title}
            </span>
            <span className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground uppercase text-[10px] shrink-0">
              Raw text
            </span>
          </div>
          <button
            onClick={onClose}
            className="ml-2 text-muted-foreground hover:text-foreground transition-colors shrink-0"
            aria-label="Zamknij"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-4">
          {loading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground py-8 justify-center">
              <Loader2 className="w-4 h-4 animate-spin" />
              Wczytywanie oryginału…
            </div>
          )}
          {error && !loading && (
            <p className="text-sm text-red-600 dark:text-red-400 py-8 text-center">{error}</p>
          )}
          {rawText !== null && !loading && (
            <pre className="whitespace-pre-wrap break-words text-xs leading-relaxed text-foreground font-mono">
              {rawText}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
