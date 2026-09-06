import { HelpCircle } from "lucide-react";
import type { SessionMetrics } from "../../types";

interface HeaderProps {
  metrics: SessionMetrics | null;
  onStartTour?: () => void;
}

export function Header({ metrics, onStartTour }: HeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-card px-6">
      <div className="flex items-baseline gap-2">
        <span className="text-sm font-semibold tracking-tight">RAG 2.0</span>
        <span className="text-xs text-muted-foreground">Karpathy Method</span>
      </div>
      <div className="flex items-center gap-5">
        {metrics && (
          <div className="flex items-center gap-5 font-mono text-[11px] text-muted-foreground">
            <span>{metrics.total_queries} queries</span>
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
