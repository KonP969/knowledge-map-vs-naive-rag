import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Node,
  type Edge as RFEdge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Search, X, User, Building, Package, MapPin, Calendar, Lightbulb } from "lucide-react";
import { api } from "../../api/client";
import type { WikiEntity, WikiConcept, WikiSource, WikiEdge } from "../../types";

const ENTITY_ICONS: Record<string, React.ElementType> = {
  Person: User, Org: Building, Product: Package, Place: MapPin, Event: Calendar,
};

type GraphSearchResult = { nodeId: string; label: string; type: string; Icon: React.ElementType };

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

function GraphAutoFocus({ selectedNodeId, nodes }: { selectedNodeId: string | null | undefined; nodes: Node[] }) {
  const { setCenter } = useReactFlow();
  useEffect(() => {
    if (!selectedNodeId) return;
    const node = nodes.find((n) => n.id === selectedNodeId);
    if (!node) return;
    setCenter(node.position.x + NODE_W / 2, node.position.y + NODE_H / 2, { zoom: 1.5, duration: 600 });
  }, [selectedNodeId, nodes, setCenter]);
  return null;
}

interface GraphViewProps {
  onNodeClick: (nodeId: string) => void;
  selectedNodeId?: string | null;
}

export function GraphView({ onNodeClick, selectedNodeId }: GraphViewProps) {
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
  const [graphSearch, setGraphSearch] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

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

  // Derived nodes/edges with selection highlighting
  const displayNodes = useMemo(() => {
    if (!selectedNodeId) return rfNodes;

    const connectedNodeIds = new Set<string>();
    rfEdges.forEach((e) => {
      if (e.source === selectedNodeId) connectedNodeIds.add(e.target);
      if (e.target === selectedNodeId) connectedNodeIds.add(e.source);
    });

    return rfNodes.map((n) => {
      if (n.id === selectedNodeId || connectedNodeIds.has(n.id)) {
        return n; // keep fully visible
      }
      return { ...n, style: { ...(n.style as object), opacity: 0.3 } };
    });
  }, [rfNodes, rfEdges, selectedNodeId]);

  const displayEdges = useMemo(() => {
    if (!selectedNodeId) return rfEdges;

    return rfEdges.map((e) => {
      const connected = e.source === selectedNodeId || e.target === selectedNodeId;
      return connected
        ? { ...e, style: { stroke: "#3b82f6", strokeWidth: 2, opacity: 1 } }
        : { ...e, style: { opacity: 0.15 } };
    });
  }, [rfEdges, selectedNodeId]);

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

  function resetFilters() {
    setFilters({
      showEntities: true,
      showConcepts: true,
      showSources: true,
      entityTypes: new Set(ENTITY_TYPES),
    });
  }

  const totalData = entities.length + concepts.length + sources.length;

  const searchResults: GraphSearchResult[] = (() => {
    const gq = graphSearch.toLowerCase();
    if (!gq) return [];
    const results: GraphSearchResult[] = [];
    for (const e of entities) {
      if (results.length >= 8) break;
      if (!e.slug.includes(gq) && !e.aliases.some((a) => a.toLowerCase().includes(gq))) continue;
      results.push({ nodeId: `entity:${e.id}`, label: e.slug, type: e.type, Icon: ENTITY_ICONS[e.type] ?? User });
    }
    for (const c of concepts) {
      if (results.length >= 8) break;
      if (!c.slug.includes(gq)) continue;
      results.push({ nodeId: `concept:${c.id}`, label: c.slug, type: "Concept", Icon: Lightbulb });
    }
    for (const s of sources) {
      if (results.length >= 8) break;
      if (!s.title.toLowerCase().includes(gq)) continue;
      results.push({ nodeId: `source:${s.id}`, label: s.title, type: "Source", Icon: Package });
    }
    return results;
  })();

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
        Loading graph…
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Filter bar — always rendered so filters stay accessible */}
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
        {/* Legend */}
        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground border-l border-border pl-2 ml-1">
          <span className="w-2.5 h-2.5 rounded-sm inline-block shrink-0" style={{ background: "#f59e0b" }} />Concept
          <span className="w-2.5 h-2.5 rounded-sm inline-block shrink-0 ml-1" style={{ background: "#3b82f6" }} />Person
          <span className="w-2.5 h-2.5 rounded-sm inline-block shrink-0" style={{ background: "#10b981" }} />Org
          <span className="w-2.5 h-2.5 rounded-sm inline-block shrink-0" style={{ background: "#f97316" }} />Product
          <span className="w-2.5 h-2.5 rounded-full inline-block shrink-0 ml-1" style={{ background: "#6b7280" }} />Source
        </div>

        {/* Node search */}
        <div className="relative border-l border-border pl-2 ml-1 shrink-0">
          <div className="flex items-center border border-border rounded-md bg-background">
            <Search className="w-3 h-3 text-muted-foreground ml-1.5 shrink-0" />
            <input
              ref={searchInputRef}
              value={graphSearch}
              onChange={(e) => { setGraphSearch(e.target.value); setDropdownOpen(true); }}
              onFocus={() => setDropdownOpen(true)}
              onBlur={() => setTimeout(() => setDropdownOpen(false), 150)}
              placeholder="Search nodes…"
              className="px-1.5 py-1 text-[11px] bg-transparent focus:outline-none w-28"
            />
            {graphSearch && (
              <button onClick={() => { setGraphSearch(""); setDropdownOpen(false); searchInputRef.current?.focus(); }} className="px-1 text-muted-foreground hover:text-foreground">
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
          {dropdownOpen && graphSearch.length > 0 && (
            <div className="absolute right-0 top-full mt-1 w-72 bg-popover border border-border rounded-md shadow-lg z-50 overflow-hidden">
              {searchResults.length === 0 ? (
                <p className="px-3 py-2 text-xs text-muted-foreground">Brak wyników dla «{graphSearch}»</p>
              ) : (
                searchResults.map((r) => (
                  <button
                    key={r.nodeId}
                    onMouseDown={() => { onNodeClick(r.nodeId); setGraphSearch(""); setDropdownOpen(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-muted transition-colors text-left"
                  >
                    <r.Icon className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                    <span className="flex-1 truncate font-medium">{r.label}</span>
                    <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded shrink-0">{r.type}</span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Canvas or empty state */}
      {rfNodes.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-sm text-muted-foreground">
          {totalData === 0 ? (
            <p>Brak danych. Dodaj źródła w panelu Sources.</p>
          ) : (
            <>
              <p>Wszystkie filtry wyłączone — brak węzłów do wyświetlenia.</p>
              <button
                onClick={resetFilters}
                className="text-xs text-primary hover:underline"
              >
                Włącz wszystkie filtry
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="flex-1">
          <ReactFlow
            nodes={displayNodes}
            edges={displayEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            fitView
            minZoom={0.1}
            maxZoom={3}
            proOptions={{ hideAttribution: true }}
          >
            <GraphAutoFocus selectedNodeId={selectedNodeId} nodes={rfNodes} />
            <Background color="#e2e8f0" gap={20} />
            <Controls />
            <MiniMap nodeStrokeWidth={3} pannable zoomable />
          </ReactFlow>
        </div>
      )}
    </div>
  );
}
