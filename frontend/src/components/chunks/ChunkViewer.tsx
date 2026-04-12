import type { Chunk, ChunkStats } from "../../types";

interface ChunkViewerProps {
  chunks: Chunk[];
  stats: ChunkStats | null;
}

export function ChunkViewer({ chunks, stats }: ChunkViewerProps) {
  if (chunks.length === 0) {
    return <p className="text-sm text-muted-foreground">No chunks generated yet.</p>;
  }

  const COLORS = ["bg-blue-100", "bg-green-100", "bg-yellow-100", "bg-purple-100", "bg-pink-100"];

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
            <div key={label} className="border rounded-lg p-3 bg-white text-center">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-sm font-semibold mt-0.5">{value}</p>
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
            <p className="text-xs leading-relaxed">{chunk.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
