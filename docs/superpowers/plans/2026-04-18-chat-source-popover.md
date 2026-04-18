# Chat Source Popover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the expand/collapse source cards below chat messages with footnote-style superscript numbers that open a positioned popover when clicked, plus a compact footnote list.

**Architecture:** Four focused components — `SourceRef` (superscript chip), `FootnotesList` (compact list), `SourcePopover` (React portal with viewport-aware positioning), and a refactored `ChatInterface` that wires them together. The existing `renderWithHighlights` logic is duplicated into `SourcePopover` since it's a small self-contained helper.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, `ReactDOM.createPortal`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/components/chat/SourceRef.tsx` | Create | Superscript chip — click triggers popover |
| `frontend/src/components/chat/FootnotesList.tsx` | Create | Compact footnote list under AI bubble |
| `frontend/src/components/chat/SourcePopover.tsx` | Create | Portal popover with positioning + highlight rendering |
| `frontend/src/components/chat/ChatInterface.tsx` | Modify | Wire new components, remove old cards |

All paths are relative to the worktree:
`C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG\.worktrees\feature\scaffolding\`

The repo also tracks copies at the same relative paths without `.worktrees/feature/scaffolding/` prefix (e.g. `frontend/src/components/chat/`). After each commit, sync the worktree file to the tracked copy and commit that too.

---

## Task 1: SourceRef component

**Files:**
- Create: `frontend/src/components/chat/SourceRef.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { useRef } from "react";
import type { RetrievedChunk } from "../../types";

interface SourceRefProps {
  num: number;
  source: RetrievedChunk | undefined;
  onActivate: (rect: DOMRect, num: number, source: RetrievedChunk) => void;
  isActive: boolean;
}

export function SourceRef({ num, source, onActivate, isActive }: SourceRefProps) {
  const spanRef = useRef<HTMLSpanElement>(null);

  if (!source) {
    return (
      <span className="inline-flex items-center justify-center bg-primary/20 text-primary text-[10px] font-bold w-4 h-4 rounded align-super relative -top-0.5 mx-0.5">
        {num}
      </span>
    );
  }

  return (
    <span
      ref={spanRef}
      onClick={() => {
        if (spanRef.current) {
          onActivate(spanRef.current.getBoundingClientRect(), num, source);
        }
      }}
      className={`inline-flex items-center justify-center text-[10px] font-bold w-4 h-4 rounded align-super relative -top-0.5 mx-0.5 cursor-pointer transition-colors select-none ${
        isActive
          ? "bg-primary/50 text-primary border border-primary/70"
          : "bg-primary/20 text-primary border border-primary/30 hover:bg-primary/35"
      }`}
    >
      {num}
    </span>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG\.worktrees\feature\scaffolding\frontend && npx tsc --noEmit 2>&1
```

Expected: no errors.

- [ ] **Step 3: Commit**

Sync to tracked copy and commit:
```bash
cp ".worktrees/feature/scaffolding/frontend/src/components/chat/SourceRef.tsx" "frontend/src/components/chat/SourceRef.tsx"
git -C C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG add frontend/src/components/chat/SourceRef.tsx
git -C C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG commit -m "feat: add SourceRef superscript chip component"
```

---

## Task 2: FootnotesList component

**Files:**
- Create: `frontend/src/components/chat/FootnotesList.tsx`

- [ ] **Step 1: Create the component**

```tsx
import type { RetrievedChunk } from "../../types";

interface FootnotesListProps {
  sources: RetrievedChunk[];
}

export function FootnotesList({ sources }: FootnotesListProps) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-1.5 pt-1.5 border-t border-border/50">
      <p className="text-[10px] text-muted-foreground/60 uppercase tracking-wide mb-1">Źródła</p>
      <div className="space-y-0.5">
        {sources.map((chunk) => (
          <div key={chunk.chunk_id} className="flex items-baseline gap-1.5 text-[11px]">
            <span className="text-primary font-bold shrink-0">{chunk.rank}</span>
            <span className="text-muted-foreground truncate">
              {chunk.document_name || chunk.document_id.slice(0, 12)}
            </span>
            <span className="text-muted-foreground/50 shrink-0">· {chunk.score.toFixed(3)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG\.worktrees\feature\scaffolding\frontend && npx tsc --noEmit 2>&1
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cp ".worktrees/feature/scaffolding/frontend/src/components/chat/FootnotesList.tsx" "frontend/src/components/chat/FootnotesList.tsx"
git -C C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG add frontend/src/components/chat/FootnotesList.tsx
git -C C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG commit -m "feat: add FootnotesList component"
```

---

## Task 3: SourcePopover component

**Files:**
- Create: `frontend/src/components/chat/SourcePopover.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { useEffect, type ReactNode } from "react";
import { createPortal } from "react-dom";
import type { RetrievedChunk, HighlightRange } from "../../types";

interface SourcePopoverProps {
  source: RetrievedChunk;
  anchorRect: DOMRect;
  onClose: () => void;
}

const POPOVER_WIDTH = 320;
const POPOVER_HEIGHT_ESTIMATE = 280;
const MARGIN = 8;

function renderWithHighlights(content: string, ranges: HighlightRange[]): ReactNode {
  if (!ranges || ranges.length === 0) return <span>{content}</span>;
  const parts: ReactNode[] = [];
  let cursor = 0;
  for (const range of ranges) {
    if (cursor < range.start) {
      parts.push(<span key={`t-${cursor}`}>{content.slice(cursor, range.start)}</span>);
    }
    parts.push(
      <mark key={`h-${range.start}`} className="bg-primary/25 text-foreground font-medium rounded px-0.5">
        {content.slice(range.start, range.end)}
      </mark>
    );
    cursor = range.end;
  }
  if (cursor < content.length) {
    parts.push(<span key="t-end">{content.slice(cursor)}</span>);
  }
  return <>{parts}</>;
}

export function SourcePopover({ source, anchorRect, onClose }: SourcePopoverProps) {
  const spaceAbove = anchorRect.top;
  const openAbove = spaceAbove > POPOVER_HEIGHT_ESTIMATE + MARGIN;

  const top = openAbove
    ? anchorRect.top - POPOVER_HEIGHT_ESTIMATE - MARGIN
    : anchorRect.bottom + MARGIN;

  const left = Math.min(
    Math.max(anchorRect.left, MARGIN),
    window.innerWidth - POPOVER_WIDTH - MARGIN
  );

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return createPortal(
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40" onClick={onClose} />
      {/* Popover */}
      <div
        className="fixed z-50 bg-card border border-border rounded-lg shadow-xl overflow-hidden"
        style={{ top, left, width: POPOVER_WIDTH, maxHeight: POPOVER_HEIGHT_ESTIMATE }}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-border bg-muted/50">
          <span className="text-xs font-semibold text-primary truncate">
            {source.document_name || source.document_id.slice(0, 12)}
          </span>
          <span className="text-[10px] text-muted-foreground shrink-0">
            #{source.rank} · {source.score.toFixed(3)}
          </span>
        </div>
        {/* Content */}
        <div className="px-3 py-2 overflow-y-auto text-xs leading-relaxed text-foreground" style={{ maxHeight: POPOVER_HEIGHT_ESTIMATE - 40 }}>
          {renderWithHighlights(source.content, source.highlighted_ranges ?? [])}
        </div>
      </div>
    </>,
    document.body
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG\.worktrees\feature\scaffolding\frontend && npx tsc --noEmit 2>&1
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
cp ".worktrees/feature/scaffolding/frontend/src/components/chat/SourcePopover.tsx" "frontend/src/components/chat/SourcePopover.tsx"
git -C C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG add frontend/src/components/chat/SourcePopover.tsx
git -C C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG commit -m "feat: add SourcePopover portal component"
```

---

## Task 4: Refactor ChatInterface

**Files:**
- Modify: `frontend/src/components/chat/ChatInterface.tsx`

This task replaces the old expand/collapse source cards with the new footnote system.

- [ ] **Step 1: Write the new ChatInterface.tsx**

Replace the entire file with:

```tsx
import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import type { RetrievedChunk, PromptData } from "../../types";
import { streamChat, api } from "../../api/client";
import { RetrievalPanel } from "./RetrievalPanel";
import { PromptBuilderPanel } from "./PromptBuilderPanel";
import { SourceRef } from "./SourceRef";
import { SourcePopover } from "./SourcePopover";
import { FootnotesList } from "./FootnotesList";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: RetrievedChunk[];
}

interface ActivePopover {
  num: number;
  source: RetrievedChunk;
  anchorRect: DOMRect;
}

function renderAssistantContent(
  content: string,
  sources: RetrievedChunk[],
  activeNum: number | null,
  onActivate: (rect: DOMRect, num: number, source: RetrievedChunk) => void
) {
  const parts = content.split(/(\[Źródło\s+\d+(?::[^\]]+)?\])/g);
  return parts.map((part, i) => {
    const match = part.match(/^\[Źródło\s+(\d+)/);
    if (match) {
      const num = parseInt(match[1], 10);
      const source = sources[num - 1];
      return (
        <SourceRef
          key={i}
          num={num}
          source={source}
          onActivate={onActivate}
          isActive={activeNum === num}
        />
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(8);
  const [temperature, setTemperature] = useState(0.0);
  const [retrieval, setRetrieval] = useState<RetrievedChunk[]>([]);
  const [promptData, setPromptData] = useState<PromptData | null>(null);
  const [activePopover, setActivePopover] = useState<ActivePopover | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Close popover when a new message arrives
  useEffect(() => {
    setActivePopover(null);
  }, [messages.length]);

  function handleActivate(rect: DOMRect, num: number, source: RetrievedChunk) {
    setActivePopover((prev) =>
      prev?.num === num ? null : { num, source, anchorRect: rect }
    );
  }

  function handleSend() {
    const query = input.trim();
    if (!query || loading) return;
    setInput("");
    setLoading(true);

    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    abortRef.current = streamChat(
      query,
      topK,
      (token) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = { ...last, content: last.content + token };
          return updated;
        });
      },
      () => {
        setLoading(false);
        Promise.all([api.getRetrieval(), api.getPrompt()])
          .then(([ret, prompt]) => {
            setRetrieval(ret);
            setPromptData(prompt);
            if (ret.length > 0) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  updated[updated.length - 1] = { ...last, sources: ret };
                }
                return updated;
              });
            }
          })
          .catch(console.error);
      },
      undefined,
      temperature,
    );
  }

  return (
    <div className="h-full flex gap-4 p-6">
      {/* Chat column */}
      <div className="flex-1 flex flex-col border border-border rounded-lg bg-card overflow-hidden">
        <div className="flex-1 overflow-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground text-center mt-8">
              Ask a question about your uploaded documents.
            </p>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
                }`}
              >
                {msg.role === "assistant"
                  ? renderAssistantContent(
                      msg.content || (loading && i === messages.length - 1 ? "▋" : ""),
                      msg.sources ?? [],
                      activePopover?.num ?? null,
                      handleActivate
                    )
                  : msg.content}
              </div>
              {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                <div className="max-w-[80%] w-full">
                  <FootnotesList sources={msg.sources} />
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        <div className="border-t px-3 pt-2 pb-0 flex items-center gap-3 text-xs text-muted-foreground">
          <span>Temperatura:</span>
          <input
            type="range" min={0} max={1} step={0.1} value={temperature}
            onChange={(e) => setTemperature(Number(e.target.value))}
            className="w-24 accent-primary"
          />
          <span className="w-6 text-center font-medium text-foreground">{temperature.toFixed(1)}</span>
          <span className="text-xs ml-1">(0 = deterministyczny, 1 = kreatywny)</span>
        </div>
        <div className="px-3 pb-3 pt-2 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Ask a question..."
            className="flex-1 text-sm border border-border rounded-md px-3 py-1.5 bg-muted text-foreground outline-none focus:border-primary"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="p-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Right panels */}
      <div className="w-80 flex flex-col gap-4 overflow-auto">
        <RetrievalPanel chunks={retrieval} topK={topK} onTopKChange={setTopK} />
        <PromptBuilderPanel promptData={promptData} />
      </div>

      {/* Popover */}
      {activePopover && (
        <SourcePopover
          source={activePopover.source}
          anchorRect={activePopover.anchorRect}
          onClose={() => setActivePopover(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: TypeScript check**

```bash
cd C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG\.worktrees\feature\scaffolding\frontend && npx tsc --noEmit 2>&1
```

Expected: no errors.

- [ ] **Step 3: Manual test in browser**

With both servers running (backend port 8000, frontend port 5173):

1. Open http://localhost:5173 → Chat tab
2. Ask a question about uploaded documents
3. Wait for response — verify:
   - Source chips in text are **superscript numbers** (¹ ²), not `[Źródło 1]` chips
   - Compact footnote list appears below bubble: `¹ filename · score`
   - Old "Rozwiń ▼" cards are **gone**
4. Click a superscript number — verify:
   - Popover opens above (or below if near top) the clicked number
   - Popover shows document name, rank, score
   - Cited text is highlighted in `bg-primary/25`
5. Click outside popover — verify it closes
6. Press Escape — verify it closes
7. Click same number again — verify it toggles closed
8. Click different number — verify new popover opens

- [ ] **Step 4: Commit**

```bash
cp ".worktrees/feature/scaffolding/frontend/src/components/chat/ChatInterface.tsx" "frontend/src/components/chat/ChatInterface.tsx"
git -C C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG add frontend/src/components/chat/ChatInterface.tsx
git -C C:\Users\Konrad\Documents\__projects_and_git_repo_clones\RAG commit -m "feat: refactor chat to footnote-style sources with popover"
```
