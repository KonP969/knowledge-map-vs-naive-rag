# Chat Source Highlighting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zwinięte karty źródeł w chacie rozszerzają się po kliknięciu i pokazują pełny tekst z podświetlonymi fragmentami cytowanymi przez AI.

**Architecture:** Backend przechowuje ostatnią odpowiedź AI i przy GET /api/chat/retrieval uruchamia `_find_citations()` — exact substring matching zdań odpowiedzi w tekście chunka, zwraca `highlighted_ranges`. Frontend renderuje karty źródeł w trybie expand/collapse; po rozwinięciu dzieli tekst na segmenty i owija pasujące fragmenty w `<mark>`.

**Tech Stack:** FastAPI (Python 3.9), React 18, TypeScript, Tailwind CSS

---

## File Map

| File | Action | Odpowiedzialność |
|---|---|---|
| `backend/api/chat.py` | Modify | Dodaj `_last_response`, `_find_citations()`, wzbogać `/retrieval` |
| `frontend/src/types/index.ts` | Modify | Dodaj `HighlightRange`, rozszerz `RetrievedChunk` |
| `frontend/src/components/chat/ChatInterface.tsx` | Modify | Expand/collapse cards, `renderWithHighlights()` |

---

## Task 1: Backend — `_find_citations` + wzbogacony `/retrieval`

**Files:**
- Modify: `backend/api/chat.py`

- [ ] **Step 1: Dodaj `_last_response` do module-level state**

W `backend/api/chat.py`, po linii z `_current_system_prompt`, dodaj:

```python
_last_response: str = ""
```

- [ ] **Step 2: Zbieraj tokeny streamu do `_last_response`**

W funkcji `chat()`, zastąp wewnętrzną funkcję `event_stream()`:

```python
    # 6. Stream response
    collected: List[str] = []

    def event_stream():
        global _last_response
        for token in stream_chat(
            prompt_data["full_prompt"],
            req.query,
            embedding_ms=embedding_ms,
            retrieval_ms=retrieval_ms,
            temperature=req.temperature,
        ):
            collected.append(token)
            yield f"data: {token}\n\n"
        _last_response = "".join(collected)
        yield "data: [DONE]\n\n"
```

- [ ] **Step 3: Napisz funkcję `_find_citations`**

Po definicji `router = APIRouter(...)` (po linii 14), przed definicją klas `ChatRequest`, dodaj:

```python
import re as _re


def _find_citations(response_text: str, source_text: str) -> List[Dict[str, Any]]:
    """Exact substring matching — finds response sentences in source_text.
    Returns sorted, merged list of {start, end, text} ranges."""
    cleaned = _re.sub(r'\[Źródło\s+\d+[^\]]*\]', '', response_text)
    ranges: List[Dict[str, Any]] = []
    for sentence in _re.split(r'(?<=[.!?])\s+', cleaned):
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue
        idx = source_text.find(sentence)
        if idx != -1:
            ranges.append({"start": idx, "end": idx + len(sentence), "text": sentence})
    ranges.sort(key=lambda r: r["start"])
    merged: List[Dict[str, Any]] = []
    for r in ranges:
        if merged and r["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], r["end"])
            merged[-1]["text"] = source_text[merged[-1]["start"]:merged[-1]["end"]]
        else:
            merged.append(dict(r))
    return merged
```

- [ ] **Step 4: Wzbogać endpoint `/retrieval`**

Zastąp istniejącą funkcję `get_retrieval()`:

```python
@router.get("/retrieval")
def get_retrieval():
    global _last_retrieval, _last_response
    enriched = []
    for chunk in _last_retrieval:
        highlights = _find_citations(_last_response, chunk["content"]) if _last_response else []
        enriched.append({**chunk, "highlighted_ranges": highlights})
    return enriched
```

- [ ] **Step 5: Ręczny test backendu**

Uruchom (lub przeładuj) backend:
```
uvicorn main:app --reload --port 8000
```

Wyślij pytanie przez frontend Chat, następnie:
```bash
curl -s http://localhost:8000/api/chat/retrieval | python -m json.tool | head -60
```

Oczekiwany output: każdy element ma klucz `"highlighted_ranges": [...]` (może być `[]` jeśli brak dokładnych cytatów).

- [ ] **Step 6: Commit**

```bash
git add backend/api/chat.py
git commit -m "feat: backend _find_citations and highlighted_ranges in /retrieval"
```

---

## Task 2: Frontend — typy

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Dodaj `HighlightRange` i rozszerz `RetrievedChunk`**

W pliku `frontend/src/types/index.ts`, zastąp blok `RetrievedChunk` (linie 60-67):

```typescript
export interface HighlightRange {
  start: number;
  end: number;
  text: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  document_name: string;
  content: string;
  score: number;
  rank: number;
  highlighted_ranges?: HighlightRange[];
}
```

- [ ] **Step 2: Sprawdź że TypeScript kompiluje się bez błędów**

```bash
cd frontend && npx tsc --noEmit
```

Oczekiwany output: brak błędów.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat: add HighlightRange type and extend RetrievedChunk"
```

---

## Task 3: Frontend — expand/collapse + highlight rendering

**Files:**
- Modify: `frontend/src/components/chat/ChatInterface.tsx`

- [ ] **Step 1: Dodaj import `HighlightRange`**

W linii 2 pliku (`import type { ... } from "../../types"`), dodaj `HighlightRange`:

```typescript
import type { DocumentMeta, EmbeddingPoint, EmbeddingStatus, HighlightRange } from "../../types";
```

Uwaga: `HighlightRange` pochodzi z `frontend/src/types/index.ts` — Task 2 musi być ukończony przed Task 3.

- [ ] **Step 2: Dodaj helper `renderWithHighlights`**

Po funkcji `renderAssistantContent` (linia 27), przed `export function ChatInterface()`, dodaj:

```typescript
function renderWithHighlights(content: string, ranges: HighlightRange[]) {
  if (!ranges || ranges.length === 0) return <span>{content}</span>;
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  for (const range of ranges) {
    if (cursor < range.start) {
      parts.push(<span key={`t-${cursor}`}>{content.slice(cursor, range.start)}</span>);
    }
    parts.push(
      <mark
        key={`h-${range.start}`}
        className="bg-primary/25 text-foreground font-medium rounded px-0.5"
      >
        {content.slice(range.start, range.end)}
      </mark>
    );
    cursor = range.end;
  }
  if (cursor < content.length) {
    parts.push(<span key={`t-end`}>{content.slice(cursor)}</span>);
  }
  return <>{parts}</>;
}
```

- [ ] **Step 3: Dodaj stan `expandedSources` do komponentu**

W `ChatInterface`, po deklaracji `const [similarity, setSimilarity]` (lub po ostatnim useState), dodaj:

```typescript
const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());

function toggleSource(key: string) {
  setExpandedSources((prev) => {
    const next = new Set(prev);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    return next;
  });
}
```

- [ ] **Step 4: Zastąp rendering kart źródeł**

W JSX, znajdź blok renderujący źródła (linie 109-122):

```tsx
{msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
  <div className="max-w-[80%] mt-1 space-y-1">
    <p className="text-xs text-muted-foreground font-medium px-1">Źródła:</p>
    {msg.sources.map((chunk) => (
      <div key={chunk.chunk_id} className="bg-muted border border-border rounded-md px-2 py-1.5 text-xs">
        <div className="flex items-center justify-between gap-2 mb-0.5">
          <span className="font-medium text-primary truncate">{chunk.document_name || chunk.document_id.slice(0, 12)}</span>
          <span className="text-muted-foreground shrink-0">#{chunk.rank} · {chunk.score.toFixed(3)}</span>
        </div>
        <p className="text-muted-foreground line-clamp-2 leading-relaxed">{chunk.content.slice(0, 120)}…</p>
      </div>
    ))}
  </div>
)}
```

Zastąp całość:

```tsx
{msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
  <div className="max-w-[80%] mt-1 space-y-1">
    <p className="text-xs text-muted-foreground font-medium px-1">Źródła:</p>
    {msg.sources.map((chunk) => {
      const key = `${i}-${chunk.chunk_id}`;
      const isExpanded = expandedSources.has(key);
      return (
        <div key={chunk.chunk_id} className="bg-muted border border-border rounded-md px-2 py-1.5 text-xs">
          <div className="flex items-center justify-between gap-2 mb-0.5">
            <span className="font-medium text-primary truncate">
              {chunk.document_name || chunk.document_id.slice(0, 12)}
            </span>
            <span className="text-muted-foreground shrink-0">#{chunk.rank} · {chunk.score.toFixed(3)}</span>
          </div>
          {!isExpanded ? (
            <>
              <p className="text-muted-foreground line-clamp-2 leading-relaxed">
                {chunk.content.slice(0, 120)}…
              </p>
              <button
                onClick={() => toggleSource(key)}
                className="mt-1 text-primary/70 hover:text-primary transition-colors"
              >
                Rozwiń ▼
              </button>
            </>
          ) : (
            <>
              <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                {renderWithHighlights(chunk.content, chunk.highlighted_ranges ?? [])}
              </p>
              <button
                onClick={() => toggleSource(key)}
                className="mt-1 text-primary/70 hover:text-primary transition-colors"
              >
                Zwiń ▲
              </button>
            </>
          )}
        </div>
      );
    })}
  </div>
)}
```

- [ ] **Step 5: Sprawdź że TypeScript kompiluje się bez błędów**

```bash
cd frontend && npx tsc --noEmit
```

Oczekiwany output: brak błędów.

- [ ] **Step 6: Sprawdź w przeglądarce**

1. Otwórz http://localhost:5173 → Chat
2. Zadaj pytanie związane z uploadowanymi dokumentami
3. Poczekaj na odpowiedź
4. Sprawdź czy pod odpowiedzią widać zwinięte karty źródeł z przyciskiem "Rozwiń ▼"
5. Kliknij "Rozwiń ▼" — card powinien się rozwinąć z pełnym tekstem
6. Jeśli AI cytowało dokładne fragmenty — powinny być podświetlone na niebiesko (`bg-primary/25`)
7. Kliknij "Zwiń ▲" — card powinien się zwinąć

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/chat/ChatInterface.tsx
git commit -m "feat: expandable source cards with citation highlighting in chat"
```
