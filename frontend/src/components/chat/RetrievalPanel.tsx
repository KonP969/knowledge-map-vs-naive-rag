import { RetrievedChunk } from "../../types";

interface RetrievalPanelProps {
  chunks: RetrievedChunk[];
  topK: number;
  onTopKChange: (k: number) => void;
}

export function RetrievalPanel({ chunks, topK, onTopKChange }: RetrievalPanelProps) {
  return (
    <div className="border rounded-lg bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Retrieved Chunks</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">top-k:</span>
          <input
            type="number" min={1} max={20} value={topK}
            onChange={(e) => onTopKChange(Number(e.target.value))}
            className="w-12 text-xs border border-border rounded px-1.5 py-0.5 text-center"
          />
        </div>
      </div>

      {chunks.length === 0 ? (
        <p className="text-xs text-muted-foreground">Ask a question to see retrieved chunks.</p>
      ) : (
        <div className="space-y-2 max-h-[300px] overflow-auto">
          {chunks.map((chunk) => (
            <div key={chunk.chunk_id} className="border border-border rounded p-2">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">#{chunk.rank}</span>
                <span className="text-xs font-medium text-primary">
                  score: {chunk.score.toFixed(4)}
                </span>
              </div>
              <p className="text-xs leading-relaxed line-clamp-3">{chunk.content}</p>
              <p className="text-xs text-muted-foreground mt-1">
                doc: {chunk.document_name || chunk.document_id.slice(0, 8)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
