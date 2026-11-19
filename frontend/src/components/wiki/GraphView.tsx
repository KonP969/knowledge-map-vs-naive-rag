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
import {
  forceSimulation, forceLink, forceManyBody, forceCollide, forceX, forceY,
  type SimulationNodeDatum,
} from "d3-force";
import { Search, X, User, Building, Package, MapPin, Calendar, Lightbulb } from "lucide-react";
import { api } from "../../api/client";
import type { WikiEntity, WikiConcept, WikiSource, WikiEdge } from "../../types";

const ENTITY_ICONS: Record<string, React.ElementType> = {
  Person: User, Org: Building, Product: Package, Place: MapPin, Event: Calendar,
};

type GraphSearchResult = { nodeId: string; label: string; type: string; Icon: React.ElementType };

const NODE_W = 140;
const NODE_H = 36;

// A calm categorical set that sits on the graphite ground without competing with
// the UI's single orange accent. Concept (usually the largest group) is the
// quietest; sources are near-neutral containers.
const ENTITY_COLORS: Record<string, string> = {
  Person: "#c98f6b",
  Org: "#6fa98f",
  Product: "#9b8bc4",
  Place: "#b76d6d",
  Event: "#b5a05c",
};
const CONCEPT_COLOR = "#6b8cae";
const SOURCE_COLOR = "#565963";

// Position nodes with a force simulation so connected nodes cluster and nothing
// overlaps. Seeded by type (sources up top, entities mid, concepts below) to keep
// the layout roughly stable and readable, then relaxed by the forces.
function forceLayout(nodes: Node[], edges: RFEdge[]): Node[] {
  type SimNode = SimulationNodeDatum & { id: string; band: number };
  const bandOf = (id: string) => (id.startsWith("source:") ? -1 : id.startsWith("entity:") ? 0 : 1);

  const sim: SimNode[] = nodes.map((n, i) => ({
    id: n.id,
    band: bandOf(n.id),
    x: (i % 20) * 60 - 600 + (Math.random() - 0.5) * 40,
    y: bandOf(n.id) * 260 + (Math.random() - 0.5) * 40,
  }));
  const links = edges.map((e) => ({ source: e.source, target: e.target }));

  forceSimulation(sim)
    .force("link", forceLink(links).id((d) => (d as SimNode).id).distance(120).strength(0.28))
    .force("charge", forceManyBody().strength(-520))
    .force("collide", forceCollide(NODE_W / 2 + 12))
    .force("x", forceX(0).strength(0.05))
    .force("y", forceY<SimNode>((d) => d.band * 200).strength(0.06))
    .stop()
    .tick(440);

  const pos = new Map(sim.map((s) => [s.id, s]));
  return nodes.map((n) => {
    const p = pos.get(n.id);
    return { ...n, position: { x: (p?.x ?? 0) - NODE_W / 2, y: (p?.y ?? 0) - NODE_H / 2 } };
  });
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
  /** null = decide by graph size (hide only in large graphs) */
  showMinorConcepts: boolean | null;
  entityTypes: Set<string>;
}

const SELECT_COLOR = "#FF7A2F"; // the UI accent: selection is a live state
const LARGE_GRAPH = 150; // nodes; above this, minor concepts start hidden

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
  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<Node>([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<RFEdge>([]);
  const [entities, setEntities] = useState<WikiEntity[]>([]);
  const [concepts, setConcepts] = useState<WikiConcept[]>([]);
  const [sources, setSources] = useState<WikiSource[]>([]);
  const [wikiEdges, setWikiEdges] = useState<WikiEdge[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<FilterState>({
    showEntities: true,
    showConcepts: true,
    showSources: true,
    showMinorConcepts: null,
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

  // A concept wired to a single node or source is detail, not structure. With the
  // resolver creating a node for every claim subject these outnumber everything
  // else, so they start hidden.
  const minorConceptIds = useMemo(() => {
    const degree = new Map<string, number>();
    wikiEdges.forEach((e) => {
      degree.set(e.from, (degree.get(e.from) ?? 0) + 1);
      degree.set(e.to, (degree.get(e.to) ?? 0) + 1);
    });
    return new Set(
      concepts.map((c) => `concept:${c.id}`).filter((id) => (degree.get(id) ?? 0) <= 1),
    );
  }, [concepts, wikiEdges]);
  // Small graphs stay complete; the cut only pays off once the map gets crowded.
  const showMinor =
    filters.showMinorConcepts ?? entities.length + concepts.length + sources.length <= LARGE_GRAPH;
  // A hidden node that something asks to focus (search, lint, a citation) is shown anyway.
  const forcedNodeId =
    selectedNodeId && minorConceptIds.has(selectedNodeId) && !showMinor
      ? selectedNodeId
      : null;

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
            style: buildNodeStyle(ENTITY_COLORS[e.type] ?? "#c98f6b", "rect"),
          });
        });
    }

    if (filters.showConcepts) {
      concepts
        .filter((c) => showMinor || !minorConceptIds.has(`concept:${c.id}`)
          || `concept:${c.id}` === forcedNodeId)
        .forEach((c) => {
        rawNodes.push({
          id: `concept:${c.id}`,
          data: { label: c.slug },
          position: { x: 0, y: 0 },
          style: buildNodeStyle(CONCEPT_COLOR, "pill"),
        });
      });
    }

    if (filters.showSources) {
      sources.forEach((s) => {
        rawNodes.push({
          id: `source:${s.id}`,
          data: { label: s.title.length > 18 ? s.title.slice(0, 18) + "…" : s.title },
          position: { x: 0, y: 0 },
          style: buildNodeStyle(SOURCE_COLOR, "round"),
        });
      });
    }

    const nodeIdSet = new Set(rawNodes.map((n) => n.id));

    // Relation labels are kept on the edge data but not painted here — with
    // hundreds of edges they turn the canvas to fog. displayEdges shows the
    // label only for the currently selected node's edges.
    const rawEdges: RFEdge[] = wikiEdges
      .filter((e) => nodeIdSet.has(e.from) && nodeIdSet.has(e.to))
      .map((e) => ({
        id: e.id,
        source: e.from,
        target: e.to,
        data: { relation: e.relation },
        style: { stroke: "#94a3b8", strokeWidth: 1, opacity: 0.35 },
        animated: false,
      }));

    setRfNodes(forceLayout(rawNodes, rawEdges));
    setRfEdges(rawEdges);
  }, [entities, concepts, sources, wikiEdges, filters, loading, minorConceptIds, forcedNodeId, showMinor]);

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
        ? {
            ...e,
            label: (e.data as { relation?: string })?.relation,
            labelStyle: { fontSize: 9, fill: SELECT_COLOR },
            labelBgStyle: { fill: "#0b0e14", fillOpacity: 0.85 },
            style: { stroke: SELECT_COLOR, strokeWidth: 2, opacity: 1 },
          }
        : { ...e, style: { stroke: "#94a3b8", strokeWidth: 1, opacity: 0.08 } };
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
      showMinorConcepts: true,
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
        Loading the graph…
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
              aria-pressed={on}
              className={`px-2 py-0.5 rounded border text-xs transition-colors ${
                on
                  ? "border-primary/50 text-foreground"
                  : "border-transparent bg-muted text-muted-foreground"
              }`}
            >
              {t}
            </button>
          );
        })}
        {minorConceptIds.size > 0 && filters.showConcepts && (
          <>
            <span className="text-muted-foreground text-xs">|</span>
            <button
              onClick={() => setFilters((f) => ({ ...f, showMinorConcepts: !showMinor }))}
              aria-pressed={showMinor}
              title="Concepts linked to a single node or source. Hidden by default to keep the map readable."
              className={`px-2 py-0.5 rounded border text-xs transition-colors ${
                showMinor
                  ? "border-primary/50 text-foreground"
                  : "border-transparent bg-muted text-muted-foreground"
              }`}
            >
              {showMinor ? "Hide" : "Show"} {minorConceptIds.size} minor concepts
            </button>
          </>
        )}
        <span className="ml-auto text-xs tabular-nums text-muted-foreground">
          {rfNodes.length} nodes · {rfEdges.length} edges
        </span>
        {/* Legend */}
        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground border-l border-border pl-2 ml-1">
          <span className="w-2.5 h-2.5 rounded-sm inline-block shrink-0" style={{ background: CONCEPT_COLOR }} />Concept
          <span className="w-2.5 h-2.5 rounded-sm inline-block shrink-0 ml-1" style={{ background: ENTITY_COLORS.Person }} />Person
          <span className="w-2.5 h-2.5 rounded-sm inline-block shrink-0" style={{ background: ENTITY_COLORS.Org }} />Org
          <span className="w-2.5 h-2.5 rounded-sm inline-block shrink-0" style={{ background: ENTITY_COLORS.Product }} />Product
          <span className="w-2.5 h-2.5 rounded-full inline-block shrink-0 ml-1" style={{ background: SOURCE_COLOR }} />Source
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
                <p className="px-3 py-2 text-xs text-muted-foreground">No nodes match “{graphSearch}”</p>
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
            <p>No graph yet. Add sources in the Sources panel.</p>
          ) : (
            <>
              <p>Every filter is off — nothing to show.</p>
              <button
                onClick={resetFilters}
                className="text-xs text-primary hover:underline"
              >
                Turn all filters on
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
            colorMode="dark"
            minZoom={0.1}
            maxZoom={3}
            proOptions={{ hideAttribution: true }}
          >
            <GraphAutoFocus selectedNodeId={selectedNodeId} nodes={rfNodes} />
            <Background color="#33343A" gap={20} />
            <Controls />
            <MiniMap nodeStrokeWidth={3} pannable zoomable bgColor="#202227" maskColor="rgba(23,24,28,0.7)" />
          </ReactFlow>
        </div>
      )}
    </div>
  );
}
