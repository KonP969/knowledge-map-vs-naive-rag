# Graph Search — Design Spec
Date: 2026-05-30

## Summary

Add a search input to the Knowledge Map panel's top bar (graph view) that lets users find and navigate to nodes by name. Selecting a result centers the graph on that node and activates the existing highlight/dim mechanism.

## Scope

Two files changed: `KnowledgeMapPanel.tsx`, `GraphView.tsx`. No backend changes. No new dependencies.

## Architecture

### KnowledgeMapPanel.tsx

New state:
- `graphSearch: string` — current input value
- `graphDropdownOpen: boolean` — controls dropdown visibility

Top bar additions (when `view === "graph"`):
- Search input with magnifier icon, positioned before the Refresh button
- `x` clear button appears when input is non-empty
- Dropdown rendered below the input

Search logic:
- Filters `entities`, `concepts`, `sources` already loaded in component state
- Matches on: `slug`, `title`, `type`, `aliases` (case-insensitive substring)
- Max 8 results, ordered: entities → concepts → sources
- Node ID format: `entity:${e.id}`, `concept:${c.id}`, `source:${s.id}`

On result click:
- `setSelectedNodeId(nodeId)` — activates existing highlight + triggers GraphAutoFocus
- Clears input and closes dropdown

Dropdown close:
- `onBlur` with 150 ms delay (allows click-on-result to fire first)
- `graphSearch` empty → dropdown hidden

Empty state in dropdown: `"Brak wyników dla «{query}»"`

### GraphView.tsx

New internal component `<GraphAutoFocus>` rendered as a child of `<ReactFlow>`:

```tsx
function GraphAutoFocus({ selectedNodeId, nodes }: { selectedNodeId: string | null; nodes: Node[] }) {
  const { setCenter } = useReactFlow();
  useEffect(() => {
    if (!selectedNodeId) return;
    const node = nodes.find((n) => n.id === selectedNodeId);
    if (!node) return;
    setCenter(node.position.x + NODE_W / 2, node.position.y + NODE_H / 2, { zoom: 1.5, duration: 600 });
  }, [selectedNodeId]);
  return null;
}
```

`useReactFlow()` requires being a descendant of `<ReactFlow>` — this pattern satisfies that without adding a `<ReactFlowProvider>`.

`rfNodes` passed as prop so `GraphAutoFocus` can find position of the selected node.

Guard: if `selectedNodeId` not found in `nodes` (e.g. filtered out), skip `setCenter` silently.

## Data Flow

```
User types → graphSearch state → filter entities/concepts/sources
→ dropdown with ≤8 results
→ user clicks result
→ setSelectedNodeId(nodeId) [KnowledgeMapPanel]
→ GraphView receives selectedNodeId prop
  → displayNodes/displayEdges (existing): dim unrelated nodes/edges
  → GraphAutoFocus useEffect: setCenter on node position
```

## Edge Cases

| Scenario | Behavior |
|---|---|
| Graph still loading | Input shown, results empty (entities/concepts/sources are `[]`) |
| Node filtered out (not in rfNodes) | GraphAutoFocus skips setCenter; highlight still applied via selectedNodeId |
| All filters off | setCenter executes but node invisible — acceptable |
| Long slug in dropdown | `truncate` + `max-w-xs` |
| No results | Empty state: `"Brak wyników dla «{query}»"` |

## UX Details

- Input always visible in top bar when `view === "graph"` (consistent with browser view search)
- Dropdown max 8 items to avoid covering the graph
- Each dropdown item: type icon + slug/title + type badge (right-aligned)
- After selection: input clears, selectedNodeId persists (user can click canvas to deselect — existing behavior)

## Tests (Playwright)

1. Type query → dropdown appears with matching nodes
2. Click result → dropdown closes, input empty
3. Click result → NodeDetailDrawer opens with correct node data (confirms selectedNodeId set)
4. Type query with no matches → empty state message shown
5. Click outside dropdown → dropdown closes

## Out of Scope

- Keyboard navigation in dropdown (↑↓ Enter) — can be added later
- Searching while graph is animating
