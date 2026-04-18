# Chat Source Popover Redesign

**Date:** 2026-04-18
**Feature:** Footnote-style source references with inline popover in Chat

## Problem

Current implementation shows all retrieved source cards below each AI message as a list with expand/collapse buttons. This creates visual chaos — sources are always visible, taking up space, and the interaction is disconnected from where sources are cited in the text.

## Goals

- Sources referenced as footnote-style superscript numbers in AI response text
- Clicking a superscript opens a popover with full chunk content + citation highlights
- Compact footnote list below each message (name + score only)
- Remove old source cards entirely

## Decisions

- **Interaction:** Click (not hover) on superscript → popover
- **Popover content:** Full chunk text with `highlighted_ranges` from existing backend implementation
- **Old cards:** Removed completely — replaced by footnote list
- **Implementation:** Pure React + `getBoundingClientRect()`, no new dependencies

## Architecture

```
renderAssistantContent(content, sources)
  — parses [Źródło N] tokens from text
  — maps number → chunk from msg.sources
  — renders <SourceRef num={N} source={chunk} />

<SourceRef />
  — superscript chip (¹ ² ³...)
  — onClick: sets activePopover = { num, source, anchorRect }
  — active state when activePopover.num === this.num

<SourcePopover />  (React portal → document.body)
  — position: fixed, anchored to SourceRef via getBoundingClientRect()
  — renders full chunk text with highlighted_ranges
  — viewport-aware: flips down if not enough space above; clamps to right edge
  — closes on: outside click, Escape key, new message received

<FootnotesList sources={RetrievedChunk[]} />
  — compact list below AI bubble: ¹ filename · score
  — no expand/collapse — read-only reference
```

## Data Flow

```
msg.sources: RetrievedChunk[]  (existing, no backend changes needed)
     ↓
renderAssistantContent(content, sources)
  — splits on [Źródło N] markers
  — wraps each marker in <SourceRef num={N} source={sources[N-1]} />
     ↓
User clicks ¹
  — anchorRect = spanRef.getBoundingClientRect()
  — setActivePopover({ num: 1, source: chunk, anchorRect })
     ↓
<SourcePopover />
  — renders at: top = anchorRect.top - popoverHeight - 8px (or below if flipped)
  — left = clamp(anchorRect.left, 8, viewport.width - 328)
  — shows: document name, rank, score, full text with highlights
     ↓
<FootnotesList />
  — renders below AI bubble
  — ¹ rag-intro.pdf · 0.94
  — ² architecture.md · 0.87
```

## Components

### `SourceRef`

```
Props: { num: number; source: RetrievedChunk | undefined; onActivate: (rect, num, source) => void; isActive: boolean }
Render: superscript span
  - bg-primary/20 text-primary font-bold text-[10px] px-1 py-0.5 rounded cursor-pointer
  - active: bg-primary/40 border border-primary/60
  - undefined source: rendered as plain chip, no click handler
```

### `SourcePopover`

```
Props: { source: RetrievedChunk; anchorRect: DOMRect; onClose: () => void }
Render: React portal (document.body)
  - position: fixed
  - width: 320px, max-height: 280px, overflow-y: auto
  - header: document_name | rank · score
  - body: renderWithHighlights(content, highlighted_ranges ?? [])
  - small triangle arrow pointing to anchor
  - backdrop: invisible full-screen div (onClick → onClose)
  - Escape listener via useEffect
```

### `FootnotesList`

```
Props: { sources: RetrievedChunk[] }
Render: compact list
  - small "Źródła" label
  - for each source: ¹ filename · score (single line)
  - no interaction — purely informational
```

## Positioning Logic

```typescript
const POPOVER_WIDTH = 320;
const POPOVER_HEIGHT_ESTIMATE = 280;
const MARGIN = 8;

const spaceAbove = anchorRect.top;
const openAbove = spaceAbove > POPOVER_HEIGHT_ESTIMATE + MARGIN;

const top = openAbove
  ? anchorRect.top - POPOVER_HEIGHT_ESTIMATE - MARGIN
  : anchorRect.bottom + MARGIN;

const left = Math.min(
  Math.max(anchorRect.left, MARGIN),
  window.innerWidth - POPOVER_WIDTH - MARGIN
);
```

## Error Handling

| Scenario | Behavior |
|---|---|
| `[Źródło N]` where N > sources.length | Render as plain chip, no click handler |
| `sources = []` | FootnotesList not rendered |
| `highlighted_ranges = []` | Popover shows full text without highlights |
| Popover exceeds right viewport edge | Clamp left position |
| Popover exceeds top viewport edge | Flip: open below anchor |
| Press Escape | Close popover |
| New message arrives | Close popover (reset activePopover) |

## Files Changed

| File | Action |
|---|---|
| `frontend/src/components/chat/ChatInterface.tsx` | Remove old source cards + `expandedSources` state; add `activePopover` state; pass `sources` to `renderAssistantContent`; add `<FootnotesList>` and `<SourcePopover>` |
| `frontend/src/components/chat/SourceRef.tsx` | New component — superscript chip |
| `frontend/src/components/chat/SourcePopover.tsx` | New component — portal popover with positioning logic |
| `frontend/src/components/chat/FootnotesList.tsx` | New component — compact footnote list |
| `frontend/src/types/index.ts` | No changes needed |
| `backend/` | No changes needed |

## Out of Scope

- Hover preview (click-only by design)
- Keyboard navigation within popover
- Crawl UI transcript download (separate spec)
