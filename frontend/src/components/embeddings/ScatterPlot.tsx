import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { EmbeddingPoint } from "../../types";

const COLORS = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899"];

interface ScatterPlotProps {
  points: EmbeddingPoint[];
  selectedA: string | null;
  selectedB: string | null;
  onSelect: (id: string) => void;
}

function getDocColor(docId: string, allDocIds: string[]): string {
  const idx = allDocIds.indexOf(docId);
  return COLORS[idx % COLORS.length];
}

interface TooltipPayloadItem {
  payload: EmbeddingPoint;
}

export function ScatterPlot({ points, selectedA, selectedB, onSelect }: ScatterPlotProps) {
  const docIds = [...new Set(points.map((p) => p.document_id))];
  const docNames = Object.fromEntries(points.map((p) => [p.document_id, p.document_name]));

  if (points.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 border rounded-lg bg-white">
        <p className="text-sm text-muted-foreground">Generate embeddings to see the visualization.</p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg bg-white p-4">
      <ResponsiveContainer width="100%" height={350}>
        <ScatterChart>
          <XAxis dataKey="x" type="number" domain={["auto", "auto"]} tick={{ fontSize: 10 }} />
          <YAxis dataKey="y" type="number" domain={["auto", "auto"]} tick={{ fontSize: 10 }} />
          <Tooltip
            content={({ payload }) => {
              const item = (payload as unknown as TooltipPayloadItem[] | undefined)?.[0];
              if (!item) return null;
              const p = item.payload;
              return (
                <div className="bg-white border rounded shadow-sm p-2 max-w-xs">
                  <p className="text-xs font-medium truncate">{p.content_preview}</p>
                  <p className="text-xs text-muted-foreground">Doc: {p.document_name}</p>
                </div>
              );
            }}
          />
          <Scatter
            data={points}
            onClick={(d: unknown) => onSelect((d as EmbeddingPoint).chunk_id)}
          >
            {points.map((p) => (
              <Cell
                key={p.chunk_id}
                fill={getDocColor(p.document_id, docIds)}
                opacity={selectedA === p.chunk_id || selectedB === p.chunk_id ? 1 : 0.7}
                stroke={selectedA === p.chunk_id || selectedB === p.chunk_id ? "#1e40af" : "none"}
                strokeWidth={2}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
      <div className="flex gap-4 mt-2 flex-wrap">
        {docIds.map((id, i) => (
          <div key={id} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
            <span className="text-xs text-muted-foreground truncate max-w-[160px]" title={docNames[id]}>{docNames[id]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
