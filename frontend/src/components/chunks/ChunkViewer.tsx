import type { Chunk, ChunkStats } from "../../types";

interface ChunkViewerProps {
  chunks: Chunk[];
  stats: ChunkStats | null;
}

export function ChunkViewer({ chunks, stats }: ChunkViewerProps) {
  if (chunks.length === 0) {
    return <p className="text-sm text-muted-foreground">No chunks generated yet.</p>;
  }

  const COLORS = [
    "bg-primary/20 border border-primary/30",
    "bg-success/15 border border-success/25",
    "bg-warning/15 border border-warning/25",
    "bg-purple-500/15 border border-purple-500/25",
    "bg-pink-500/15 border border-pink-500/25",
  ];

  return (
    <div className="space-y-4">
      {stats && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Count", value: stats.count },
            { label: "Avg length", value: `${stats.avg_length.toFixed(0)} chars` },
            { label: "Min / Max", value: `${stats.min_length} / ${stats.max_length}` },
            { label: "Overlap", value: `${stats.overlap_pct}%` },
          ].map(({ label, value }) => (
            <div key={label} className="border border-border rounded-lg p-3 bg-card text-center">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-sm font-semibold mt-0.5 text-foreground">{value}</p>
            </div>
          ))}
        </div>
      )}
      <div className="space-y-2 max-h-[500px] overflow-auto">
        {chunks.map((chunk, i) => (
          <div key={chunk.id} className={`rounded-lg p-3 ${COLORS[i % COLORS.length]}`}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground">
                Chunk {chunk.index + 1}
              </span>
              <span className="text-xs text-muted-foreground">
                {chunk.char_count} chars · {chunk.token_count} tokens
              </span>
            </div>
            <p className="text-xs leading-relaxed text-foreground">{chunk.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
