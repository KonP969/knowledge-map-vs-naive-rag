import type { ChunkRequest } from "../../types";

interface StrategySelectorProps {
  value: ChunkRequest;
  onChange: (v: ChunkRequest) => void;
  documentId: string;
}

const STRATEGY_INFO = {
  fixed: {
    label: "Fixed Size",
    description: "Dzieli tekst na równe fragmenty o zadanej liczbie znaków z zachowaniem overlap.",
    when: "Dobra dla dokumentów o równomiernej gęstości informacji: raporty, artykuły, transkrypcje.",
  },
  recursive: {
    label: "Recursive",
    description: "Próbuje dzielić po naturalnych granicach: akapity → zdania → słowa.",
    when: "Dobra dla dokumentów z wyraźną strukturą: dokumentacja, tutoriale, README.",
  },
  semantic: {
    label: "Semantic",
    description: "Grupuje zdania o zbliżonej tematyce w jeden chunk. Najwolniejsza, najlepsza jakość semantyczna.",
    when: "Dobra gdy treść jest zróżnicowana i zależy Ci na spójności znaczeniowej chunków.",
  },
} as const;

export function StrategySelector({ value, onChange, documentId }: StrategySelectorProps) {
  const strategies = (["fixed", "recursive", "semantic"] as const);

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Strategy
        </label>
        <div className="flex gap-2 mt-1.5">
          {strategies.map((id) => {
            const info = STRATEGY_INFO[id];
            return (
              <div key={id} className="relative group">
                <button
                  type="button"
                  onClick={() => onChange({ ...value, strategy: id, document_id: documentId })}
                  className={`px-3 py-1.5 text-xs rounded-md border transition-colors ${
                    value.strategy === id
                      ? "border-primary bg-primary text-white"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  {info.label}
                </button>

                {/* Tooltip */}
                <div className="absolute bottom-full left-0 mb-2 z-50 w-52 p-2.5 bg-card border border-border rounded-lg shadow-xl invisible group-hover:visible pointer-events-none">
                  <p className="text-[11px] font-semibold text-foreground mb-1">
                    {info.label}
                  </p>
                  <p className="text-[11px] text-muted-foreground leading-relaxed mb-1.5">
                    {info.description}
                  </p>
                  <p className="text-[11px] text-primary/80 leading-relaxed">
                    {info.when}
                  </p>
                </div>
              </div>
            );
          })}
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
