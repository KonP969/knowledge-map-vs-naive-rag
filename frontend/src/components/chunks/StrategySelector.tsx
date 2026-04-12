import type { ChunkRequest } from "../../types";

interface StrategySelectorProps {
  value: ChunkRequest;
  onChange: (v: ChunkRequest) => void;
  documentId: string;
}

export function StrategySelector({ value, onChange, documentId }: StrategySelectorProps) {
  const strategies = [
    { id: "fixed" as const, label: "Fixed Size" },
    { id: "recursive" as const, label: "Recursive" },
    { id: "semantic" as const, label: "Semantic" },
  ];

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Strategy</label>
        <div className="flex gap-2 mt-1.5">
          {strategies.map((s) => (
            <button
              key={s.id}
              onClick={() => onChange({ ...value, strategy: s.id, document_id: documentId })}
              className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                value.strategy === s.id
                  ? "border-primary bg-primary text-white"
                  : "border-border hover:border-primary/50"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {(value.strategy === "fixed" || value.strategy === "recursive") && (
        <>
          <div>
            <label className="text-xs font-medium text-muted-foreground">
              Chunk Size: <strong>{value.chunk_size}</strong> chars
            </label>
            <input
              type="range" min={100} max={2000} step={50}
              value={value.chunk_size ?? 500}
              onChange={(e) => onChange({ ...value, chunk_size: Number(e.target.value) })}
              className="w-full mt-1"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">
              Overlap: <strong>{value.overlap}</strong> chars
            </label>
            <input
              type="range" min={0} max={200} step={10}
              value={value.overlap ?? 50}
              onChange={(e) => onChange({ ...value, overlap: Number(e.target.value) })}
              className="w-full mt-1"
            />
          </div>
        </>
      )}
    </div>
  );
}
