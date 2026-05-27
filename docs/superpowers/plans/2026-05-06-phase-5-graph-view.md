# Phase 5 — Graph View Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Graph tab to KnowledgeMapPanel that renders entities, concepts, and sources as an interactive node-link diagram using react-flow, with a NodeDetailDrawer that slides in when a node is clicked.

**Architecture:** Backend gains two new endpoints — `GET /api/wiki/edges` (graph connections from `edges.jsonl`) and `GET /api/wiki/node-detail?id=<prefixed-id>` (full node data + claims + edges for the drawer). Frontend installs `@xyflow/react` (react-flow v12) and renders nodes via a radial layout: concepts in the center ring, entities in the middle ring, sources on the outer ring. KnowledgeMapPanel is restructured from 3 browser tabs to a "Graph" / "Browser" top-level toggle; the browser keeps its 3 sub-tabs unchanged. The NodeDetailDrawer is a slide-in panel alongside the graph canvas.

**Tech Stack:** Python 3.9, FastAPI, `@xyflow/react` (react-flow v12), React 19, TypeScript, Tailwind CSS, lucide-react, pytest.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/api/wiki.py` | Add `GET /api/wiki/edges` and `GET /api/wiki/node-detail` endpoints |
| Modify | `backend/tests/api/test_wiki_api.py` | Tests for both new endpoints |
| Modify | `frontend/src/types/index.ts` | Add `WikiEdge`, `NodeDetail`, `NodeDetailClaim`, `NodeDetailEdge` types |
| Modify | `frontend/src/api/client.ts` | Add `api.listWikiEdges()` and `api.getWikiNodeDetail()` |
| Create | `frontend/src/components/wiki/GraphView.tsx` | React Flow canvas with radial layout, filter bar, node click handler |
| Create | `frontend/src/components/wiki/NodeDetailDrawer.tsx` | Slide-in drawer showing node metadata + claims + edges |
| Modify | `frontend/src/components/wiki/KnowledgeMapPanel.tsx` | Restructure: Graph/Browser toggle, integrate GraphView + NodeDetailDrawer |

---

## Task 1: Backend — edges and node-detail endpoints

**Files:**
- Modify: `backend/api/wiki.py`
- Modify: `backend/tests/api/test_wiki_api.py`

- [ ] **Step 1: Write failing tests**

Add to the bottom of `backend/tests/api/test_wiki_api.py`:

```python
def test_get_wiki_edges_returns_list(client):
    response = client.get("/api/wiki/edges")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_wiki_edges_shape(client, tmp_path):
    from unittest.mock import patch
    from models.wiki_models import Edge, Span

    store = WikiStore(root=tmp_path)
    edge = Edge(
        id="edge_001", **{"from": "entity:e_001"},
        to="concept:c_001", relation="associated_with",
        source_id="src_001",
        span=Span(start=0, end=10, text="bedroom"),
        confidence=0.8,
    )
    store.append_edge(edge)

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/edges")

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "edge_001"
    assert data[0]["from"] == "entity:e_001"
    assert data[0]["to"] == "concept:c_001"
    assert data[0]["relation"] == "associated_with"
    assert data[0]["confidence"] == 0.8


def test_get_wiki_node_detail_invalid_id_returns_400(client):
    response = client.get("/api/wiki/node-detail?id=invalidnoprefix")
    assert response.status_code == 400


def test_get_wiki_node_detail_entity(client, tmp_path):
    from unittest.mock import patch
    from datetime import datetime
    from models.wiki_models import Entity, Source
    from services.wiki_index import regenerate_index

    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="T", type="txt",
        raw_path="r/x.md", ingested_at=datetime(2026, 5, 1),
        summary="S", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, slug="test-source")
    entity = Entity(
        id="e_001", type="Place", aliases=["room"],
        description="A room.", mentions_count=1,
        questions=["q?"], tags=["space"],
    )
    store.write_entity(entity, slug="test-room")
    regenerate_index(store)

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/node-detail?id=entity:e_001")

    assert response.status_code == 200
    data = response.json()
    assert data["node_type"] == "entity"
    assert data["entity_type"] == "Place"
    assert data["description"] == "A room."
    assert isinstance(data["claims"], list)
    assert isinstance(data["edges"], list)


def test_get_wiki_node_detail_concept(client, tmp_path):
    from unittest.mock import patch
    from datetime import datetime
    from models.wiki_models import Concept, Source
    from services.wiki_index import regenerate_index

    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="T", type="txt",
        raw_path="r/x.md", ingested_at=datetime(2026, 5, 1),
        summary="S", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, slug="test-source")
    concept = Concept(
        id="c_001", definition="Neutral colors palette.",
        examples=[], related=[], questions=["What?"], tags=["color"],
    )
    store.write_concept(concept, slug="neutral-palette")
    regenerate_index(store)

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/node-detail?id=concept:c_001")

    assert response.status_code == 200
    data = response.json()
    assert data["node_type"] == "concept"
    assert "neutral" in data["description"].lower()
    assert isinstance(data["claims"], list)
    assert isinstance(data["edges"], list)


def test_get_wiki_node_detail_includes_claims_and_edges(client, tmp_path):
    from unittest.mock import patch
    from datetime import datetime
    from models.wiki_models import Entity, Source, Claim, Edge, Span
    from services.wiki_index import regenerate_index

    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="T", type="txt",
        raw_path="r/x.md", ingested_at=datetime(2026, 5, 1),
        summary="S", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, slug="test-source")
    entity = Entity(
        id="e_001", type="Place", aliases=[],
        description="A room.", mentions_count=1,
        questions=[], tags=[],
    )
    store.write_entity(entity, slug="test-room")
    claim = Claim(
        id="cl_001", text="Room is neutral.",
        subject_id="entity:e_001", source_id="src_001",
        span=Span(start=0, end=14, text="Room is neutral."),
        confidence=0.9, polarity="asserts",
    )
    store.append_claim(claim)
    edge = Edge(
        id="edge_001", **{"from": "entity:e_001"},
        to="concept:c_001", relation="associated_with",
        source_id="src_001",
        span=Span(start=0, end=5, text="room"),
        confidence=0.8,
    )
    store.append_edge(edge)
    regenerate_index(store)

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/node-detail?id=entity:e_001")

    data = response.json()
    assert len(data["claims"]) == 1
    assert data["claims"][0]["id"] == "cl_001"
    assert len(data["edges"]) == 1
    assert data["edges"][0]["id"] == "edge_001"
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend && python -m pytest tests/api/test_wiki_api.py -v -k "edges or node_detail"
```
Expected: 6 FAILED — routes `/api/wiki/edges` and `/api/wiki/node-detail` not yet defined.

- [ ] **Step 3: Add both endpoints to `backend/api/wiki.py`**

Add these imports at the top of the file:
```python
import json as _json
from fastapi import HTTPException
from typing import Optional
```

Then append to the end of `backend/api/wiki.py`:

```python
@router.get("/edges", response_model=List[Dict[str, Any]])
def list_wiki_edges():
    store = _get_store()
    return [
        {
            "id": e.id,
            "from": e.from_,
            "to": e.to,
            "relation": e.relation,
            "source_id": e.source_id,
            "confidence": e.confidence,
        }
        for e in store.read_all_edges()
    ]


@router.get("/node-detail", response_model=Dict[str, Any])
def get_wiki_node_detail(id: str):
    """
    id format: "entity:e_001", "concept:c_001", "source:src_001"
    Returns node metadata + up to 20 claims + up to 20 edges for the drawer.
    """
    store = _get_store()
    if ":" not in id:
        raise HTTPException(status_code=400, detail="id must be prefixed: entity:, concept:, or source:")

    prefix, inner_id = id.split(":", 1)

    claims = [
        {
            "id": c.id, "text": c.text, "confidence": c.confidence,
            "polarity": c.polarity, "source_id": c.source_id,
        }
        for c in store.read_all_claims()
        if c.subject_id == id or (prefix == "source" and c.source_id == inner_id)
    ][:20]

    edges = [
        {
            "id": e.id, "from": e.from_, "to": e.to,
            "relation": e.relation, "source_id": e.source_id,
        }
        for e in store.read_all_edges()
        if e.from_ == id or e.to == id
    ][:20]

    base: Dict[str, Any] = {"id": id, "node_type": prefix, "claims": claims, "edges": edges}

    index_path = store.root / "wiki" / "00-Index" / "index.json"

    if prefix == "entity" and index_path.exists():
        idx = _json.loads(index_path.read_text(encoding="utf-8"))
        entry = next((e for e in idx.get("entities", []) if e.get("id") == inner_id), None)
        if entry:
            entity = store.read_entity(entry["slug"], entry["type"])
            if entity:
                base.update({
                    "slug": entry["slug"],
                    "title": entry["slug"].replace("-", " ").title(),
                    "entity_type": entity.type,
                    "description": entity.description,
                    "aliases": entity.aliases,
                    "tags": entity.tags,
                    "questions": entity.questions,
                })

    elif prefix == "concept" and index_path.exists():
        idx = _json.loads(index_path.read_text(encoding="utf-8"))
        entry = next((c for c in idx.get("concepts", []) if c.get("id") == inner_id), None)
        if entry:
            concept = store.read_concept(entry["slug"])
            if concept:
                base.update({
                    "slug": entry["slug"],
                    "title": entry["slug"].replace("-", " ").title(),
                    "description": concept.definition,
                    "tags": concept.tags,
                    "questions": concept.questions,
                })

    elif prefix == "source":
        for slug in store.list_sources():
            src = store.read_source(slug)
            if src and src.id == inner_id:
                base.update({
                    "slug": slug,
                    "title": src.title,
                    "description": src.summary,
                    "tags": src.tags,
                    "questions": src.questions,
                })
                break

    return base
```

- [ ] **Step 4: Run wiki API tests**

```
cd backend && python -m pytest tests/api/test_wiki_api.py -v
```
Expected: all tests PASS (including the 6 new ones).

- [ ] **Step 5: Run full suite**

```
cd backend && python -m pytest --ignore=tests/test_web_crawler.py -q
```
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/api/wiki.py backend/tests/api/test_wiki_api.py
git commit -m "feat(api/wiki): add /edges and /node-detail endpoints"
```

---

## Task 2: Frontend types and API client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

(No backend changes — pure TypeScript additions, no frontend test runner configured in this project.)

- [ ] **Step 1: Add new types to `frontend/src/types/index.ts`**

Append to the end of the file:

```typescript
// ── Graph / Node Detail types ──────────────────────────────────────────────

export interface WikiEdge {
  id: string;
  from: string;
  to: string;
  relation: string;
  source_id: string;
  confidence: number;
}

export interface NodeDetailClaim {
  id: string;
  text: string;
  confidence: number;
  polarity: "asserts" | "denies";
  source_id: string;
}

export interface NodeDetailEdge {
  id: string;
  from: string;
  to: string;
  relation: string;
  source_id: string;
}

export interface NodeDetail {
  id: string;
  node_type: "entity" | "concept" | "source";
  entity_type?: string;
  slug?: string;
  title?: string;
  description?: string;
  aliases?: string[];
  tags?: string[];
  questions?: string[];
  claims: NodeDetailClaim[];
  edges: NodeDetailEdge[];
}
```

- [ ] **Step 2: Add API methods to `frontend/src/api/client.ts`**

Inside the `api` object (after `queryWiki`), add:

```typescript
  // Graph
  listWikiEdges: () => request<import("../types").WikiEdge[]>("/wiki/edges"),
  getWikiNodeDetail: (id: string) =>
    request<import("../types").NodeDetail>(`/wiki/node-detail?id=${encodeURIComponent(id)}`),
```

- [ ] **Step 3: Verify TypeScript compiles**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat(frontend/types): add WikiEdge, NodeDetail types and API methods"
```

---

## Task 3: Install react-flow and implement GraphView

**Files:**
- Create: `frontend/src/components/wiki/GraphView.tsx`
- (package.json and package-lock updated by npm)

- [ ] **Step 1: Install `@xyflow/react`**

```
cd frontend && npm install @xyflow/react
```
Expected: `@xyflow/react` appears in `package.json` dependencies.

- [ ] **Step 2: Create `frontend/src/components/wiki/GraphView.tsx`**

```tsx
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
```

- [ ] **Step 3: Verify TypeScript compiles**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/wiki/GraphView.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat(frontend): GraphView with react-flow radial layout and entity-type filters"
```

---

## Task 4: Implement NodeDetailDrawer

**Files:**
- Create: `frontend/src/components/wiki/NodeDetailDrawer.tsx`

- [ ] **Step 1: Create `frontend/src/components/wiki/NodeDetailDrawer.tsx`**

```tsx
import { useEffect, useState } from "react";
import { X, Tag, HelpCircle, FileText, Link2 } from "lucide-react";
import { api } from "../../api/client";
import type { NodeDetail } from "../../types";

const POLARITY_COLOR: Record<string, string> = {
  asserts: "text-green-600",
  denies: "text-red-600",
};

interface NodeDetailDrawerProps {
  nodeId: string | null;
  onClose: () => void;
}

export function NodeDetailDrawer({ nodeId, onClose }: NodeDetailDrawerProps) {
  const [detail, setDetail] = useState<NodeDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!nodeId) return;
    setDetail(null);
    setError(null);
    setLoading(true);
    api
      .getWikiNodeDetail(nodeId)
      .then(setDetail)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [nodeId]);

  if (!nodeId) return null;

  return (
    <div className="w-72 border-l border-border flex flex-col bg-card shrink-0 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
        <span className="text-sm font-medium truncate">
          {loading ? "Loading…" : (detail?.title ?? nodeId)}
        </span>
        <button
          onClick={onClose}
          className="ml-2 text-muted-foreground hover:text-foreground transition-colors shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {loading && (
        <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">
          Loading…
        </div>
      )}

      {error && (
        <div className="flex-1 flex items-center justify-center text-xs text-red-500 p-4 text-center">
          {error}
        </div>
      )}

      {detail && !loading && (
        <div className="flex-1 overflow-auto p-4 flex flex-col gap-4 text-xs">
          {/* Type badges */}
          <div className="flex gap-1.5 flex-wrap">
            <span className="px-2 py-0.5 rounded bg-muted text-muted-foreground capitalize font-medium">
              {detail.node_type}
              {detail.entity_type ? ` · ${detail.entity_type}` : ""}
            </span>
            {detail.tags?.map((t) => (
              <span key={t} className="flex items-center gap-1 px-2 py-0.5 rounded bg-muted/50 text-muted-foreground">
                <Tag className="w-2.5 h-2.5" />
                {t}
              </span>
            ))}
          </div>

          {/* Aliases (entities only) */}
          {detail.aliases && detail.aliases.length > 0 && (
            <p className="text-muted-foreground">
              Also: {detail.aliases.join(", ")}
            </p>
          )}

          {/* Description */}
          {detail.description && (
            <p className="leading-relaxed text-foreground">{detail.description}</p>
          )}

          {/* Questions */}
          {detail.questions && detail.questions.length > 0 && (
            <div>
              <div className="flex items-center gap-1 font-medium text-muted-foreground mb-1.5">
                <HelpCircle className="w-3 h-3" />
                Questions
              </div>
              <ul className="space-y-1">
                {detail.questions.slice(0, 5).map((q, i) => (
                  <li key={i} className="text-muted-foreground leading-snug">
                    • {q}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Claims */}
          {detail.claims.length > 0 && (
            <div>
              <div className="flex items-center gap-1 font-medium text-muted-foreground mb-1.5">
                <FileText className="w-3 h-3" />
                Claims ({detail.claims.length})
              </div>
              <ul className="space-y-2">
                {detail.claims.slice(0, 6).map((c) => (
                  <li key={c.id} className="border border-border rounded p-2 space-y-1">
                    <p className="text-foreground leading-snug">{c.text}</p>
                    <p className={`${POLARITY_COLOR[c.polarity] ?? "text-muted-foreground"}`}>
                      {c.polarity} · {(c.confidence * 100).toFixed(0)}%
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Edges */}
          {detail.edges.length > 0 && (
            <div>
              <div className="flex items-center gap-1 font-medium text-muted-foreground mb-1.5">
                <Link2 className="w-3 h-3" />
                Relations ({detail.edges.length})
              </div>
              <ul className="space-y-1.5">
                {detail.edges.slice(0, 8).map((e) => {
                  const isFrom = e.from === nodeId;
                  const other = isFrom ? e.to : e.from;
                  const arrow = isFrom ? "→" : "←";
                  return (
                    <li key={e.id} className="text-muted-foreground leading-snug">
                      <span className="text-foreground font-medium">{arrow} {e.relation}</span>{" "}
                      <span className="font-mono">{other}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {detail.claims.length === 0 && detail.edges.length === 0 && (
            <p className="text-muted-foreground text-center py-2">No claims or relations yet.</p>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/wiki/NodeDetailDrawer.tsx
git commit -m "feat(frontend): NodeDetailDrawer with claims and relations"
```

---

## Task 5: Wire Graph tab into KnowledgeMapPanel

**Files:**
- Modify: `frontend/src/components/wiki/KnowledgeMapPanel.tsx`

- [ ] **Step 1: Replace the entire content of `frontend/src/components/wiki/KnowledgeMapPanel.tsx`**

```tsx
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
          <GraphView onNodeClick={setSelectedNodeId} />
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
```

- [ ] **Step 2: Verify TypeScript compiles**

```
cd frontend && npx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Start the dev server and manually verify**

Start backend (in one terminal):
```
cd backend && uvicorn main:app --reload
```

Start frontend (in another terminal):
```
cd frontend && npm run dev
```

Open `http://localhost:5173`, click **Knowledge Map** in the sidebar.

Verify:
- "Graph" and "Browser" toggle buttons appear in the top bar
- Graph tab: canvas renders (empty state message if no sources ingested, or nodes if sources exist)
- Graph tab: filter chips for Entities / Concepts / Sources and entity type chips are visible
- Graph tab: clicking a node opens NodeDetailDrawer on the right with node title
- NodeDetailDrawer: X button closes the drawer
- Browser tab: sub-tabs (Entities / Concepts / Sources), search box, and tables all work as before

- [ ] **Step 4: Run full backend suite to confirm no regressions**

```
cd backend && python -m pytest --ignore=tests/test_web_crawler.py -q
```
Expected: all green (231 + 6 new = 237 passed).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/wiki/KnowledgeMapPanel.tsx
git commit -m "feat(frontend): Graph/Browser toggle in KnowledgeMapPanel with NodeDetailDrawer"
```

---

## Task 6: Tag Phase 5 complete

- [ ] **Step 1: Final test run**

```
cd backend && python -m pytest --ignore=tests/test_web_crawler.py -v 2>&1 | tail -10
```
Expected: ends with `237 passed, 0 failed`.

- [ ] **Step 2: Count tests**

```
cd backend && python -m pytest --ignore=tests/test_web_crawler.py --collect-only -q 2>&1 | tail -3
```

- [ ] **Step 3: Tag**

```bash
git tag phase-5-complete
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| KM Graph tab with react-flow | Task 3 (GraphView) |
| Force-directed visual (initial layout) | Task 3 (radialLayout — concepts center, entities middle, sources outer) |
| Filters (node type, entity type) | Task 3 (filter bar with toggles) |
| NodeDetailDrawer (slide-in with claims + edges) | Task 4 |
| KM Browser tab preserved | Task 5 (Browser sub-tabs intact) |
| `GET /api/wiki/edges` endpoint | Task 1 |
| `GET /api/wiki/node-detail` endpoint | Task 1 |
| Renders 50+ nodes smoothly | React Flow virtualizes by default; radial layout avoids layout recomputation |

**Placeholder scan:** No TBD, TODO, or "implement later" found.

**Type consistency:**
- `WikiEdge.from` (string) used as `e.from` in GraphView and NodeDetailDrawer — matches backend JSON key `"from"`
- `api.listWikiEdges()` → `WikiEdge[]` → GraphView `wikiEdges` state — consistent
- `api.getWikiNodeDetail(nodeId)` → `NodeDetail` → NodeDetailDrawer `detail` state — consistent
- `NodeDetailDrawer` props: `nodeId: string | null, onClose: () => void` — used in KnowledgeMapPanel as `selectedNodeId` (string | null) and `setSelectedNodeId(null)` — consistent
- `GraphView` props: `onNodeClick: (nodeId: string) => void` — wired to `setSelectedNodeId` in KnowledgeMapPanel — consistent
