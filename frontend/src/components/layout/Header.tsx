import type { SessionMetrics } from "../../types";

interface HeaderProps {
  metrics: SessionMetrics | null;
}

export function Header({ metrics }: HeaderProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-card px-6">
      <div className="flex items-baseline gap-2">
        <span className="text-sm font-semibold tracking-tight">RAG 2.0</span>
        <span className="text-xs text-muted-foreground">Karpathy Method</span>
      </div>
      {metrics && (
        <div className="flex items-center gap-5 font-mono text-[11px] text-muted-foreground">
          <span>{metrics.total_queries} queries</span>
          <span>{metrics.total_tokens.toLocaleString()} tokens</span>
          <span className="text-foreground">${metrics.total_cost_usd.toFixed(4)}</span>
        </div>
      )}
    </header>
  );
}
