import { Brain } from "lucide-react";
import type { SessionMetrics } from "../../types";

interface HeaderProps {
  metrics: SessionMetrics | null;
}

export function Header({ metrics }: HeaderProps) {
  return (
    <header className="h-14 border-b border-border bg-card flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-2">
        <Brain className="w-5 h-5 text-primary" />
        <span className="font-semibold text-sm">RAG Learning Lab</span>
      </div>
      {metrics && (
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>Queries: <strong className="text-foreground">{metrics.total_queries}</strong></span>
          <span>Tokens: <strong className="text-foreground">{metrics.total_tokens.toLocaleString()}</strong></span>
          <span>Cost: <strong className="text-foreground">${metrics.total_cost_usd.toFixed(4)}</strong></span>
        </div>
      )}
    </header>
  );
}
