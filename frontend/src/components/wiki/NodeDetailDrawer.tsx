import { useEffect, useState } from "react";
import { X, Tag, HelpCircle, FileText, Link2 } from "lucide-react";
import { api } from "../../api/client";
import type { NodeDetail } from "../../types";

const POLARITY_COLOR: Record<string, string> = {
  asserts: "text-green-600",
  denies: "text-red-600",
};

interface NodeDetailDrawerProps {
  nodeId: string | null;
  onClose: () => void;
}

export function NodeDetailDrawer({ nodeId, onClose }: NodeDetailDrawerProps) {
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!nodeId) return;
    setDetail(null);
    setError(null);
    setLoading(true);
    api
      .getWikiNodeDetail(nodeId)
      .then(setDetail)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [nodeId]);

  if (!nodeId) return null;

  return (
    <div className="w-72 border-l border-border flex flex-col bg-card shrink-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <span className="text-sm font-medium truncate">
          {loading ? "Loading…" : (detail?.title ?? nodeId)}
        </span>
        <button
          onClick={onClose}
          className="ml-2 text-muted-foreground hover:text-foreground transition-colors shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {loading && (
        <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">
          Loading…
        </div>
      )}

      {error && (
        <div className="flex-1 flex items-center justify-center text-xs text-red-500 p-4 text-center">
          {error}
        </div>
      )}

      {detail && !loading && (
        <div className="flex-1 overflow-auto p-4 flex flex-col gap-4 text-xs">
          {/* Type badges */}
          <div className="flex gap-1.5 flex-wrap">
            <span className="px-2 py-0.5 rounded bg-muted text-muted-foreground capitalize font-medium">
              {detail.node_type}
              {detail.entity_type ? ` · ${detail.entity_type}` : ""}
            </span>
            {detail.tags?.map((t) => (
              <span key={t} className="flex items-center gap-1 px-2 py-0.5 rounded bg-muted/50 text-muted-foreground">
                <Tag className="w-2.5 h-2.5" />
                {t}
              </span>
            ))}
          </div>

          {/* Aliases (entities only) */}
          {detail.aliases && detail.aliases.length > 0 && (
            <p className="text-muted-foreground">
              Also: {detail.aliases.join(", ")}
            </p>
          )}

          {/* Description */}
          {detail.description && (
            <p className="leading-relaxed text-foreground">{detail.description}</p>
          )}

          {/* Questions */}
          {detail.questions && detail.questions.length > 0 && (
            <div>
              <div className="flex items-center gap-1 font-medium text-muted-foreground mb-1.5">
                <HelpCircle className="w-3 h-3" />
                Questions
              </div>
              <ul className="space-y-1">
                {detail.questions.slice(0, 5).map((q, i) => (
                  <li key={i} className="text-muted-foreground leading-snug">
                    • {q}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Claims */}
          {detail.claims.length > 0 && (
            <div>
              <div className="flex items-center gap-1 font-medium text-muted-foreground mb-1.5">
                <FileText className="w-3 h-3" />
                Claims ({detail.claims.length})
              </div>
              <ul className="space-y-2">
                {detail.claims.slice(0, 6).map((c) => (
                  <li key={c.id} className="border border-border rounded p-2 space-y-1">
                    <p className="text-foreground leading-snug">{c.text}</p>
                    <p className={`${POLARITY_COLOR[c.polarity] ?? "text-muted-foreground"}`}>
                      {c.polarity} · {(c.confidence * 100).toFixed(0)}%
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Edges */}
          {detail.edges.length > 0 && (
            <div>
              <div className="flex items-center gap-1 font-medium text-muted-foreground mb-1.5">
                <Link2 className="w-3 h-3" />
                Relations ({detail.edges.length})
              </div>
              <ul className="space-y-1.5">
                {detail.edges.slice(0, 8).map((e) => {
                  const isFrom = e.from === nodeId;
                  const other = isFrom ? e.to : e.from;
                  const arrow = isFrom ? "→" : "←";
                  return (
                    <li key={e.id} className="text-muted-foreground leading-snug">
                      <span className="text-foreground font-medium">{arrow} {e.relation}</span>{" "}
                      <span className="font-mono">{other}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {detail.claims.length === 0 && detail.edges.length === 0 && (
            <p className="text-muted-foreground text-center py-2">No claims or relations yet.</p>
          )}
        </div>
      )}
    </div>
  );
}
