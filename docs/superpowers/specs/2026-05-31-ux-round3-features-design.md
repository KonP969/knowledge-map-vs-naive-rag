# UX Round 3 — features 2/4/5/6 (design)

**Data:** 2026-05-31
**Zakres:** 4 pozostałe poprawki UX z oryginalnej listy Round 3 (po graph search).
**Kolejność realizacji:** 2 → 4 → 5 → 6. Każde feature = osobny commit + test Playwright.

## Kontekst

Round 3 zaczął się od node search w Knowledge Map (commity `87da338`–`93767c2`).
Pozostały 4 features. Wszystkie dane potrzebne dla nich są już dostępne w API/typach
(`WikiSource` ma `key_takeaways`, `tags`, `questions`, `summary`, `source_url`).

---

## Feature 2 — Historia rozmów w Wiki Chat

**Problem:** `ChatWithTracePanel` trzyma pojedynczy `trace`; nowe pytanie kasuje poprzednie
(`setTrace(null)`). Brak historii Q&A.

**Rozwiązanie:**
- Zamiana `trace: QueryTrace | null` na `history: QueryTrace[]`.
- Render lewego panelu jako pionowy scroll par Q&A (najstarsze u góry, najnowsze na dole),
  styl ChatGPT. Każdy wpis zachowuje obecny layout (answer + sources + reasoning +
  related questions + metryki). Auto-scroll do najnowszego po dodaniu.
- **Pipeline Trace** (prawy panel) pokazuje etapy **ostatniej** rozmowy; replay etapów
  uruchamia się tylko dla najnowszego wpisu.
- **Persystencja:** `localStorage`, klucz `wikiChatHistory`. Limit ostatnich 20 rozmów
  (FIFO), by nie puchło. Odczyt przy montowaniu, zapis przy każdej zmianie historii.
- Przycisk **„Wyczyść historię"** czyści stan i localStorage.
- `related_questions` i klik nadal wypełniają input (bez zmian).

**Pliki:** `frontend/src/components/chat_with_trace/ChatWithTracePanel.tsx`.

---

## Feature 4 — Lint → Knowledge Map (klikalne lokalizacje)

**Problem:** Issue w lincie ma `location` (np. `entity:e_001`), ale nie da się
przeskoczyć do węzła w grafie.

**Ustalony fakt:** backend zapisuje `location` dla węzłów jako `entity:<id>` /
`concept:<id>` / `source:<id>` (patrz `navigability.py`, `stale_summary.py`,
`entity_alias_collision.py`). Format jest **identyczny** z ID węzłów ReactFlow w
`GraphView` (`entity:${e.id}` itd.) → `location` można podać wprost jako `selectedNodeId`,
bez mapowania slug→id. `GraphAutoFocus` już centruje na `selectedNodeId`.

**Rozwiązanie:**
- **`App.tsx`:** podniesienie stanu — `focusNode: string | null` + funkcja
  `goToNode(nodeId)` ustawiająca `activePanel="knowledge_map"` i `focusNode=nodeId`.
  Przekazane do `LintPanel` (jako `onLocationClick`) i `KnowledgeMapPanel` (jako `focusNode`).
- **`LintIssueRow`:** jeśli `location` ma prefix `entity:`/`concept:`/`source:` — render
  lokalizacji jako klikalny przycisk-link wywołujący `onLocationClick(location)`.
  Pozostałe (`claims.jsonl:…`, `edges.jsonl:…`) zostają zwykłym tekstem.
  Prop `onLocationClick` przechodzi `LintPanel → LintIssueRow`.
- **`KnowledgeMapPanel`:** nowy prop `focusNode?: string | null`. `useEffect` na zmianę
  `focusNode`: ustawia `view="graph"` + `selectedNodeId=focusNode` (otwiera drawer).
  Konsument musi wyzerować `focusNode` po obsłużeniu (callback `onFocusHandled`) lub
  KnowledgeMapPanel reaguje na każdą nową wartość.

**Pliki:** `App.tsx`, `LintPanel.tsx`, `LintIssueRow.tsx`, `KnowledgeMapPanel.tsx`.

---

## Feature 5 — Sortowanie Sources (data / tytuł)

**Problem:** Lista źródeł w `SourcesPanel` jest w kolejności z API, bez możliwości sortowania.

**Rozwiązanie:**
- Stan `sortBy: "date" | "title"` (domyślnie `date`) + `sortDir: "asc" | "desc"`
  (domyślnie `desc` — najnowsze u góry).
- Kontrolki w nagłówku listy (obok Refresh/Reset): przełącznik pola + kierunku.
- Sortowanie czysto frontendowe na kopii `sources` (`ingested_at` dla date, `title`
  lokalnie `localeCompare` dla tytułu). Nie zmienia danych z API.

**Pliki:** `SourcesPanel.tsx`.

---

## Feature 6 — Podgląd szczegółów źródła (drawer)

**Problem:** Kafelek źródła pokazuje tylko title/summary/tagi/datę. `key_takeaways`,
`questions`, `source_url` są w API, ale niewidoczne.

**Rozwiązanie:**
- Nowy komponent **`SourceDetailDrawer`** (wzorowany na `NodeDetailDrawer`): wysuwany
  panel z prawej, pokazuje `title`, `source_url` (jako link), `ingested_at`, `summary`,
  `key_takeaways` (lista), `tags`, `questions` (lista).
- `SourcesPanel`: stan `selectedSource: WikiSource | null`. Klik w kafelek (poza ikoną
  kosza i przyciskami potwierdzenia usuwania) otwiera drawer. Drawer ma przycisk zamknięcia.

**Pliki:** nowy `frontend/src/components/wiki/SourceDetailDrawer.tsx`, `SourcesPanel.tsx`.

---

## Testy

Zgodnie z konwencją UX Round 2 (`test(playwright)`): po jednym scenariuszu e2e na feature,
weryfikującym kluczowe zachowanie (np. historia przeżywa „nowe pytanie", klik lokalizacji
lintu przełącza na Knowledge Map, sortowanie zmienia kolejność, drawer pokazuje takeaways).

## Out of scope (YAGNI)

- Brak edycji/usuwania pojedynczych wpisów historii czatu (tylko „wyczyść wszystko").
- Brak klikalności `claim:`/`edge:` w lincie (nie mają węzłów w grafie).
- Brak serwerowej persystencji historii czatu.
