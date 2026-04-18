import type { RetrievedChunk } from "../../types";

interface FootnotesListProps {
  sources: RetrievedChunk[];
}

export function FootnotesList({ sources }: FootnotesListProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-1.5 pt-1.5 border-t border-border/50">
      <p className="text-[10px] text-muted-foreground/60 uppercase tracking-wide mb-1">Źródła</p>
      <div className="space-y-0.5">
        {sources.map((chunk) => (
          <div key={chunk.chunk_id} className="flex items-baseline gap-1.5 text-[11px]">
            <span className="text-primary font-bold shrink-0">{chunk.rank}</span>
            <span className="text-muted-foreground truncate">
              {chunk.document_name || chunk.document_id.slice(0, 12)}
            </span>
            <span className="text-muted-foreground/50 shrink-0">· {chunk.score.toFixed(3)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
