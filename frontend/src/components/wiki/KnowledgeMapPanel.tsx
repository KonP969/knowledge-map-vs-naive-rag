import { useState, useEffect } from "react";
import { RefreshCw, Search, User, Building, Package, MapPin, Calendar, Lightbulb } from "lucide-react";
import { api } from "../../api/client";
import type { WikiEntity, WikiConcept, WikiSource } from "../../types";
import { GraphView } from "./GraphView";
import { NodeDetailDrawer } from "./NodeDetailDrawer";

type View = "graph" | "browser";
type BrowserTab = "entities" | "concepts" | "sources";

const ENTITY_TYPE_ICONS: Record<string, React.ElementType> = {
  Person: User,
  Org: Building,
  Product: Package,
  Place: MapPin,
  Event: Calendar,
};

export function KnowledgeMapPanel() {
  const [view, setView] = useState<View>("graph");
  const [browserTab, setBrowserTab] = useState<BrowserTab>("entities");
  const [entities, setEntities] = useState<WikiEntity[]>([]);
  const [concepts, setConcepts] = useState<WikiConcept[]>([]);
  const [sources, setSources] = useState<WikiSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  async function fetchAll() {
    setLoading(true);
    try {
      const [e, c, s] = await Promise.all([
        api.listWikiEntities(),
        api.listWikiConcepts(),
        api.listWikiSources(),
      ]);
      setEntities(e);
      setConcepts(c);
      setSources(s);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchAll(); }, []);

  const q = search.toLowerCase();

  const filteredEntities = entities.filter(
    (e) =>
      !q ||
      e.slug.includes(q) ||
      e.type.toLowerCase().includes(q) ||
      e.description.toLowerCase().includes(q) ||
      e.aliases.some((a) => a.toLowerCase().includes(q)),
  );

  const filteredConcepts = concepts.filter(
    (c) => !q || c.slug.includes(q) || c.definition.toLowerCase().includes(q),
  );

  const filteredSources = sources.filter(
    (s) =>
      !q ||
      s.title.toLowerCase().includes(q) ||
      s.summary.toLowerCase().includes(q) ||
      s.tags.some((t) => t.includes(q)),
  );

  const browserTabs: { id: BrowserTab; label: string; count: number }[] = [
    { id: "entities", label: "Entities", count: entities.length },
    { id: "concepts", label: "Concepts", count: concepts.length },
    { id: "sources", label: "Sources", count: sources.length },
  ];

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border shrink-0">
        {/* View toggle */}
        <div className="flex gap-1">
          {(["graph", "browser"] as View[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-1.5 text-xs rounded-md capitalize transition-colors ${
                view === v
                  ? "bg-primary text-primary-foreground font-medium"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              {v}
            </button>
          ))}
        </div>

        {/* Browser-only controls */}
        {view === "browser" && (
          <>
            <div className="flex gap-1">
              {browserTabs.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setBrowserTab(t.id)}
                  className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                    browserTab === t.id
                      ? "bg-primary/10 text-primary font-medium"
                      : "bg-muted text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {t.label} ({t.count})
                </button>
              ))}
            </div>
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter…"
                className="w-full pl-7 pr-3 py-1.5 text-xs border border-border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-primary/40"
              />
            </div>
          </>
        )}

        <button
          onClick={fetchAll}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors ml-auto"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Content */}
      {view === "graph" ? (
        <div className="flex-1 flex overflow-hidden">
          <GraphView onNodeClick={setSelectedNodeId} selectedNodeId={selectedNodeId} />
          <NodeDetailDrawer
            nodeId={selectedNodeId}
            onClose={() => setSelectedNodeId(null)}
          />
        </div>
      ) : (
        <div className="flex-1 border-t border-border bg-card overflow-auto">
          {browserTab === "entities" && (
            <table className="w-full text-xs">
              <thead className="border-b border-border sticky top-0 bg-card">
                <tr>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Type</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Slug</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Description</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Aliases</th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">ID</th>
                </tr>
              </thead>
              <tbody>
                {filteredEntities.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                      {entities.length === 0 ? "No entities ingested yet." : "No matches."}
                    </td>
                  </tr>
                )}
                {filteredEntities.map((e) => {
                  const Icon = ENTITY_TYPE_ICONS[e.type] ?? User;
                  return (
                    <tr key={e.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                      <td className="px-3 py-2">
                        <span className="flex items-center gap-1">
                          <Icon className="w-3 h-3" />
                          {e.type}
                        </span>
                      </td>
                      <td className="px-3 py-2 font-mono">{e.slug}</td>
                      <td className="px-3 py-2 max-w-xs truncate text-muted-foreground">{e.description}</td>
                      <td className="px-3 py-2 text-muted-foreground">{e.aliases.slice(0, 3).join(", ")}</td>
                      <td className="px-3 py-2 text-right font-mono text-muted-foreground">{e.id}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}

          {browserTab === "concepts" && (
            <table className="w-full text-xs">
              <thead className="border-b border-border sticky top-0 bg-card">
                <tr>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Slug</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Definition</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Tags</th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">ID</th>
                </tr>
              </thead>
              <tbody>
                {filteredConcepts.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-3 py-6 text-center text-muted-foreground">
                      {concepts.length === 0 ? "No concepts ingested yet." : "No matches."}
                    </td>
                  </tr>
                )}
                {filteredConcepts.map((c) => (
                  <tr key={c.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                    <td className="px-3 py-2 font-mono">
                      <span className="flex items-center gap-1">
                        <Lightbulb className="w-3 h-3 text-yellow-500" />
                        {c.slug}
                      </span>
                    </td>
                    <td className="px-3 py-2 max-w-xs truncate text-muted-foreground">{c.definition}</td>
                    <td className="px-3 py-2 text-muted-foreground">{c.tags.slice(0, 4).join(", ")}</td>
                    <td className="px-3 py-2 text-right font-mono text-muted-foreground">{c.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {browserTab === "sources" && (
            <table className="w-full text-xs">
              <thead className="border-b border-border sticky top-0 bg-card">
                <tr>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Title</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Summary</th>
                  <th className="text-left px-3 py-2 font-medium text-muted-foreground">Tags</th>
                  <th className="text-right px-3 py-2 font-medium text-muted-foreground">ID</th>
                </tr>
              </thead>
              <tbody>
                {filteredSources.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-3 py-6 text-center text-muted-foreground">
                      {sources.length === 0 ? "No sources ingested yet." : "No matches."}
                    </td>
                  </tr>
                )}
                {filteredSources.map((s) => (
                  <tr key={s.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                    <td className="px-3 py-2 font-medium truncate max-w-[180px]">{s.title}</td>
                    <td className="px-3 py-2 max-w-xs truncate text-muted-foreground">{s.summary}</td>
                    <td className="px-3 py-2 text-muted-foreground">{s.tags.slice(0, 4).join(", ")}</td>
                    <td className="px-3 py-2 text-right font-mono text-muted-foreground">{s.id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
