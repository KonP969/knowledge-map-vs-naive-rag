interface KBHProps {
  totalDocs: number;
  embeddedDocs: number;
  totalChunks: number;
  totalChars: number;
}

function CircularGauge({
  value,
  max,
  label,
  sublabel,
  color = "hsl(188 95% 52%)",
}: {
  value: number;
  max: number;
  label: string;
  sublabel: string;
  color?: string;
}) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const pct = max > 0 ? Math.min(value / max, 1) : 0;
  const offset = circumference * (1 - pct);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-24 h-24">
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 88 88">
          <circle
            cx="44" cy="44" r={radius}
            fill="none"
            stroke="hsl(220 15% 22%)"
            strokeWidth="8"
          />
          <circle
            cx="44" cy="44" r={radius}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.5s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-sm font-bold text-foreground">{label}</span>
          <span className="text-xs text-muted-foreground">{sublabel}</span>
        </div>
      </div>
    </div>
  );
}

function formatChars(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return `${n}`;
}

export function KnowledgeBaseHealth({ totalDocs, embeddedDocs, totalChunks, totalChars }: KBHProps) {
  const embeddedPct = totalDocs > 0 ? Math.round((embeddedDocs / totalDocs) * 100) : 0;

  return (
    <div className="border border-border rounded-lg bg-card p-4 space-y-4">
      <h3 className="text-sm font-semibold text-foreground">Knowledge Base</h3>

      <div className="flex justify-around">
        <CircularGauge
          value={embeddedDocs}
          max={totalDocs}
          label={`${embeddedPct}%`}
          sublabel="embedded"
        />
        <CircularGauge
          value={totalChunks}
          max={Math.max(totalChunks, 1)}
          label={`${totalChunks}`}
          sublabel="chunks"
          color="hsl(270 70% 65%)"
        />
      </div>

      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border">
        {[
          { label: "Total Docs", value: totalDocs },
          { label: "Embedded", value: embeddedDocs },
          { label: "Chars", value: formatChars(totalChars) },
        ].map(({ label, value }) => (
          <div key={label} className="text-center">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-sm font-semibold text-foreground">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
