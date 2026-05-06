import { useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge as RFEdge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api } from "../../api/client";
import type { WikiEntity, WikiConcept, WikiSource, WikiEdge } from "../../types";

const NODE_W = 140;
const NODE_H = 36;

const ENTITY_COLORS: Record<string, string> = {
  Person: "#3b82f6",
  Org: "#10b981",
  Product: "#f97316",
  Place: "#ef4444",
  Event: "#8b5cf6",
};

function radialLayout(nodes: Node[]): Node[] {
  const entities = nodes.filter((n) => n.id.startsWith("entity:"));
  const concepts = nodes.filter((n) => n.id.startsWith("concept:"));
  const sources = nodes.filter((n) => n.id.startsWith("source:"));

  function ring(items: Node[], radius: number): Node[] {
    return items.map((n, i) => {
      const angle = (2 * Math.PI * i) / Math.max(items.length, 1) - Math.PI / 2;
      return { ...n, position: { x: radius * Math.cos(angle), y: radius * Math.sin(angle) } };
    });
  }

  return [
    ...ring(concepts, 160),
    ...ring(entities, 360),
    ...ring(sources, 580),
  ];
}

function buildNodeStyle(color: string, shape: "round" | "rect" | "pill") {
  const radius = shape === "round" ? 18 : shape === "pill" ? 6 : 4;
  return {
    background: color,
    color: "#fff",
    borderRadius: radius,
    fontSize: 10,
    width: NODE_W,
    height: NODE_H,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "0 8px",
    cursor: "pointer",
    border: "none",
    boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
  };
}

const ENTITY_TYPES = ["Person", "Org", "Product", "Place", "Event"] as const;

interface FilterState {
  showEntities: boolean;
  showConcepts: boolean;
  showSources: boolean;
  entityTypes: Set<string>;
}

interface GraphViewProps {
  onNodeClick: (nodeId: string) => void;
}

export function GraphView({ onNodeClick }: GraphViewProps) {
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState([]);
  const [entities, setEntities] = useState<WikiEntity[]>([]);
  const [concepts, setConcepts] = useState<WikiConcept[]>([]);
  const [sources, setSources] = useState<WikiSource[]>([]);
  const [wikiEdges, setWikiEdges] = useState<WikiEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<FilterState>({
    showEntities: true,
    showConcepts: true,
    showSources: true,
    entityTypes: new Set(ENTITY_TYPES),
  });

  useEffect(() => {
    Promise.all([
      api.listWikiEntities(),
      api.listWikiConcepts(),
      api.listWikiSources(),
      api.listWikiEdges(),
    ])
      .then(([e, c, s, ed]) => {
        setEntities(e);
        setConcepts(c);
        setSources(s);
        setWikiEdges(ed);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (loading) return;

    const rawNodes: Node[] = [];

    if (filters.showEntities) {
      entities
        .filter((e) => filters.entityTypes.has(e.type))
        .forEach((e) => {
          rawNodes.push({
            id: `entity:${e.id}`,
            data: { label: e.slug },
            position: { x: 0, y: 0 },
            style: buildNodeStyle(ENTITY_COLORS[e.type] ?? "#3b82f6", "rect"),
          });
        });
    }

    if (filters.showConcepts) {
      concepts.forEach((c) => {
        rawNodes.push({
          id: `concept:${c.id}`,
          data: { label: c.slug },
          position: { x: 0, y: 0 },
          style: buildNodeStyle("#f59e0b", "pill"),
        });
      });
    }

    if (filters.showSources) {
      sources.forEach((s) => {
        rawNodes.push({
          id: `source:${s.id}`,
          data: { label: s.title.length > 18 ? s.title.slice(0, 18) + "…" : s.title },
          position: { x: 0, y: 0 },
          style: buildNodeStyle("#6b7280", "round"),
        });
      });
    }

    const nodeIdSet = new Set(rawNodes.map((n) => n.id));

    const rawEdges: RFEdge[] = wikiEdges
      .filter((e) => nodeIdSet.has(e.from) && nodeIdSet.has(e.to))
      .map((e) => ({
        id: e.id,
        source: e.from,
        target: e.to,
        label: e.relation,
        style: { stroke: "#94a3b8", strokeWidth: 1 },
        labelStyle: { fontSize: 8, fill: "#94a3b8" },
        labelBgStyle: { fill: "transparent" },
        animated: false,
      }));

    setRfNodes(radialLayout(rawNodes));
    setRfEdges(rawEdges);
  }, [entities, concepts, sources, wikiEdges, filters, loading]);

  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => onNodeClick(node.id),
    [onNodeClick],
  );

  const toggleEntityType = (t: string) =>
    setFilters((f) => {
      const next = new Set(f.entityTypes);
      next.has(t) ? next.delete(t) : next.add(t);
      return { ...f, entityTypes: next };
    });

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
        Loading graph…
      </div>
    );
  }

  if (rfNodes.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
        No nodes to display. Ingest some sources first.
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Filter bar */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border flex-wrap shrink-0">
        {(["Entities", "Concepts", "Sources"] as const).map((label) => {
          const key = `show${label}` as keyof FilterState;
          const on = filters[key] as boolean;
          return (
            <button
              key={label}
              onClick={() => setFilters((f) => ({ ...f, [key]: !on }))}
              className={`px-2 py-0.5 rounded text-xs transition-colors ${
                on
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {label}
            </button>
          );
        })}
        <span className="text-muted-foreground text-xs">|</span>
        {ENTITY_TYPES.map((t) => {
          const on = filters.entityTypes.has(t);
          return (
            <button
              key={t}
              onClick={() => toggleEntityType(t)}
              className={`px-2 py-0.5 rounded text-xs transition-colors ${
                on
                  ? "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {t}
            </button>
          );
        })}
        <span className="ml-auto text-xs text-muted-foreground">
          {rfNodes.length} nodes · {rfEdges.length} edges
        </span>
      </div>

      {/* Canvas */}
      <div className="flex-1">
        <ReactFlow
          nodes={rfNodes}
          edges={rfEdges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          fitView
          minZoom={0.1}
          maxZoom={3}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#e2e8f0" gap={20} />
          <Controls />
          <MiniMap nodeStrokeWidth={3} pannable zoomable />
        </ReactFlow>
      </div>
    </div>
  );
}
