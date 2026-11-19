import { HelpCircle } from "lucide-react";
import type { SessionMetrics } from "../../types";

interface HeaderProps {
  metrics: SessionMetrics | null;
  onStartTour?: () => void;
}

export function Header({ metrics, onStartTour }: HeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-card px-4 md:px-6">
      <div className="flex items-baseline gap-2">
        <span className="text-sm font-semibold tracking-tight">Knowledge-Map RAG</span>
        <span className="hidden text-xs text-muted-foreground sm:inline">vs naive RAG</span>
      </div>
      <div className="flex items-center gap-5">
        {metrics && (
          <div className="hidden items-center gap-5 font-mono text-[11px] tabular-nums text-muted-foreground md:flex">
            <span>{metrics.total_queries} {metrics.total_queries === 1 ? "query" : "queries"}</span>
            <span>{metrics.total_tokens.toLocaleString()} tokens</span>
            <span className="text-foreground">${metrics.total_cost_usd.toFixed(4)}</span>
          </div>
        )}
        {onStartTour && (
          <button
            onClick={onStartTour}
            className="flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
            title="Take the tour"
          >
            <HelpCircle className="h-3.5 w-3.5" />
            Tour
          </button>
        )}
      </div>
    </header>
  );
}
