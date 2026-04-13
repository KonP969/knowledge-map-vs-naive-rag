# Dark Theme Redesign — Design Spec

**Data:** 2026-04-13  
**Zakres:** Pełny redesign UI RAG Learning Lab — zamiana jasnego motywu na ciemny  
**Źródło:** Screenshoty z `stitch_redesign/` (6 wzorców wizualnych)

---

## Cel

Zastąpić obecny jasny motyw (białe tło, niebieski primary) ciemnym motywem wzorowanym na screenshotach Stitch. Zmiany wyłącznie wizualne — bez nowych funkcji, z jednym wyjątkiem: dodanie widgetu Knowledge Base Health w panelu Documents.

---

## 1. Design Tokens (`src/index.css`)

Nowe wartości CSS variables:

| Token | HSL | Opis |
|---|---|---|
| `--background` | `220 20% 7%` | Tło aplikacji (prawie czarny granat) |
| `--card` | `220 18% 13%` | Tło kart i paneli |
| `--border` | `220 15% 22%` | Linie oddzielające |
| `--primary` | `188 95% 52%` | Akcent teal/cyan |
| `--primary-foreground` | `220 20% 7%` | Tekst na tle primary |
| `--foreground` | `220 25% 88%` | Główny tekst |
| `--muted` | `220 15% 20%` | Tło muted elementów |
| `--muted-foreground` | `215 18% 58%` | Drugorzędny tekst |

Nowe tokeny (status badges):

| Token | HSL | Opis |
|---|---|---|
| `--success` | `142 71% 45%` | Status Active (zielony) |
| `--warning` | `38 92% 50%` | Status Processing (żółty) |
| `--error` | `0 84% 60%` | Status Error (czerwony) |

---

## 2. Layout

### Sidebar (`components/layout/Sidebar.tsx`)
- Tło: `bg-card border-r border-border`
- Aktywny element: `bg-primary/15 text-primary` (teal zamiast blue)
- Hover: `hover:bg-muted hover:text-foreground`

### Header (`components/layout/Header.tsx`)
- Tło: `bg-card border-b border-border`
- Metryki: small badge z `bg-muted text-muted-foreground`

### Footer (`components/layout/Footer.tsx`)
- Tło: `bg-background border-t border-border`

---

## 3. Panele

### Documents (`DocumentManager`, `DocumentList`, `UploadZone`, `CrawlPanel`)

**Układ:** siatka 2-kolumnowa — DocumentList zajmuje ~70% szerokości, nowy `KnowledgeBaseHealth` widget ~30% po prawej.

**DocumentList:**
- Tabela z dark rows, `hover:bg-muted/50`
- Status badges:
  - Active → `bg-success/20 text-success`
  - Processing → `bg-warning/20 text-warning`
  - Error → `bg-error/20 text-error`

**UploadZone:**
- `border-dashed border-border bg-card`, przy hover teal border

**CrawlPanel:**
- Input `bg-muted border-border`, button primary teal

**KnowledgeBaseHealth** (nowy komponent):
- Dwa circular gauge SVG (`strokeDasharray` + `strokeDashoffset`):
  - Storage Usage (% z `/api/embeddings/status` lub aproks.)
  - Total Token Count (suma tokenów dokumentów)
- Pod nimi 3 liczniki: Active Sources, Processing, Errors
- Dane z istniejących endpointów: `/api/documents` + `/api/embeddings/status`

### Chunking Lab (`ChunkingLab`, `StrategySelector`, `ChunkViewer`)
- Obecny układ 2-kolumnowy zachowany
- Kolory: `bg-background`, karty `bg-card border border-border`
- Wykresy tokenów (recharts): kolor słupków → `var(--primary)` (teal)
- Config panel lewy, preview prawy — jak screen 1

### Embeddings (`EmbeddingExplorer`, `ScatterPlot`)
- ScatterPlot ma już `bg-gray-900` — zamieniamy na `bg-background`
- Status badges dokumentów → kolory z tokenów success/warning/error
- Akcenty generowania → teal

### Chat (`ChatInterface`, `RetrievalPanel`, `PromptBuilderPanel`)
- Bąbelki: user → `bg-primary text-primary-foreground`, assistant → `bg-card`
- Pasek modelu (info bar) u góry: `bg-muted text-muted-foreground text-xs`
- Input: `bg-muted border-border`
- RetrievalPanel, PromptBuilderPanel: `bg-card border-border`

### Metrics (`MetricsPanel`)
- Wykresy recharts: linie/słupki w kolorach teal (`var(--primary)`) i purple (`#8B5CF6`)
- Tabela logów: dark rows ze status badges (Info/Error/Warning)
- Karty metryk: `bg-card border-border`

### Tutorial (`TutorialPanel`)
- Karty: `bg-card border-border`
- Kody/snippety: `bg-muted text-foreground`
- Nagłówki sekcji: `text-primary`

---

## 4. Hardcoded kolory do usunięcia

Podczas przeglądu komponentów usunąć/zastąpić:
- `bg-white` → `bg-card`
- `bg-[#F9FAFB]`, `bg-gray-50`, `bg-gray-100` → `bg-background` lub `bg-muted`
- `text-gray-*` → odpowiednie tokeny (`text-foreground`, `text-muted-foreground`)
- `border-gray-*` → `border-border`
- Hardcoded hex kolory w recharts → `hsl(var(--primary))`

---

## 5. Tailwind config

Dodać do `tailwind.config.ts` w `theme.extend.colors`:
```ts
success: "hsl(var(--success))",
warning: "hsl(var(--warning))",
error: "hsl(var(--error))",
```

---

## 6. Nowe pliki

- `src/components/documents/KnowledgeBaseHealth.tsx` — circular gauge widget

---

## 7. Co się NIE zmienia

- Struktura nawigacji (te same panele, te same etykiety)
- Logika biznesowa, API calls, typy TypeScript
- Funkcjonalność chatu (bez Context Inspector, bez zakładek History/Inspector)
- Zależności npm (bez nowych bibliotek)
