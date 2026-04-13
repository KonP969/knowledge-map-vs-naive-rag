import { useState, useEffect } from "react";
import type { SessionMetrics } from "../../types";
import { api } from "../../api/client";

export function MetricsPanel() {
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    api.getSessionMetrics().then(setMetrics).catch(console.error);
  }, []);

  async function handleReset() {
    if (!confirm("Reset all data (documents, chunks, embeddings, metrics)?")) return;
    setResetting(true);
    try {
      await api.resetAll();
      setMetrics(null);
      window.location.reload();
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-sm text-foreground">Metrics & Logs</h2>
        <button
          onClick={handleReset}
          disabled={resetting}
          className="text-xs px-3 py-1.5 border border-error/50 text-error rounded-md hover:bg-error/10 disabled:opacity-50 transition-colors"
        >
          {resetting ? "Resetting..." : "Clear All Data"}
        </button>
      </div>

      {metrics ? (
        <>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Total Queries", value: metrics.total_queries },
              { label: "Total Tokens", value: metrics.total_tokens.toLocaleString() },
              { label: "Total Cost", value: `$${metrics.total_cost_usd.toFixed(4)}` },
            ].map(({ label, value }) => (
              <div key={label} className="border border-border rounded-lg p-4 bg-card text-center">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="text-xl font-semibold mt-1 text-foreground">{value}</p>
              </div>
            ))}
          </div>

          <div className="border border-border rounded-lg bg-card overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-muted/60">
                <tr>
                  {["Query", "Embed ms", "Retrieval ms", "LLM ms", "Tokens", "Cost"].map((h) => (
                    <th key={h} className="text-left px-3 py-2 text-muted-foreground font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metrics.queries.map((q) => (
                  <tr key={q.query_id} className="border-t border-border hover:bg-muted/30 transition-colors">
                    <td className="px-3 py-2 max-w-[180px] truncate text-foreground">{q.query}</td>
                    <td className="px-3 py-2 text-muted-foreground">{q.embedding_ms.toFixed(0)}</td>
                    <td className="px-3 py-2 text-muted-foreground">{q.retrieval_ms.toFixed(0)}</td>
                    <td className="px-3 py-2 text-muted-foreground">{q.llm_ms.toFixed(0)}</td>
                    <td className="px-3 py-2 text-muted-foreground">{q.total_tokens}</td>
                    <td className="px-3 py-2 text-muted-foreground">${q.estimated_cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {metrics.queries.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-4">No queries yet.</p>
            )}
          </div>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">Loading metrics...</p>
      )}
    </div>
  );
}
