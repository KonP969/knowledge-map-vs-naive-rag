# Chat Source Highlighting Design

**Date:** 2026-04-17
**Feature:** Expandable sources with citation highlighting in Chat

## Overview

When the AI answers a question in the Chat tab, it retrieves relevant chunks from the vector store and cites them in its response as `[Źródło N]` markers. Currently, sources are shown below the message as cards with a 120-character preview. This feature adds expandable source cards that show the full chunk text with highlighted fragments that the AI cited in its response.

## Goals

- **Primary:** Accuracy — highlighted fragments must precisely match what the AI used
- **Secondary:** Speed — no noticeable delay when expanding a source

## Data Flow

```
User asks question
    ↓
Backend: /api/chat — embed → retrieve → build prompt → stream GPT response
    ↓
Frontend: collects streaming tokens
    ↓
Frontend: on stream end → GET /api/chat/retrieval
    ↓
Backend: for each chunk, runs _find_citations(last_response, chunk.content)
         returns highlighted_ranges: [{ start, end, text }]
    ↓
Frontend: renders collapsed source cards
    ↓
User clicks Expand ▼
    ↓
Frontend: renders full text, splits on highlighted_ranges, wraps matches in <mark>
```

## Backend

### New state variable

```python
_last_response: str = ""
```

Updated in the `chat()` endpoint by concatenating streamed tokens after the stream completes (captured in a wrapper generator).

### Citation extraction

```python
def _find_citations(response_text: str, source_text: str) -> List[Dict]:
    """
    Finds sentences/phrases from response_text that appear verbatim in source_text.
    Returns list of { start, end, text } ranges sorted by start position.
    Overlapping ranges are merged.
    [Źródło N] markers are stripped from response_text before matching.
    """
    import re
    cleaned = re.sub(r'\[Źródło\s+\d+[^\]]*\]', '', response_text)
    ranges = []
    for sentence in re.split(r'(?<=[.!?])\s+', cleaned):
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue
        idx = source_text.find(sentence)
        if idx != -1:
            ranges.append({"start": idx, "end": idx + len(sentence), "text": sentence})
    # Sort and merge overlapping ranges
    ranges.sort(key=lambda r: r["start"])
    merged = []
    for r in ranges:
        if merged and r["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], r["end"])
            merged[-1]["text"] = source_text[merged[-1]["start"]:merged[-1]["end"]]
        else:
            merged.append(dict(r))
    return merged
```

### Modified endpoint

`GET /api/chat/retrieval` — returns same shape as before, each item extended with:

```json
{
  "chunk_id": "...",
  "document_id": "...",
  "document_name": "...",
  "content": "full chunk text",
  "score": 0.95,
  "rank": 1,
  "highlighted_ranges": [
    { "start": 42, "end": 87, "text": "cytat ze źródła" }
  ]
}
```

If no citations found, `highlighted_ranges` is `[]`. Frontend still works — renders full text without highlights.

## Frontend

### Types

Add `highlighted_ranges` to `RetrievedChunk` type:

```ts
interface HighlightRange {
  start: number;
  end: number;
  text: string;
}

interface RetrievedChunk {
  // ... existing fields
  highlighted_ranges?: HighlightRange[];
}
```

### Source card component

Each source card in ChatInterface:

- **Collapsed (default):** header (document name + rank + score) + 120-char preview + "Rozwiń ▼" button
- **Expanded:** header + full text with highlighted ranges + "Zwiń ▲" button

Highlight rendering — split `content` string on range boundaries, wrap matched fragments in `<mark>`:

```tsx
function renderWithHighlights(content: string, ranges: HighlightRange[]) {
  if (!ranges.length) return <span>{content}</span>;
  const parts = [];
  let cursor = 0;
  for (const range of ranges) {
    if (cursor < range.start) parts.push(content.slice(cursor, range.start));
    parts.push(<mark key={range.start}>{content.slice(range.start, range.end)}</mark>);
    cursor = range.end;
  }
  if (cursor < content.length) parts.push(content.slice(cursor));
  return <>{parts.map((p, i) => typeof p === 'string' ? <span key={i}>{p}</span> : p)}</>;
}
```

Highlight style (Tailwind `<mark>` override via className):

```
bg-primary/25 text-foreground font-medium rounded px-0.5
```

### State

Each source card manages its own `expanded: boolean` state (local to component, no global state needed).

## Error Handling

| Scenario | Behavior |
|---|---|
| `highlighted_ranges = []` | Render full text without any highlights |
| Citation not found in source | Skip — not added to ranges |
| Overlapping highlights | Merge before returning from backend |
| Very long source (>10k chars) | Render normally, scroll within expanded card if needed |
| Backend error on retrieval | Sources not shown — existing behavior unchanged |

## Files Changed

| File | Change |
|---|---|
| `backend/api/chat.py` | Add `_last_response`, `_find_citations()`, extend `/retrieval` response |
| `frontend/src/types.ts` | Add `HighlightRange`, extend `RetrievedChunk` |
| `frontend/src/components/chat/ChatInterface.tsx` | Expand/collapse source cards, `renderWithHighlights()` |

## Out of Scope

- Fuzzy matching fallback (can be added later if exact matching proves insufficient)
- Copying source text to clipboard
- Linking to original document file
