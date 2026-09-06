import { useEffect, useRef, useState } from "react";
import { X, FileText, Loader2 } from "lucide-react";
import { api } from "../../api/client";

interface RawHighlight {
  start: number;
  end: number;
  text: string;
}

interface SourceRawModalProps {
  slug: string;
  title: string;
  onClose: () => void;
  highlight?: RawHighlight;
}

// Locate the fragment to highlight: trust the offsets when they actually match the
// verbatim text, otherwise fall back to searching for the literal text (offsets can
// drift if the raw file was re-parsed). Returns null when nothing matches.
function resolveHighlightRange(raw: string, hl: RawHighlight): { start: number; end: number } | null {
  if (raw.slice(hl.start, hl.end) === hl.text && hl.text.length > 0) {
    return { start: hl.start, end: hl.end };
  }
  if (hl.text) {
    const idx = raw.indexOf(hl.text);
    if (idx >= 0) return { start: idx, end: idx + hl.text.length };
  }
  return null;
}

export function SourceRawModal({ slug, title, onClose, highlight }: SourceRawModalProps) {
  const [rawText, setRawText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const markRef = useRef<HTMLElement>(null);

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
        if (!cancelled) setError(e instanceof Error ? e.message : "Couldn't load the original");
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

  // Scroll the highlighted fragment into view once the text is rendered
  useEffect(() => {
    if (rawText !== null && highlight && markRef.current) {
      markRef.current.scrollIntoView({ block: "center" });
    }
  }, [rawText, highlight]);

  const range = rawText !== null && highlight ? resolveHighlightRange(rawText, highlight) : null;

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
              Loading the original…
            </div>
          )}
          {error && !loading && (
            <p className="text-sm text-red-600 dark:text-red-400 py-8 text-center">{error}</p>
          )}
          {rawText !== null && !loading && (
            <pre className="whitespace-pre-wrap break-words text-xs leading-relaxed text-foreground font-mono">
              {range ? (
                <>
                  {rawText.slice(0, range.start)}
                  <mark
                    ref={markRef}
                    className="bg-primary/25 text-foreground rounded-sm px-0.5"
                  >
                    {rawText.slice(range.start, range.end)}
                  </mark>
                  {rawText.slice(range.end)}
                </>
              ) : (
                rawText
              )}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
