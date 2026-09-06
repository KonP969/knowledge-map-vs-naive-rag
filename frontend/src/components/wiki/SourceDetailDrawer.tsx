import { useState } from "react";
import { X, Tag, HelpCircle, Lightbulb, ExternalLink, Clock, FileText } from "lucide-react";
import type { WikiSource } from "../../types";
import { SourceRawModal } from "./SourceRawModal";

interface SourceDetailDrawerProps {
  source: WikiSource | null;
  onClose: () => void;
}

export function SourceDetailDrawer({ source, onClose }: SourceDetailDrawerProps) {
  const [showRaw, setShowRaw] = useState(false);
  if (!source) return null;

  return (
    <div className="w-80 border-l border-border flex flex-col bg-card shrink-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <span className="text-sm font-medium truncate" title={source.title}>
          {source.title}
        </span>
        <button
          onClick={onClose}
          className="ml-2 text-muted-foreground hover:text-foreground transition-colors shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4 flex flex-col gap-4 text-xs">
        {/* Meta */}
        <div className="flex flex-col gap-1.5">
          <span className="flex items-center gap-1.5 text-muted-foreground">
            <Clock className="w-3 h-3 shrink-0" />
            {new Date(source.ingested_at).toLocaleString()}
            <span className="px-1.5 py-0.5 rounded bg-muted text-muted-foreground uppercase text-[10px] ml-1">
              {source.type}
            </span>
          </span>
          {source.source_url && (
            <a
              href={source.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-primary hover:underline truncate"
              title={source.source_url}
            >
              <ExternalLink className="w-3 h-3 shrink-0" />
              <span className="truncate">{source.source_url}</span>
            </a>
          )}
        </div>

        {/* Summary */}
        {source.summary && (
          <p className="leading-relaxed text-foreground">{source.summary}</p>
        )}

        {/* Key takeaways */}
        {source.key_takeaways.length > 0 && (
          <div>
            <div className="flex items-center gap-1 font-medium text-muted-foreground mb-1.5">
              <Lightbulb className="w-3 h-3" />
              Key takeaways
            </div>
            <ul className="space-y-1">
              {source.key_takeaways.map((t, i) => (
                <li key={i} className="text-foreground leading-snug">• {t}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Tags */}
        {source.tags.length > 0 && (
          <div className="flex gap-1.5 flex-wrap">
            {source.tags.map((t) => (
              <span key={t} className="flex items-center gap-1 px-2 py-0.5 rounded bg-muted/50 text-muted-foreground">
                <Tag className="w-2.5 h-2.5" />
                {t}
              </span>
            ))}
          </div>
        )}

        {/* Questions */}
        {source.questions.length > 0 && (
          <div>
            <div className="flex items-center gap-1 font-medium text-muted-foreground mb-1.5">
              <HelpCircle className="w-3 h-3" />
              Questions
            </div>
            <ul className="space-y-1">
              {source.questions.map((q, i) => (
                <li key={i} className="text-muted-foreground leading-snug">• {q}</li>
              ))}
            </ul>
          </div>
        )}

        {source.key_takeaways.length === 0 &&
          source.questions.length === 0 &&
          !source.summary && (
            <p className="text-muted-foreground text-center py-2">No extra details for this source.</p>
          )}

        {/* Raw text */}
        <button
          onClick={() => setShowRaw(true)}
          className="mt-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 transition-opacity"
        >
          <FileText className="w-3.5 h-3.5" />
          Show original
        </button>
      </div>

      {showRaw && (
        <SourceRawModal slug={source.slug} title={source.title} onClose={() => setShowRaw(false)} />
      )}
    </div>
  );
}
