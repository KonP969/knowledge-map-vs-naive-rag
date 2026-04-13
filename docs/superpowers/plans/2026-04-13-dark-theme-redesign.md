# Dark Theme Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current light theme with a dark theme across all frontend panels, and add a Knowledge Base Health widget to the Documents panel.

**Architecture:** CSS variables in `index.css` drive all colors via Tailwind tokens — changing the variables cascades across the whole app. Each component gets hardcoded light-theme classes replaced with token-based ones. A new `KnowledgeBaseHealth` component is created and wired into `DocumentManager`.

**Tech Stack:** React 18, TypeScript, Tailwind CSS (token-based), Lucide React, Recharts (MetricsPanel)

> **Note on testing:** This repo has no frontend test suite. Verification is done by starting the dev server and visually confirming each panel. Backend tests (`pytest tests/ -v`, expected: 15 passed) should remain green — this plan makes no backend changes.

---

## File Map

| File | Action |
|------|--------|
| `src/index.css` | Modify — new dark CSS variables + success/warning/error tokens |
| `tailwind.config.ts` | Modify — add `success`, `warning`, `error` color tokens |
| `src/components/layout/Header.tsx` | Modify — remove `bg-white` |
| `src/components/layout/Footer.tsx` | Modify — remove `bg-white` |
| `src/components/layout/Sidebar.tsx` | Modify — `bg-white` → `bg-card`, active teal |
| `src/App.tsx` | Modify — `bg-[#F9FAFB]` → `bg-background` |
| `src/components/documents/DocumentManager.tsx` | Modify — layout + dark colors + wire KBH widget |
| `src/components/documents/DocumentList.tsx` | Modify — dark rows, status-badge-ready delete hover |
| `src/components/documents/UploadZone.tsx` | Modify — dark bg, teal drag accent |
| `src/components/documents/CrawlPanel.tsx` | Modify — dark inputs, fix hardcoded light colors |
| `src/components/documents/KnowledgeBaseHealth.tsx` | **Create** — SVG circular gauge widget |
| `src/components/chunks/ChunkingLab.tsx` | Modify — dark colors |
| `src/components/chunks/StrategySelector.tsx` | Modify — dark colors |
| `src/components/chunks/ChunkViewer.tsx` | Modify — dark chunk colors |
| `src/components/embeddings/EmbeddingExplorer.tsx` | Modify — dark table, error strip |
| `src/components/embeddings/ScatterPlot.tsx` | Modify — `bg-gray-900` → `bg-background` |
| `src/components/chat/ChatInterface.tsx` | Modify — dark container, source cards |
| `src/components/chat/RetrievalPanel.tsx` | Modify — `bg-white` → `bg-card` |
| `src/components/chat/PromptBuilderPanel.tsx` | Modify — `bg-white` → `bg-card`, dark textarea |
| `src/components/metrics/MetricsPanel.tsx` | Modify — dark cards, table |
| `src/components/tutorial/TutorialPanel.tsx` | Modify — dark cards, Note component, table |

---

### Task 1: Design Tokens

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/index.css`
- Modify: `.worktrees/feature/scaffolding/frontend/tailwind.config.ts`

- [ ] **Step 1: Replace index.css with dark palette**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 220 20% 7%;
    --foreground: 220 25% 88%;
    --card: 220 18% 13%;
    --card-foreground: 220 25% 88%;
    --border: 220 15% 22%;
    --primary: 188 95% 52%;
    --primary-foreground: 220 20% 7%;
    --muted: 220 15% 20%;
    --muted-foreground: 215 18% 58%;
    --radius: 0.5rem;
    --success: 142 71% 45%;
    --warning: 38 92% 50%;
    --error: 0 84% 60%;
  }
}

body {
  @apply bg-background text-foreground;
}
```

- [ ] **Step 2: Add success/warning/error to tailwind.config.ts**

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        error: "hsl(var(--error))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 3: Start dev server and verify dark background appears**

```
cd .worktrees/feature/scaffolding/frontend
npm run dev
```

Open http://localhost:5173 — the app should now have a dark background. Layout will look broken (white boxes everywhere) — that's expected at this stage.

- [ ] **Step 4: Commit**

```bash
git add .worktrees/feature/scaffolding/frontend/src/index.css .worktrees/feature/scaffolding/frontend/tailwind.config.ts
git commit -m "feat: dark theme — CSS variables and Tailwind tokens"
```

---

### Task 2: Layout — Header, Sidebar, Footer, App

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/layout/Header.tsx`
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/layout/Footer.tsx`
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/layout/Sidebar.tsx`
- Modify: `.worktrees/feature/scaffolding/frontend/src/App.tsx`

- [ ] **Step 1: Update Header.tsx** — remove `bg-white`

```tsx
import { Brain } from "lucide-react";
import type { SessionMetrics } from "../../types";

interface HeaderProps {
  metrics: SessionMetrics | null;
}

export function Header({ metrics }: HeaderProps) {
  return (
    <header className="h-14 border-b border-border bg-card flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-2">
        <Brain className="w-5 h-5 text-primary" />
        <span className="font-semibold text-sm">RAG Learning Lab</span>
      </div>
      {metrics && (
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>Queries: <strong className="text-foreground">{metrics.total_queries}</strong></span>
          <span>Tokens: <strong className="text-foreground">{metrics.total_tokens.toLocaleString()}</strong></span>
          <span>Cost: <strong className="text-foreground">${metrics.total_cost_usd.toFixed(4)}</strong></span>
        </div>
      )}
    </header>
  );
}
```

- [ ] **Step 2: Update Footer.tsx** — remove `bg-white`

```tsx
export function Footer() {
  return (
    <footer className="h-8 border-t border-border bg-card flex items-center px-6 shrink-0">
      <span className="text-xs text-muted-foreground">
        RAG Learning Lab — educational single-user app
      </span>
    </footer>
  );
}
```

- [ ] **Step 3: Update Sidebar.tsx** — dark bg, teal active state

```tsx
import { FileText, Layers, ScatterChart, MessageSquare, BarChart2, BookOpen } from "lucide-react";
import type { Panel } from "../../types";

const NAV = [
  { id: "documents" as Panel, label: "Documents", icon: FileText },
  { id: "chunks" as Panel, label: "Chunking Lab", icon: Layers },
  { id: "embeddings" as Panel, label: "Embeddings", icon: ScatterChart },
  { id: "chat" as Panel, label: "Chat", icon: MessageSquare },
  { id: "metrics" as Panel, label: "Metrics", icon: BarChart2 },
  { id: "tutorial" as Panel, label: "Tutorial", icon: BookOpen },
];

interface SidebarProps {
  active: Panel;
  onChange: (panel: Panel) => void;
}

export function Sidebar({ active, onChange }: SidebarProps) {
  return (
    <nav className="w-48 border-r border-border bg-card flex flex-col pt-4 shrink-0">
      {NAV.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
            active === id
              ? "bg-primary/15 text-primary font-medium"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          }`}
        >
          <Icon className="w-4 h-4" />
          {label}
        </button>
      ))}
    </nav>
  );
}
```

- [ ] **Step 4: Update App.tsx** — `bg-[#F9FAFB]` → `bg-background`

```tsx
import { useState, useEffect } from "react";
import { Header } from "./components/layout/Header";
import { Sidebar } from "./components/layout/Sidebar";
import { Footer } from "./components/layout/Footer";
import { DocumentManager } from "./components/documents/DocumentManager";
import { ChunkingLab } from "./components/chunks/ChunkingLab";
import { EmbeddingExplorer } from "./components/embeddings/EmbeddingExplorer";
import { ChatInterface } from "./components/chat/ChatInterface";
import { MetricsPanel } from "./components/metrics/MetricsPanel";
import { TutorialPanel } from "./components/tutorial/TutorialPanel";
import type { Panel, SessionMetrics } from "./types";
import { api } from "./api/client";

export default function App() {
  const [activePanel, setActivePanel] = useState<Panel>("documents");
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);

  useEffect(() => {
    api.getSessionMetrics().then(setMetrics).catch(() => {});
    const interval = setInterval(() => {
      api.getSessionMetrics().then(setMetrics).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <Header metrics={metrics} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar active={activePanel} onChange={setActivePanel} />
        <main className="flex-1 overflow-auto bg-background">
          {activePanel === "documents" && <DocumentManager />}
          {activePanel === "chunks" && <ChunkingLab />}
          {activePanel === "embeddings" && <EmbeddingExplorer />}
          {activePanel === "chat" && <ChatInterface />}
          {activePanel === "metrics" && <MetricsPanel />}
          {activePanel === "tutorial" && <TutorialPanel />}
        </main>
      </div>
      <Footer />
    </div>
  );
}
```

- [ ] **Step 5: Verify in browser** — sidebar, header, footer should look dark and clean.

- [ ] **Step 6: Commit**

```bash
git add .worktrees/feature/scaffolding/frontend/src/components/layout/Header.tsx .worktrees/feature/scaffolding/frontend/src/components/layout/Footer.tsx .worktrees/feature/scaffolding/frontend/src/components/layout/Sidebar.tsx .worktrees/feature/scaffolding/frontend/src/App.tsx
git commit -m "feat: dark theme — layout components"
```

---

### Task 3: KnowledgeBaseHealth Component (new)

**Files:**
- Create: `.worktrees/feature/scaffolding/frontend/src/components/documents/KnowledgeBaseHealth.tsx`

This widget shows:
- Circular gauge: % of documents with embeddings
- Circular gauge: total chunk count (number, not a %)
- Counters: Total Docs, With Embeddings, Total Chars

Data comes from props (parent fetches and passes down).

- [ ] **Step 1: Create KnowledgeBaseHealth.tsx**

```tsx
interface KBHProps {
  totalDocs: number;
  embeddedDocs: number;
  totalChunks: number;
  totalChars: number;
}

function CircularGauge({
  value,
  max,
  label,
  sublabel,
  color = "hsl(188 95% 52%)",
}: {
  value: number;
  max: number;
  label: string;
  sublabel: string;
  color?: string;
}) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const pct = max > 0 ? Math.min(value / max, 1) : 0;
  const offset = circumference * (1 - pct);

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-24 h-24">
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 88 88">
          <circle
            cx="44" cy="44" r={radius}
            fill="none"
            stroke="hsl(220 15% 22%)"
            strokeWidth="8"
          />
          <circle
            cx="44" cy="44" r={radius}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.5s ease" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-sm font-bold text-foreground">{label}</span>
          <span className="text-xs text-muted-foreground">{sublabel}</span>
        </div>
      </div>
    </div>
  );
}

function formatChars(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return `${n}`;
}

export function KnowledgeBaseHealth({ totalDocs, embeddedDocs, totalChunks, totalChars }: KBHProps) {
  const embeddedPct = totalDocs > 0 ? Math.round((embeddedDocs / totalDocs) * 100) : 0;

  return (
    <div className="border border-border rounded-lg bg-card p-4 space-y-4">
      <h3 className="text-sm font-semibold text-foreground">Knowledge Base</h3>

      <div className="flex justify-around">
        <div className="flex flex-col items-center gap-1">
          <CircularGauge
            value={embeddedDocs}
            max={totalDocs}
            label={`${embeddedPct}%`}
            sublabel="embedded"
          />
        </div>
        <div className="flex flex-col items-center gap-1">
          <CircularGauge
            value={totalChunks}
            max={Math.max(totalChunks, 1)}
            label={`${totalChunks}`}
            sublabel="chunks"
            color="hsl(270 70% 65%)"
          />
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 pt-2 border-t border-border">
        {[
          { label: "Total Docs", value: totalDocs },
          { label: "Embedded", value: embeddedDocs },
          { label: "Chars", value: formatChars(totalChars) },
        ].map(({ label, value }) => (
          <div key={label} className="text-center">
            <p className="text-xs text-muted-foreground">{label}</p>
            <p className="text-sm font-semibold text-foreground">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add .worktrees/feature/scaffolding/frontend/src/components/documents/KnowledgeBaseHealth.tsx
git commit -m "feat: add KnowledgeBaseHealth widget with SVG circular gauges"
```

---

### Task 4: Documents Panel

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/documents/DocumentManager.tsx`
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/documents/DocumentList.tsx`
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/documents/UploadZone.tsx`
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/documents/CrawlPanel.tsx`

- [ ] **Step 1: Update DocumentManager.tsx** — new 3-column layout + wire KBH widget

```tsx
import { useState, useEffect } from "react";
import type { DocumentMeta, DocumentDetail, EmbeddingStatus } from "../../types";
import { api } from "../../api/client";
import { UploadZone } from "./UploadZone";
import { DocumentList } from "./DocumentList";
import { CrawlPanel } from "./CrawlPanel";
import { KnowledgeBaseHealth } from "./KnowledgeBaseHealth";

type Tab = "upload" | "crawl";

export function DocumentManager() {
  const [tab, setTab] = useState<Tab>("upload");
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [embeddingStatus, setEmbeddingStatus] = useState<EmbeddingStatus[]>([]);
  const [selected, setSelected] = useState<DocumentDetail | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  useEffect(() => {
    api.listDocuments().then(setDocuments).catch(console.error);
    api.getEmbeddingStatus().then(setEmbeddingStatus).catch(() => {});
  }, []);

  async function handleSelect(doc: DocumentMeta) {
    setLoadingPreview(true);
    try {
      const detail = await api.getDocument(doc.id);
      setSelected(detail);
    } finally {
      setLoadingPreview(false);
    }
  }

  async function handleDelete(id: string) {
    await api.deleteDocument(id);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    if (selected?.id === id) setSelected(null);
  }

  function handleCrawled(added: DocumentMeta[]) {
    if (added.length > 0) {
      setDocuments((prev) => [...added, ...prev]);
    }
  }

  const embeddedDocs = embeddingStatus.length;
  const totalChunks = embeddingStatus.reduce((sum, s) => sum + s.chunk_count, 0);
  const totalChars = documents.reduce((sum, d) => sum + d.char_count, 0);

  return (
    <div className="p-6 h-full flex gap-6">
      {/* Left — upload/crawl + list */}
      <div className="w-80 shrink-0 space-y-4">
        <div className="flex border-b border-border">
          {(["upload", "crawl"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                tab === t
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "upload" ? "Upload File" : "From URL"}
            </button>
          ))}
        </div>

        {tab === "upload" && (
          <UploadZone onUploaded={(doc) => setDocuments((prev) => [doc, ...prev])} />
        )}
        {tab === "crawl" && (
          <CrawlPanel onDocumentsAdded={handleCrawled} />
        )}

        <h2 className="font-semibold text-sm text-foreground">Documents ({documents.length})</h2>
        <DocumentList
          documents={documents}
          selectedId={selected?.id ?? null}
          onSelect={handleSelect}
          onDelete={handleDelete}
        />
      </div>

      {/* Center — preview */}
      <div className="flex-1 border border-border rounded-lg bg-card p-4 overflow-auto">
        {loadingPreview && <p className="text-sm text-muted-foreground">Loading...</p>}
        {!loadingPreview && selected && (
          <>
            <h3 className="font-semibold text-sm mb-3 text-foreground">{selected.name} — Raw Text</h3>
            <pre className="text-xs whitespace-pre-wrap font-mono text-muted-foreground leading-relaxed">
              {selected.raw_text}
            </pre>
          </>
        )}
        {!loadingPreview && !selected && (
          <p className="text-sm text-muted-foreground">Select a document to preview its extracted text.</p>
        )}
      </div>

      {/* Right — KB Health */}
      <div className="w-52 shrink-0">
        <KnowledgeBaseHealth
          totalDocs={documents.length}
          embeddedDocs={embeddedDocs}
          totalChunks={totalChunks}
          totalChars={totalChars}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Update DocumentList.tsx** — dark rows, dark delete hover

```tsx
import { Trash2, FileText } from "lucide-react";
import type { DocumentMeta } from "../../types";

interface DocumentListProps {
  documents: DocumentMeta[];
  selectedId: string | null;
  onSelect: (doc: DocumentMeta) => void;
  onDelete: (id: string) => void;
}

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

export function DocumentList({ documents, selectedId, onSelect, onDelete }: DocumentListProps) {
  if (documents.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No documents uploaded yet.</p>;
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => (
        <div
          key={doc.id}
          className={`border rounded-lg p-3 flex items-start gap-3 cursor-pointer transition-colors ${
            selectedId === doc.id
              ? "border-primary bg-primary/10"
              : "border-border bg-card hover:border-primary/40 hover:bg-muted/50"
          }`}
          onClick={() => onSelect(doc)}
        >
          <FileText className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate text-foreground">{doc.name}</p>
            <p className="text-xs text-muted-foreground">
              {formatBytes(doc.size_bytes)} · {doc.char_count.toLocaleString()} chars
              {doc.page_count != null && ` · ${doc.page_count} pages`}
            </p>
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(doc.id); }}
            className="p-1 rounded hover:bg-error/20 hover:text-error text-muted-foreground transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Update UploadZone.tsx** — dark background, teal drag

```tsx
import { useState, useRef } from "react";
import { Upload } from "lucide-react";
import { api } from "../../api/client";
import type { DocumentMeta } from "../../types";

interface UploadZoneProps {
  onUploaded: (doc: DocumentMeta) => void;
}

export function UploadZone({ onUploaded }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setLoading(true);
    setError(null);
    try {
      const doc = await api.uploadDocument(file);
      onUploaded(doc);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files[0];
        if (f) handleFile(f);
      }}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        dragging
          ? "border-primary bg-primary/10"
          : "border-border bg-card hover:border-primary/50 hover:bg-muted/30"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
      />
      <Upload className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
      {loading ? (
        <p className="text-sm text-muted-foreground">Uploading...</p>
      ) : (
        <>
          <p className="text-sm font-medium text-foreground">Drop file here or click to upload</p>
          <p className="text-xs text-muted-foreground mt-1">PDF, DOCX, TXT</p>
        </>
      )}
      {error && <p className="text-xs text-error mt-2">{error}</p>}
    </div>
  );
}
```

- [ ] **Step 4: Update CrawlPanel.tsx** — fix hardcoded light colors

Replace these specific class strings (do NOT change any logic):
- `className="w-full pl-8 pr-3 py-2 text-sm border rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"` → `"w-full pl-8 pr-3 py-2 text-sm border border-border rounded-md bg-muted text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-50"`
- `className="text-green-600 font-medium"` (progress counter) → `"text-success font-medium"`
- `className="text-red-500"` (error counter) → `"text-error"`
- `className="h-1.5 bg-muted rounded-full overflow-hidden"` — already token-based, keep as-is
- `className="text-green-600 font-medium"` (done summary) → `"text-success font-medium"`
- `className="text-red-500"` (done summary) → `"text-error"`
- `className="border rounded-md divide-y max-h-52 overflow-y-auto"` → `"border border-border rounded-md divide-y divide-border max-h-52 overflow-y-auto bg-card"`
- `className="border border-red-200 rounded-md divide-y divide-red-100 max-h-28 overflow-y-auto"` → `"border border-error/30 rounded-md divide-y divide-error/20 max-h-28 overflow-y-auto bg-card"`
- `className="w-3 h-3 text-green-500 mt-0.5 shrink-0"` (CheckCircle in article list) → `"w-3 h-3 text-success mt-0.5 shrink-0"`
- `className="w-3 h-3 text-red-400 mt-0.5 shrink-0"` (XCircle) → `"w-3 h-3 text-error mt-0.5 shrink-0"`
- `className="text-xs font-medium text-red-500"` (error list header) → `"text-xs font-medium text-error"`
- `className="flex items-start gap-2 text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded-md p-2"` → `"flex items-start gap-2 text-xs text-error bg-error/10 border border-error/20 rounded-md p-2"`

- [ ] **Step 5: Verify Documents panel in browser** — all components dark, KB Health widget visible on right, upload zone dark, document list dark rows.

- [ ] **Step 6: Commit**

```bash
git add .worktrees/feature/scaffolding/frontend/src/components/documents/
git commit -m "feat: dark theme — Documents panel + KnowledgeBaseHealth widget"
```

---

### Task 5: Chunking Lab

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/chunks/ChunkingLab.tsx`
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/chunks/StrategySelector.tsx`
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/chunks/ChunkViewer.tsx`

- [ ] **Step 1: Update ChunkingLab.tsx** — dark select, dark bulk results

Replace these class strings (logic unchanged):
- `"w-full mt-1 text-sm border border-border rounded-md px-2 py-1.5 bg-white"` → `"w-full mt-1 text-sm border border-border rounded-md px-2 py-1.5 bg-muted text-foreground"`
- `"w-full py-2 bg-primary text-white text-sm rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"` → `"w-full py-2 bg-primary text-primary-foreground text-sm rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"`
- `"text-xs text-red-500"` (error) → `"text-xs text-error"`
- `"text-green-600 flex items-center gap-1"` → `"text-success flex items-center gap-1"`
- `"text-red-500 flex items-center gap-1"` → `"text-error flex items-center gap-1"`
- `"border rounded-md divide-y max-h-48 overflow-y-auto"` → `"border border-border rounded-md divide-y divide-border max-h-48 overflow-y-auto bg-card"`

- [ ] **Step 2: Update StrategySelector.tsx** — strategy buttons already use tokens, just verify `border-border` and `hover:border-primary/50` look right on dark. No changes needed if tokens work.

- [ ] **Step 3: Update ChunkViewer.tsx** — dark chunk color blocks + dark stat cards

```tsx
import type { Chunk, ChunkStats } from "../../types";

interface ChunkViewerProps {
  chunks: Chunk[];
  stats: ChunkStats | null;
}

export function ChunkViewer({ chunks, stats }: ChunkViewerProps) {
  if (chunks.length === 0) {
    return <p className="text-sm text-muted-foreground">No chunks generated yet.</p>;
  }

  const COLORS = [
    "bg-primary/20 border-primary/30",
    "bg-success/15 border-success/25",
    "bg-warning/15 border-warning/25",
    "bg-purple-500/15 border-purple-500/25",
    "bg-pink-500/15 border-pink-500/25",
  ];

  return (
    <div className="space-y-4">
      {stats && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: "Count", value: stats.count },
            { label: "Avg length", value: `${stats.avg_length.toFixed(0)} chars` },
            { label: "Min / Max", value: `${stats.min_length} / ${stats.max_length}` },
            { label: "Overlap", value: `${stats.overlap_pct}%` },
          ].map(({ label, value }) => (
            <div key={label} className="border border-border rounded-lg p-3 bg-card text-center">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-sm font-semibold mt-0.5 text-foreground">{value}</p>
            </div>
          ))}
        </div>
      )}
      <div className="space-y-2 max-h-[500px] overflow-auto">
        {chunks.map((chunk, i) => (
          <div key={chunk.id} className={`border rounded-lg p-3 ${COLORS[i % COLORS.length]}`}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground">
                Chunk {chunk.index + 1}
              </span>
              <span className="text-xs text-muted-foreground">
                {chunk.char_count} chars · {chunk.token_count} tokens
              </span>
            </div>
            <p className="text-xs leading-relaxed text-foreground">{chunk.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify Chunking Lab in browser** — generate chunks, check dark color blocks.

- [ ] **Step 5: Commit**

```bash
git add .worktrees/feature/scaffolding/frontend/src/components/chunks/
git commit -m "feat: dark theme — Chunking Lab panel"
```

---

### Task 6: Embeddings Panel

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/embeddings/EmbeddingExplorer.tsx`
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/embeddings/ScatterPlot.tsx`

- [ ] **Step 1: Update EmbeddingExplorer.tsx** — dark table, dark error strip

Replace these class strings (logic unchanged):
- `"border rounded-lg bg-white overflow-hidden"` → `"border border-border rounded-lg bg-card overflow-hidden"`
- `"px-4 py-2 text-xs text-red-500 bg-red-50 border-b"` → `"px-4 py-2 text-xs text-error bg-error/10 border-b border-error/20"`
- `"shrink-0 px-3 py-1.5 bg-primary text-white text-sm rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"` → `"shrink-0 px-3 py-1.5 bg-primary text-primary-foreground text-sm rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"`
- `"text-emerald-600 font-medium"` → `"text-success font-medium"`
- `"text-red-400 hover:text-red-600 disabled:opacity-40 transition-colors"` → `"text-error/70 hover:text-error disabled:opacity-40 transition-colors"`

- [ ] **Step 2: Read ScatterPlot.tsx to find hardcoded colors**

```bash
cat .worktrees/feature/scaffolding/frontend/src/components/embeddings/ScatterPlot.tsx
```

- [ ] **Step 3: Update ScatterPlot.tsx** — replace `bg-gray-900` with `bg-background`

Find the wrapping div that has `bg-gray-900` (or similar) and replace with `bg-background`. Keep all chart logic unchanged.

- [ ] **Step 4: Verify Embeddings panel in browser** — table dark, scatter plot background matches app background.

- [ ] **Step 5: Commit**

```bash
git add .worktrees/feature/scaffolding/frontend/src/components/embeddings/
git commit -m "feat: dark theme — Embeddings panel"
```

---

### Task 7: Chat Panel

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/chat/ChatInterface.tsx`
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/chat/RetrievalPanel.tsx`
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/chat/PromptBuilderPanel.tsx`

- [ ] **Step 1: Update ChatInterface.tsx** — dark chat container, dark source cards, citation chip color

Replace these class strings (logic unchanged):
- `"flex-1 flex flex-col border rounded-lg bg-white overflow-hidden"` → `"flex-1 flex flex-col border border-border rounded-lg bg-card overflow-hidden"`
- `"bg-muted text-foreground"` (assistant bubble) — already token-based, keep
- `"border-t px-3 pt-2 pb-0 flex items-center gap-3 text-xs text-muted-foreground"` — keep, already uses tokens
- `"flex-1 text-sm border border-border rounded-md px-3 py-1.5 outline-none focus:border-primary"` → `"flex-1 text-sm border border-border rounded-md px-3 py-1.5 bg-muted text-foreground outline-none focus:border-primary"`
- In `renderAssistantContent`: `"inline-block bg-blue-100 text-blue-700 text-xs font-medium px-1.5 py-0.5 rounded mx-0.5"` → `"inline-block bg-primary/20 text-primary text-xs font-medium px-1.5 py-0.5 rounded mx-0.5"`
- Source cards: `"bg-white border border-border rounded-md px-2 py-1.5 text-xs"` → `"bg-muted border border-border rounded-md px-2 py-1.5 text-xs"`

- [ ] **Step 2: Update RetrievalPanel.tsx** — `bg-white` → `bg-card`

```tsx
import type { RetrievedChunk } from "../../types";

interface RetrievalPanelProps {
  chunks: RetrievedChunk[];
  topK: number;
  onTopKChange: (k: number) => void;
}

export function RetrievalPanel({ chunks, topK, onTopKChange }: RetrievalPanelProps) {
  return (
    <div className="border border-border rounded-lg bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Retrieved Chunks</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">top-k:</span>
          <input
            type="number" min={1} max={20} value={topK}
            onChange={(e) => onTopKChange(Number(e.target.value))}
            className="w-12 text-xs border border-border rounded px-1.5 py-0.5 text-center bg-muted text-foreground"
          />
        </div>
      </div>

      {chunks.length === 0 ? (
        <p className="text-xs text-muted-foreground">Ask a question to see retrieved chunks.</p>
      ) : (
        <div className="space-y-2 max-h-[300px] overflow-auto">
          {chunks.map((chunk) => (
            <div key={chunk.chunk_id} className="border border-border rounded p-2 bg-muted/50">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">#{chunk.rank}</span>
                <span className="text-xs font-medium text-primary">
                  score: {chunk.score.toFixed(4)}
                </span>
              </div>
              <p className="text-xs leading-relaxed line-clamp-3 text-foreground">{chunk.content}</p>
              <p className="text-xs text-muted-foreground mt-1">
                doc: {chunk.document_name || chunk.document_id.slice(0, 8)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Update PromptBuilderPanel.tsx** — `bg-white` → `bg-card`, dark textarea and token count cells

```tsx
import { useState, useEffect } from "react";
import type { PromptData } from "../../types";
import { api } from "../../api/client";

interface PromptBuilderPanelProps {
  promptData: PromptData | null;
}

export function PromptBuilderPanel({ promptData }: PromptBuilderPanelProps) {
  const [editing, setEditing] = useState(false);
  const [sysPrompt, setSysPrompt] = useState("");

  useEffect(() => {
    if (promptData?.system_message) setSysPrompt(promptData.system_message);
  }, [promptData?.system_message]);

  async function saveSystemPrompt() {
    await api.updateSystemPrompt(sysPrompt);
    setEditing(false);
  }

  return (
    <div className="border border-border rounded-lg bg-card p-4 space-y-3">
      <h3 className="text-sm font-semibold text-foreground">Prompt Builder</h3>

      {promptData ? (
        <>
          <div className="grid grid-cols-4 gap-2">
            {(["system", "context", "query", "total"] as const).map((key) => (
              <div key={key} className="text-center border border-border rounded p-2 bg-muted/50">
                <p className="text-xs text-muted-foreground capitalize">{key}</p>
                <p className="text-sm font-semibold text-foreground">{promptData.token_counts[key]}</p>
              </div>
            ))}
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">System prompt</span>
              <button
                onClick={() => setEditing(!editing)}
                className="text-xs text-primary hover:underline"
              >
                {editing ? "Cancel" : "Edit"}
              </button>
            </div>
            {editing ? (
              <div className="space-y-1">
                <textarea
                  value={sysPrompt}
                  onChange={(e) => setSysPrompt(e.target.value)}
                  rows={4}
                  className="w-full text-xs border border-border rounded p-2 font-mono resize-none bg-muted text-foreground"
                />
                <button
                  onClick={saveSystemPrompt}
                  className="text-xs bg-primary text-primary-foreground px-2 py-1 rounded hover:bg-primary/90"
                >
                  Save
                </button>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground line-clamp-2 font-mono">
                {promptData.system_message}
              </p>
            )}
          </div>

          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Full prompt</p>
            <pre className="text-xs bg-muted rounded p-2 overflow-auto max-h-32 whitespace-pre-wrap font-mono leading-relaxed text-foreground">
              {promptData.full_prompt}
            </pre>
          </div>
        </>
      ) : (
        <p className="text-xs text-muted-foreground">Ask a question to see the assembled prompt.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Verify Chat panel in browser** — dark chat area, teal citation chips, dark input, side panels dark.

- [ ] **Step 5: Commit**

```bash
git add .worktrees/feature/scaffolding/frontend/src/components/chat/
git commit -m "feat: dark theme — Chat panel"
```

---

### Task 8: Metrics Panel

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/metrics/MetricsPanel.tsx`

- [ ] **Step 1: Update MetricsPanel.tsx** — dark cards, dark table

```tsx
import { useState, useEffect } from "react";
import type { SessionMetrics } from "../../types";
import { api } from "../../api/client";

export function MetricsPanel() {
  const [metrics, setMetrics] = useState<SessionMetrics | null>(null);
  const [resetting, setResetting] = useState(false);

  useEffect(() => {
    api.getSessionMetrics().then(setMetrics).catch(console.error);
  }, []);

  async function handleReset() {
    if (!confirm("Reset all data (documents, chunks, embeddings, metrics)?")) return;
    setResetting(true);
    try {
      await api.resetAll();
      setMetrics(null);
      window.location.reload();
    } finally {
      setResetting(false);
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-sm text-foreground">Metrics & Logs</h2>
        <button
          onClick={handleReset}
          disabled={resetting}
          className="text-xs px-3 py-1.5 border border-error/50 text-error rounded-md hover:bg-error/10 disabled:opacity-50 transition-colors"
        >
          {resetting ? "Resetting..." : "Clear All Data"}
        </button>
      </div>

      {metrics ? (
        <>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "Total Queries", value: metrics.total_queries },
              { label: "Total Tokens", value: metrics.total_tokens.toLocaleString() },
              { label: "Total Cost", value: `$${metrics.total_cost_usd.toFixed(4)}` },
            ].map(({ label, value }) => (
              <div key={label} className="border border-border rounded-lg p-4 bg-card text-center">
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className="text-xl font-semibold mt-1 text-foreground">{value}</p>
              </div>
            ))}
          </div>

          <div className="border border-border rounded-lg bg-card overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-muted/60">
                <tr>
                  {["Query", "Embed ms", "Retrieval ms", "LLM ms", "Tokens", "Cost"].map((h) => (
                    <th key={h} className="text-left px-3 py-2 text-muted-foreground font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metrics.queries.map((q) => (
                  <tr key={q.query_id} className="border-t border-border hover:bg-muted/30 transition-colors">
                    <td className="px-3 py-2 max-w-[180px] truncate text-foreground">{q.query}</td>
                    <td className="px-3 py-2 text-muted-foreground">{q.embedding_ms.toFixed(0)}</td>
                    <td className="px-3 py-2 text-muted-foreground">{q.retrieval_ms.toFixed(0)}</td>
                    <td className="px-3 py-2 text-muted-foreground">{q.llm_ms.toFixed(0)}</td>
                    <td className="px-3 py-2 text-muted-foreground">{q.total_tokens}</td>
                    <td className="px-3 py-2 text-muted-foreground">${q.estimated_cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {metrics.queries.length === 0 && (
              <p className="text-xs text-muted-foreground text-center py-4">No queries yet.</p>
            )}
          </div>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">Loading metrics...</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify Metrics panel in browser** — dark cards, dark table with hover.

- [ ] **Step 3: Commit**

```bash
git add .worktrees/feature/scaffolding/frontend/src/components/metrics/MetricsPanel.tsx
git commit -m "feat: dark theme — Metrics panel"
```

---

### Task 9: Tutorial Panel

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/tutorial/TutorialPanel.tsx`

- [ ] **Step 1: Update TutorialPanel.tsx** — dark helper components

Only the helper components at the bottom need changes. Update these local components (do NOT change TutorialPanel body JSX):

`Step` component — change number badge:
```tsx
function Step({ number, title, done, children }: { number: number; title: string; done?: boolean; children: React.ReactNode }) {
  return (
    <div className="flex gap-4">
      <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold mt-0.5 ${done ? "bg-success/20 text-success" : "bg-primary/15 text-primary"}`}>
        {done ? "✓" : number}
      </div>
      <div className="flex-1 space-y-2">
        <h3 className="font-medium text-sm text-foreground">{title}</h3>
        <div className="text-sm text-muted-foreground space-y-2">{children}</div>
      </div>
    </div>
  );
}
```

`PipelineStep` component — `bg-white` → `bg-card`:
```tsx
function PipelineStep({ icon, panel, title, children }: { icon: string; panel: string; title: string; children: React.ReactNode }) {
  return (
    <div className="border border-border rounded-lg p-4 space-y-2 bg-card">
      <div className="flex items-center gap-2">
        <span className="text-lg">{icon}</span>
        <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded text-muted-foreground">{panel}</span>
        <span className="font-medium text-sm text-foreground">{title}</span>
      </div>
      <div className="text-sm text-muted-foreground space-y-2">{children}</div>
    </div>
  );
}
```

`Code` component — already uses `bg-muted`, keep as-is.

`Note` component — change amber to warning token:
```tsx
function Note({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-warning/10 border border-warning/30 rounded px-3 py-2 text-xs text-warning">
      <span className="font-semibold">Wskazówka: </span>{children}
    </div>
  );
}
```

Troubleshooting table — update odd/even rows:
In the table `tbody`, replace:
`"border-b border-border odd:bg-white even:bg-muted/30"` → `"border-b border-border odd:bg-card even:bg-muted/20"`

Also replace the amber `td` class:
`"px-3 py-2 border border-border font-medium text-amber-700"` → `"px-3 py-2 border border-border font-medium text-warning"`

- [ ] **Step 2: Update Tutorial heading section** — `border-b pb-2` headers inherit `text-foreground`, no change needed. The main `h1` and section `h2` headers use `text-foreground`/`text-muted-foreground` tokens already — verify in browser.

- [ ] **Step 3: Verify Tutorial panel in browser** — pipeline step cards dark, note boxes use warning color, troubleshooting table dark.

- [ ] **Step 4: Commit**

```bash
git add .worktrees/feature/scaffolding/frontend/src/components/tutorial/TutorialPanel.tsx
git commit -m "feat: dark theme — Tutorial panel"
```

---

### Task 10: Final sweep and ScatterPlot check

**Files:**
- Modify: `.worktrees/feature/scaffolding/frontend/src/components/embeddings/ScatterPlot.tsx` (if needed)

- [ ] **Step 1: Read ScatterPlot.tsx and fix any remaining hardcoded light colors**

Open the file, scan for: `bg-white`, `bg-gray-`, `text-gray-`, `border-gray-`, hardcoded hex colors. Apply token replacements as needed. Keep all chart/SVG logic unchanged.

- [ ] **Step 2: Full app walkthrough** — visit every panel, check for any remaining white boxes or light-colored elements that look out of place.

- [ ] **Step 3: Run backend tests to confirm no regressions**

```bash
cd .worktrees/feature/scaffolding/backend
.\.venv\Scripts\Activate.ps1
pytest tests/ -v
```

Expected: `15 passed`

- [ ] **Step 4: Final commit**

```bash
git add .worktrees/feature/scaffolding/frontend/src/components/embeddings/ScatterPlot.tsx
git commit -m "feat: dark theme — ScatterPlot and final sweep"
```
