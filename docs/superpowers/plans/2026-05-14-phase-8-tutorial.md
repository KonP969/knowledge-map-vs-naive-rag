# Phase 8 — Tutorial Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Przepisać TutorialPanel z 6 sekcjami opisującymi Knowledge Map RAG (zastępując przestarzały naive RAG content).

**Architecture:** Tabbowane 6-sekcyjne UI z komponentem `Walkthrough` (click-through stepper per sekcja). Każda sekcja to oddzielny plik w `sections/`. Brak zmian backendowych.

**Tech Stack:** React 18, TypeScript, Tailwind CSS (klasy: `bg-card`, `text-foreground`, `bg-muted`, `text-primary`, `text-destructive`, `text-warning`, etc.)

---

## Struktura plików

| Akcja | Plik |
|---|---|
| Create | `frontend/src/components/tutorial/Walkthrough.tsx` |
| Rewrite | `frontend/src/components/tutorial/TutorialPanel.tsx` |
| Create | `frontend/src/components/tutorial/sections/SectionIntro.tsx` |
| Create | `frontend/src/components/tutorial/sections/SectionNaiveRag.tsx` |
| Create | `frontend/src/components/tutorial/sections/SectionIngest.tsx` |
| Create | `frontend/src/components/tutorial/sections/SectionRetrieval.tsx` |
| Create | `frontend/src/components/tutorial/sections/SectionQuerying.tsx` |
| Create | `frontend/src/components/tutorial/sections/SectionWalkthroughs.tsx` |

---

### Task 1: Komponent Walkthrough

**Files:**
- Create: `frontend/src/components/tutorial/Walkthrough.tsx`

- [ ] **Step 1: Utwórz plik Walkthrough.tsx**

```tsx
import { useState } from "react";

export interface WalkthroughStep {
  title: string;
  content: React.ReactNode;
  panelHint?: string;
}

export function Walkthrough({ steps }: { steps: WalkthroughStep[] }) {
  const [current, setCurrent] = useState(0);
  const step = steps[current];

  return (
    <div className="border border-primary/30 rounded-lg overflow-hidden bg-primary/5 mt-4">
      <div className="flex items-center gap-2 px-4 py-2 bg-primary/10 border-b border-primary/20">
        <span className="text-xs font-mono text-primary font-medium">Krok po kroku</span>
        <span className="ml-auto text-xs text-muted-foreground">{current + 1} / {steps.length}</span>
      </div>
      <div className="p-4 space-y-3 min-h-[100px]">
        <h4 className="font-semibold text-sm text-foreground">{step.title}</h4>
        <div className="text-sm text-muted-foreground space-y-2">{step.content}</div>
        {step.panelHint && (
          <div className="flex items-center gap-2 bg-muted rounded px-3 py-1.5 text-xs mt-2">
            <span className="text-muted-foreground">Panel →</span>
            <span className="font-mono font-semibold text-foreground">{step.panelHint}</span>
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 px-4 py-3 border-t border-primary/20 bg-card/50">
        <div className="flex gap-1.5 mr-auto">
          {steps.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrent(i)}
              className={`w-2 h-2 rounded-full transition-colors ${
                i === current ? "bg-primary" : "bg-muted-foreground/30 hover:bg-muted-foreground/60"
              }`}
            />
          ))}
        </div>
        <button
          onClick={() => setCurrent(c => Math.max(0, c - 1))}
          disabled={current === 0}
          className="px-3 py-1 text-xs rounded border border-border disabled:opacity-30 hover:bg-muted transition-colors"
        >
          ← Wstecz
        </button>
        <button
          onClick={() => setCurrent(c => Math.min(steps.length - 1, c + 1))}
          disabled={current === steps.length - 1}
          className="px-3 py-1 text-xs rounded bg-primary text-primary-foreground disabled:opacity-30 hover:bg-primary/90 transition-colors"
        >
          Dalej →
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Sprawdź TypeScript**

```bash
cd frontend && npx tsc --noEmit
```

Oczekiwane: zero błędów.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/tutorial/Walkthrough.tsx
git commit -m "feat(tutorial): add Walkthrough step-by-step component"
```

---

### Task 2: TutorialPanel — szkielet tabbowy

**Files:**
- Rewrite: `frontend/src/components/tutorial/TutorialPanel.tsx`

- [ ] **Step 1: Zamień całą zawartość TutorialPanel.tsx**

```tsx
import { useState } from "react";

type TabId = "intro" | "naive-rag" | "ingest" | "retrieval" | "querying" | "walkthroughs";

const TABS: { id: TabId; label: string }[] = [
  { id: "intro", label: "Knowledge Map RAG" },
  { id: "naive-rag", label: "Dlaczego nie naive RAG" },
  { id: "ingest", label: "Jak działa ingest" },
  { id: "retrieval", label: "Jak działa retrieval" },
  { id: "querying", label: "Jak pytać" },
  { id: "walkthroughs", label: "Przewodniki" },
];

export function TutorialPanel() {
  const [activeTab, setActiveTab] = useState<TabId>("intro");

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-foreground mb-1">RAG 2.0 — Knowledge Map</h1>
        <p className="text-muted-foreground text-sm">Kompletny przewodnik systemu opartego na wiedzy strukturalnej.</p>
      </div>

      <div className="flex gap-0.5 flex-wrap border-b border-border mb-6">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2 text-sm rounded-t transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? "border-primary text-primary font-medium bg-primary/5"
                : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/40"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "intro" && <div className="text-muted-foreground text-sm">Sekcja 1 — wkrótce</div>}
      {activeTab === "naive-rag" && <div className="text-muted-foreground text-sm">Sekcja 2 — wkrótce</div>}
      {activeTab === "ingest" && <div className="text-muted-foreground text-sm">Sekcja 3 — wkrótce</div>}
      {activeTab === "retrieval" && <div className="text-muted-foreground text-sm">Sekcja 4 — wkrótce</div>}
      {activeTab === "querying" && <div className="text-muted-foreground text-sm">Sekcja 5 — wkrótce</div>}
      {activeTab === "walkthroughs" && <div className="text-muted-foreground text-sm">Sekcja 6 — wkrótce</div>}
    </div>
  );
}
```

- [ ] **Step 2: Sprawdź w przeglądarce**

`cd frontend && npm run dev` — otwórz Tutorial, klikaj zakładki.
`npx tsc --noEmit` — zero błędów.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/tutorial/TutorialPanel.tsx
git commit -m "feat(tutorial): tabbed skeleton with 6 section placeholders"
```

---

### Task 3: Sekcja 1 — Czym jest Knowledge Map RAG

**Files:**
- Create: `frontend/src/components/tutorial/sections/SectionIntro.tsx`
- Modify: `frontend/src/components/tutorial/TutorialPanel.tsx`

- [ ] **Step 1: Utwórz SectionIntro.tsx**

```tsx
import { Walkthrough } from "../Walkthrough";

export function SectionIntro() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Czym jest Knowledge Map RAG?</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Knowledge Map RAG to podejście do pytania-odpowiedzi oparte na <strong className="text-foreground">wiedzy strukturalnej</strong> zamiast podobieństwa wektorowego.
          System buduje graf wiedzy: encje, pojęcia, claims z proweniencją i relacje. Zamiast top-K chunków — precyzyjne cytowania z grafu.
        </p>

        <div className="grid grid-cols-2 gap-3 mt-4">
          <div className="border border-border rounded-lg p-4 bg-destructive/5">
            <p className="text-xs font-semibold text-destructive uppercase tracking-wide mb-2">Naive RAG</p>
            <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
              <li>Podziel dokument na chunki</li>
              <li>Wygeneruj embeddingi (wektory)</li>
              <li>Przechowaj w vector store</li>
              <li>Zapytanie → cosine similarity → top-K</li>
              <li>Wstaw chunki do prompta → odpowiedź</li>
            </ol>
          </div>
          <div className="border border-primary/30 rounded-lg p-4 bg-primary/5">
            <p className="text-xs font-semibold text-primary uppercase tracking-wide mb-2">Knowledge Map RAG</p>
            <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
              <li>Parsuj dokument</li>
              <li>Klasyfikuj (LLM) → encje, claims, relacje</li>
              <li>Wykryj konflikty z istniejącą wiedzą</li>
              <li>Zapisz do wiki (Markdown + JSONL)</li>
              <li>Zapytanie → intent → graf → cytowana odpowiedź</li>
            </ol>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-foreground">Kluczowe różnice</h3>
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-muted">
              <th className="px-3 py-2 text-left border border-border">Cecha</th>
              <th className="px-3 py-2 text-left border border-border text-destructive">Naive RAG</th>
              <th className="px-3 py-2 text-left border border-border text-primary">KM RAG</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["Śledzenie źródeł", "Brak — chunk pochodzi z dowolnego miejsca", "Każdy claim ma proweniencję (source_id, sekcja)"],
              ["Sprzeczności", "Niewidoczne — oba chunki trafiają do prompta", "Wykrywane podczas ingestu, oznaczone w wiki"],
              ["Zapytania temporalne", "Słabe — chunki bez struktury dat", "Claims mają pola date_start/date_end"],
              ["Relacje między encjami", "Brak — każdy chunk jest izolowany", "Graf relacji: X –[CEO_OF]→ Y"],
              ["Skalowanie", "Rośnie liczba wektorów — degradacja jakości", "Rośnie wiki — każda encja wzbogaca graf"],
            ].map(([feature, naive, km]) => (
              <tr key={feature} className="border-b border-border odd:bg-card even:bg-muted/20">
                <td className="px-3 py-2 border border-border font-medium">{feature}</td>
                <td className="px-3 py-2 border border-border text-muted-foreground">{naive}</td>
                <td className="px-3 py-2 border border-border text-muted-foreground">{km}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Walkthrough
        steps={[
          {
            title: "Otwórz Knowledge Map",
            content: <p>Kliknij <strong>Knowledge Map</strong> w sidebarze. Zobaczysz graf wiedzy zbudowany ze wszystkich wgranych źródeł — każdy węzeł to encja lub pojęcie.</p>,
            panelHint: "Knowledge Map → Browser",
          },
          {
            title: "Kliknij węzeł na grafie",
            content: <p>Na zakładce <strong>Graph</strong> kliknij dowolny węzeł. Otworzy się szuflada z pełną stroną wiki: lista claims z proweniencją, relacje z innymi węzłami.</p>,
            panelHint: "Knowledge Map → Graph",
          },
          {
            title: "Porównaj z listą w Browser",
            content: <p>Zakładka <strong>Browser</strong> pokazuje tabelarycznie wszystkie encje i pojęcia z liczbą claims. Przeszukuj po nazwie — każde wystąpienie linkuje do strony wiki.</p>,
            panelHint: "Knowledge Map → Browser",
          },
          {
            title: "Struktura wiki na dysku",
            content: <p>System przechowuje wiedzę w plikach Markdown w <code className="bg-muted px-1 rounded text-xs">wiki_data/default/</code>. Każda encja to <code className="bg-muted px-1 rounded text-xs">entity_*.md</code> z YAML frontmatter i <code className="bg-muted px-1 rounded text-xs">claims.jsonl</code>.</p>,
          },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 2: Podłącz w TutorialPanel.tsx**

Dodaj import na początku pliku:
```tsx
import { SectionIntro } from "./sections/SectionIntro";
```

Zamień placeholder:
```tsx
{activeTab === "intro" && <SectionIntro />}
```

- [ ] **Step 3: Weryfikacja manualna**

Otwórz Tutorial → zakładka "Knowledge Map RAG". Sprawdź:
- Tabela porównawcza (5 wierszy) renderuje się
- Walkthrough pokazuje 4 kroki, przyciski Dalej/Wstecz działają, kropki nawigują
`npx tsc --noEmit` — zero błędów.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/tutorial/sections/SectionIntro.tsx frontend/src/components/tutorial/TutorialPanel.tsx
git commit -m "feat(tutorial): section 1 — Knowledge Map RAG intro with comparison table"
```

---

### Task 4: Sekcja 2 — Dlaczego nie naive RAG

**Files:**
- Create: `frontend/src/components/tutorial/sections/SectionNaiveRag.tsx`
- Modify: `frontend/src/components/tutorial/TutorialPanel.tsx`

- [ ] **Step 1: Utwórz SectionNaiveRag.tsx**

```tsx
import { Walkthrough } from "../Walkthrough";

export function SectionNaiveRag() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Dlaczego naive RAG zawodzi?</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Naive RAG sprawdza się przy prostych pytaniach o pojedynczy fakt. Ale gdy pytania wymagają
          <strong className="text-foreground"> syntezy wielu źródeł</strong>,
          <strong className="text-foreground"> śledzenia sprzeczności</strong> lub
          <strong className="text-foreground"> rozumowania temporalnego</strong> — system zawodzi.
        </p>
      </div>

      <div className="border border-destructive/30 rounded-lg p-4 space-y-3 bg-destructive/5">
        <p className="text-xs font-semibold text-destructive uppercase tracking-wide">Case study — trudne pytanie</p>
        <p className="text-sm font-mono bg-background rounded p-3 border border-border text-foreground">
          "Które źródła podają różne daty założenia firmy Anthropic — i które jest bardziej aktualne?"
        </p>
        <div className="space-y-2">
          <p className="text-xs font-semibold text-foreground">Dlaczego naive RAG zawodzi:</p>
          <ul className="text-xs text-muted-foreground space-y-1.5 list-none">
            {[
              ["Chunking rozcina kontekst", "Zdanie 'Anthropic założona w 2021' może być w chunku A, a 'w 2022' w chunku B — nigdy nie trafią razem do prompta"],
              ["Brak linkowania encji", "Oba chunki mówią o tej samej firmie, ale vector store nie wie że to ta sama encja"],
              ["Brak proweniencji", "Nie wiadomo które źródło (Raport A vs. Artykuł B) podało daną datę"],
              ["Brak porównania aktualności", "Cosine similarity nie uwzględnia dat publikacji — nie można ocenić który dokument jest nowszy"],
            ].map(([problem, explanation]) => (
              <li key={problem} className="flex gap-2">
                <span className="text-destructive mt-0.5 flex-shrink-0">✗</span>
                <span><strong className="text-foreground">{problem}:</strong> {explanation}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="border border-primary/30 rounded-lg p-4 space-y-3 bg-primary/5">
        <p className="text-xs font-semibold text-primary uppercase tracking-wide">Jak KM RAG odpowiada na to pytanie</p>
        <ul className="text-xs text-muted-foreground space-y-1.5 list-none">
          {[
            ["Ingest Stage 3 wykrywa konflikt", "LLM widzi nowy claim 'założona w 2022' → porównuje z istniejącym 'założona w 2021' → raport konfliktu"],
            ["Claims mają proweniencję", "Każdy claim: {source_id: 'raport_a', date_extracted: '2024-01', confidence: 0.9}"],
            ["Retrieval Stage 1 parsuje intent", "Pytanie → ParsedIntent: {entities: ['Anthropic'], query_type: 'comparison', requires_provenance: true}"],
            ["Answer generator cytuje oba źródła", "'Raport A (2021) podaje 2021, Artykuł B (2024) podaje 2022 — nowszy wskazuje 2022'"],
          ].map(([step, explanation]) => (
            <li key={step} className="flex gap-2">
              <span className="text-primary mt-0.5 flex-shrink-0">✓</span>
              <span><strong className="text-foreground">{step}:</strong> {explanation}</span>
            </li>
          ))}
        </ul>
      </div>

      <Walkthrough
        steps={[
          {
            title: "Wyobraź sobie dwa dokumenty z konfliktem",
            content: (
              <div className="space-y-2">
                <p>Dokument A (2021): <em>"Anthropic Inc. została założona w lutym 2021 przez byłych pracowników OpenAI."</em></p>
                <p>Dokument B (2024): <em>"Firma Anthropic, założona w 2022, ogłosiła..."</em></p>
              </div>
            ),
          },
          {
            title: "W naive RAG: chunki lądują osobno w vector store",
            content: (
              <p>Pytanie "kiedy założono Anthropic?" → cosine similarity → top-K. System może zwrócić tylko jeden chunk lub oba bez wskazania który jest bardziej wiarygodny. Wynik: niespójna odpowiedź.</p>
            ),
          },
          {
            title: "W KM RAG: conflict_detector wykrywa problem podczas ingestu",
            content: (
              <p>Po wgraniu Dokumentu B, Stage 3 ingestu wykrywa: nowy claim <code className="bg-muted px-1 rounded text-xs">founded_date: 2022</code> koliduje z istniejącym <code className="bg-muted px-1 rounded text-xs">founded_date: 2021</code>. Raport konfliktu widoczny w Sources.</p>
            ),
            panelHint: "Sources → Conflict Report",
          },
          {
            title: "Zapytaj w Chat — retrieval pobiera oba claims z proweniencją",
            content: (
              <p>Zapytaj: <em>"Które źródła podają różne daty założenia Anthropic?"</em> — Stage 1 parsuje intent → Stage 2 pobiera stronę wiki Anthropic z oboma claims → Stage 5 cytuje oba źródła z datami publikacji.</p>
            ),
            panelHint: "Chat with Trace",
          },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 2: Podłącz w TutorialPanel.tsx**

```tsx
import { SectionNaiveRag } from "./sections/SectionNaiveRag";
// ...
{activeTab === "naive-rag" && <SectionNaiveRag />}
```

- [ ] **Step 3: Weryfikacja manualna + commit**

Tutorial → "Dlaczego nie naive RAG": czerwony blok, niebieski blok, Walkthrough 4 kroki.
`npx tsc --noEmit` — zero błędów.

```bash
git add frontend/src/components/tutorial/sections/SectionNaiveRag.tsx frontend/src/components/tutorial/TutorialPanel.tsx
git commit -m "feat(tutorial): section 2 — naive RAG case study, conflict detection"
```

---

### Task 5: Sekcja 3 — Jak działa ingest

**Files:**
- Create: `frontend/src/components/tutorial/sections/SectionIngest.tsx`
- Modify: `frontend/src/components/tutorial/TutorialPanel.tsx`

- [ ] **Step 1: Utwórz SectionIngest.tsx**

```tsx
import { Walkthrough } from "../Walkthrough";

const STAGES = [
  { n: 1, name: "Parsowanie", type: "deterministyczny", desc: "Wyciąga czysty tekst z pliku (PDF, TXT, HTML, URL). Zero wywołań LLM.", out: "raw_text: string" },
  { n: 2, name: "Klasyfikacja źródła", type: "LLM", desc: "GPT-4 analizuje tekst: typ dokumentu, encje (osoby/org/miejsca), pojęcia, claims z polarnością i pewnością, relacje między encjami.", out: "SourceClassification: {entities[], concepts[], claims[], relations[]}" },
  { n: 3, name: "Detekcja konfliktów", type: "LLM (warunkowy)", desc: "Uruchamia się tylko gdy nowe claims dotyczą encji już istniejącej w wiki. LLM porównuje nowe claims z istniejącymi i wskazuje sprzeczności.", out: "ConflictReport: {conflicts[], severity}" },
  { n: 4, name: "Merge do wiki store", type: "deterministyczny", desc: "Nowe encje dostają pliki entity_*.md. Istniejące encje — nowe claims dopisywane do claims.jsonl z proweniencją. Relacje w edges.jsonl.", out: "wiki_data/: nowe/zaktualizowane pliki MD i JSONL" },
  { n: 5, name: "Aktualizacja indeksu", type: "deterministyczny", desc: "Regeneracja index.md (czytelny) i index.json (używany przez retrieval Stage 2). Graf relacji przebudowywany.", out: "index.md, index.json, relations_graph" },
];

export function SectionIngest() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Jak działa ingest?</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Ingest to 5-etapowy pipeline zamieniający surowy dokument w strukturalną wiedzę w wiki.
          Stage 2 zawsze wywołuje LLM. Stage 3 — tylko gdy encja już istnieje w wiki.
        </p>
      </div>

      <div className="space-y-2">
        {STAGES.map(s => (
          <div key={s.n} className="border border-border rounded-lg p-3 bg-card space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center flex-shrink-0">{s.n}</span>
              <span className="font-medium text-sm text-foreground">{s.name}</span>
              <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-mono ${s.type.startsWith("LLM") ? "bg-warning/20 text-warning" : "bg-muted text-muted-foreground"}`}>{s.type}</span>
            </div>
            <p className="text-xs text-muted-foreground pl-8">{s.desc}</p>
            <p className="text-xs font-mono text-muted-foreground/60 pl-8">→ {s.out}</p>
          </div>
        ))}
      </div>

      <Walkthrough
        steps={[
          {
            title: "Stage 1: Wgraj dokument — zero LLM",
            content: <p>Kliknij <strong>Sources → Dodaj źródło</strong>. Wgraj PDF, TXT lub podaj URL. System wyciąga tekst bez żadnych wywołań API.</p>,
            panelHint: "Sources → Dodaj źródło",
          },
          {
            title: "Stage 2: Klasyfikacja (1 wywołanie LLM)",
            content: (
              <div className="space-y-1">
                <p>LLM zwraca ustrukturyzowany JSON:</p>
                <ul className="list-disc list-inside text-xs space-y-0.5 ml-2">
                  <li>Encje: <code className="bg-muted px-1 rounded">{`[{name: 'Anthropic', type: 'organization'}]`}</code></li>
                  <li>Claims: <code className="bg-muted px-1 rounded">{`[{subject: 'Anthropic', predicate: 'founded', object: '2021'}]`}</code></li>
                  <li>Relacje: <code className="bg-muted px-1 rounded">{`[{from: 'Dario Amodei', relation: 'CEO_OF', to: 'Anthropic'}]`}</code></li>
                </ul>
              </div>
            ),
            panelHint: "Sources → [wybierz źródło] → Classification",
          },
          {
            title: "Stage 3: Detekcja konfliktów (warunkowy LLM)",
            content: <p>Jeśli Anthropic już istnieje w wiki z claimem <code className="bg-muted px-1 rounded text-xs">founded: 2022</code>, a nowe źródło mówi <code className="bg-muted px-1 rounded text-xs">founded: 2021</code> — LLM wykrywa konflikt. Sprawdź raport w Sources.</p>,
            panelHint: "Sources → Conflict Report",
          },
          {
            title: "Stage 4+5: Dane trafiają do wiki",
            content: (
              <div className="space-y-1">
                <p>Plik <code className="bg-muted px-1 rounded text-xs">wiki_data/default/entities/entity_anthropic.md</code> zawiera YAML frontmatter + claims. Otwórz <strong>Knowledge Map → Browser</strong> — nowa encja pojawi się na liście.</p>
              </div>
            ),
            panelHint: "Knowledge Map → Browser",
          },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 2: Podłącz w TutorialPanel.tsx**

```tsx
import { SectionIngest } from "./sections/SectionIngest";
// ...
{activeTab === "ingest" && <SectionIngest />}
```

- [ ] **Step 3: Weryfikacja + commit**

Tutorial → "Jak działa ingest": 5 kart stages z etykietami LLM/deterministyczny, Walkthrough 4 kroki.
`npx tsc --noEmit` — zero błędów.

```bash
git add frontend/src/components/tutorial/sections/SectionIngest.tsx frontend/src/components/tutorial/TutorialPanel.tsx
git commit -m "feat(tutorial): section 3 — ingest pipeline 5 stages with walkthrough"
```

---

### Task 6: Sekcja 4 — Jak działa retrieval

**Files:**
- Create: `frontend/src/components/tutorial/sections/SectionRetrieval.tsx`
- Modify: `frontend/src/components/tutorial/TutorialPanel.tsx`

- [ ] **Step 1: Utwórz SectionRetrieval.tsx**

```tsx
import { Walkthrough } from "../Walkthrough";

const STAGES = [
  { n: 1, name: "Intent parsing", type: "LLM", desc: "LLM analizuje pytanie: które encje, jakie pojęcia, zakres czasowy, typ zapytania (factual/comparative/temporal), czy wymagana jest proweniencja.", out: "ParsedIntent: {entities[], concepts[], time_range?, query_type}" },
  { n: 2, name: "Candidate filtering", type: "deterministyczny", desc: "Scorer przeszukuje wiki: entity pages pasujące do name/aliases, concept pages, claims z matching subject/predicate. Każdy kandydat dostaje score (0–1).", out: "Candidate[]: [{page_id, score, match_type, snippet}]" },
  { n: 3, name: "Selection", type: "LLM", desc: "LLM dostaje listę kandydatów (id + snippet) i wybiera które są relevantne. Zwraca selection z uzasadnieniem i confidence score.", out: "Selection: {selected_ids[], rationale, confidence: 0–1}" },
  { n: 4, name: "Context assembly", type: "deterministyczny", desc: "Ładuje pełną zawartość wybranych stron wiki: MD content, claims z proweniencją, relations edges. Scala w ustrukturyzowany kontekst.", out: "AssembledContext: {pages[], claims[], relations[], token_count}" },
  { n: 5, name: "Answer generation", type: "LLM", desc: "LLM generuje odpowiedź na podstawie assembled context. Cytuje encje i źródła w formacie [Entity:X] i [Source:Y]. Zwraca answer z confidence score.", out: "Answer: {text, citations[], confidence: 0–1, tokens_used}" },
];

export function SectionRetrieval() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Jak działa retrieval?</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          Retrieval to 5-etapowy pipeline zamieniający pytanie w cytowaną odpowiedź.
          Gdy confidence jest zbyt niskie lub brak kandydatów — uruchamia się <strong className="text-foreground">Agent Fallback</strong> z 10 narzędziami.
        </p>
      </div>

      <div className="space-y-2">
        {STAGES.map(s => (
          <div key={s.n} className="border border-border rounded-lg p-3 bg-card space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-primary/20 text-primary text-xs font-bold flex items-center justify-center flex-shrink-0">{s.n}</span>
              <span className="font-medium text-sm text-foreground">{s.name}</span>
              <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-mono ${s.type === "LLM" ? "bg-warning/20 text-warning" : "bg-muted text-muted-foreground"}`}>{s.type}</span>
            </div>
            <p className="text-xs text-muted-foreground pl-8">{s.desc}</p>
            <p className="text-xs font-mono text-muted-foreground/60 pl-8">→ {s.out}</p>
          </div>
        ))}
        <div className="border border-warning/30 rounded-lg p-3 bg-warning/5 space-y-1">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-warning/20 text-warning text-xs font-bold flex items-center justify-center flex-shrink-0">F</span>
            <span className="font-medium text-sm text-foreground">Agent Fallback</span>
            <span className="ml-auto text-xs px-2 py-0.5 rounded-full font-mono bg-warning/20 text-warning">10 narzędzi</span>
          </div>
          <p className="text-xs text-muted-foreground pl-8">
            Uruchamia się gdy: candidates=0, selection.confidence &lt; 0.5 lub answer.confidence &lt; 0.6.
            Agent w pętli wywołuje narzędzia (<code className="bg-muted px-1 rounded">search_entities</code>, <code className="bg-muted px-1 rounded">get_claims</code>, <code className="bg-muted px-1 rounded">get_relations</code>) aż znajdzie odpowiedź.
          </p>
        </div>
      </div>

      <Walkthrough
        steps={[
          {
            title: "Stage 1: Zadaj pytanie — obserwuj parsed intent",
            content: (
              <div className="space-y-1">
                <p>Otwórz <strong>Chat with Trace</strong> i zadaj np. <em>"Jaką rolę pełni Dario Amodei w Anthropic od 2023?"</em></p>
                <p>Trace Stage 1: <code className="bg-muted px-1 rounded text-xs">{`entities: ['Dario Amodei', 'Anthropic'], time_range: {start: 2023}`}</code></p>
              </div>
            ),
            panelHint: "Chat with Trace → Stage 1",
          },
          {
            title: "Stage 2: Candidate filtering — ile stron wiki pasuje?",
            content: <p>Scorer przeszukuje wiki: <code className="bg-muted px-1 rounded text-xs">entity_dario_amodei.md</code>, <code className="bg-muted px-1 rounded text-xs">entity_anthropic.md</code>, claims z pasującym subject i predykatem. Trace pokazuje liczbę kandydatów i score.</p>,
            panelHint: "Chat with Trace → Stage 2",
          },
          {
            title: "Stage 3: Selection — LLM wybiera najlepsze",
            content: <p>LLM decyduje które strony wiki są naprawdę relevantne. Trace pokazuje selection.confidence — jeśli &lt; 0.5, włączy się Agent Fallback.</p>,
            panelHint: "Chat with Trace → Stage 3",
          },
          {
            title: "Stage 5: Answer z cytatami",
            content: <p>Odpowiedź zawiera <code className="bg-muted px-1 rounded text-xs">[Entity:Dario Amodei]</code> i <code className="bg-muted px-1 rounded text-xs">[Source:raport_2024]</code>. Trace pokazuje pełny assembled context który dostał LLM.</p>,
            panelHint: "Chat with Trace → Stage 5",
          },
          {
            title: "Agent Fallback — gdy retrieval zawodzi",
            content: <p>Gdy candidates=0 lub confidence niskie, Trace pokazuje sekcję <strong>Agent</strong> z wywołanymi narzędziami: np. <code className="bg-muted px-1 rounded text-xs">search_entities('Dario Amodei')</code> → <code className="bg-muted px-1 rounded text-xs">get_claims('entity_dario_amodei')</code>.</p>,
            panelHint: "Chat with Trace → Agent Fallback",
          },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 2: Podłącz w TutorialPanel.tsx**

```tsx
import { SectionRetrieval } from "./sections/SectionRetrieval";
// ...
{activeTab === "retrieval" && <SectionRetrieval />}
```

- [ ] **Step 3: Weryfikacja + commit**

Tutorial → "Jak działa retrieval": 5 kart stages + 1 karta Agent Fallback (żółta), Walkthrough 5 kroków.
`npx tsc --noEmit` — zero błędów.

```bash
git add frontend/src/components/tutorial/sections/SectionRetrieval.tsx frontend/src/components/tutorial/TutorialPanel.tsx
git commit -m "feat(tutorial): section 4 — retrieval pipeline 5 stages + agent fallback"
```

---

### Task 7: Sekcja 5 — Jak efektywnie pytać

**Files:**
- Create: `frontend/src/components/tutorial/sections/SectionQuerying.tsx`
- Modify: `frontend/src/components/tutorial/TutorialPanel.tsx`

- [ ] **Step 1: Utwórz SectionQuerying.tsx**

```tsx
import { Walkthrough } from "../Walkthrough";

const EXAMPLES = [
  { bad: "Co to jest AI?", good: "Jak OpenAI zdefiniował bezpieczeństwo AI w dokumentach z 2023?", reason: "Konkretna encja + zakres czasowy" },
  { bad: "Opowiedz o projekcie", good: "Jakie kamienie milowe osiągnął projekt X w Q3 2024?", reason: "Encja + temporal scope" },
  { bad: "Dlaczego firma upadła?", good: "Jakie przyczyny upadku firmy Y podaje Raport Roczny 2023 vs. artykuł Z?", reason: "Porównanie konkretnych źródeł" },
  { bad: "Kto kieruje firmą?", good: "Kto jest CEO Anthropic według dokumentów z 2024?", reason: "Encja + rola + rok" },
  { bad: "Powiedz mi wszystko o X", good: "Jakie są claims dotyczące przychodów firmy X z lat 2022–2024?", reason: "Zakres tematyczny + temporal" },
];

export function SectionQuerying() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Jak efektywnie pytać?</h2>
        <p className="text-sm text-muted-foreground leading-relaxed">
          KM RAG działa najlepiej z pytaniami zawierającymi konkretne encje, zakres czasowy
          lub proszącymi o porównanie źródeł. Niejasne pytania dają słabsze wyniki — Stage 1 intent parser
          nie może wyekstrahować precyzyjnych filtrów.
        </p>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Zasady skutecznych pytań</h3>
        {[
          ["Wymieniaj konkretne encje", "Zamiast 'firma' pisz 'Anthropic'. System szuka po nazwie i aliasach w wiki."],
          ["Dodaj zakres czasowy", "'w 2023', 'od Q1 do Q3 2024', 'po 2020' — Stage 1 ekstrahuje time_range i filtruje claims."],
          ["Pytaj o relacje wprost", "'Jak X i Y są powiązane?' → retrieval przeszukuje edges.jsonl."],
          ["Proś o porównanie źródeł", "'Co mówi dokument A vs. B o X?' → claims z obu proweniencji."],
          ["Pytaj o sprzeczności", "'Które źródła się nie zgadzają w kwestii X?' → conflict_detector oznaczył je podczas ingestu."],
        ].map(([rule, desc]) => (
          <div key={rule} className="flex gap-3 border border-border rounded-lg p-3 bg-card">
            <span className="text-primary mt-0.5 flex-shrink-0 text-sm">→</span>
            <div>
              <p className="text-sm font-medium text-foreground">{rule}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Przykłady: słabe vs. dobre pytania</h3>
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-muted">
              <th className="px-3 py-2 text-left border border-border text-destructive">Słabe pytanie</th>
              <th className="px-3 py-2 text-left border border-border text-primary">Lepsze pytanie</th>
              <th className="px-3 py-2 text-left border border-border">Dlaczego?</th>
            </tr>
          </thead>
          <tbody>
            {EXAMPLES.map(({ bad, good, reason }) => (
              <tr key={bad} className="border-b border-border odd:bg-card even:bg-muted/20">
                <td className="px-3 py-2 border border-border text-muted-foreground italic">{bad}</td>
                <td className="px-3 py-2 border border-border text-foreground">{good}</td>
                <td className="px-3 py-2 border border-border text-muted-foreground">{reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Walkthrough
        steps={[
          {
            title: "Krok 1: Sprawdź co masz w wiki przed pytaniem",
            content: <p>Otwórz <strong>Knowledge Map → Browser</strong>. Pytanie o encję której nie ma w wiki da słaby wynik lub uruchomi agent fallback bez odpowiedzi.</p>,
            panelHint: "Knowledge Map → Browser",
          },
          {
            title: "Krok 2: Sformułuj pytanie z konkretną encją",
            content: (
              <div className="space-y-1">
                <p>Zamiast: <em className="text-muted-foreground">"Kto zarządza firmą?"</em></p>
                <p>Napisz: <em className="text-foreground font-medium">"Kto jest CEO firmy Anthropic według dokumentów z 2024?"</em></p>
                <p>Stage 1: <code className="bg-muted px-1 rounded text-xs">{`entities: ['Anthropic'], time_range: {start: 2024}`}</code></p>
              </div>
            ),
            panelHint: "Chat with Trace",
          },
          {
            title: "Krok 3: Analizuj Stage 1 trace jeśli odpowiedź jest słaba",
            content: <p>Jeśli odpowiedź niejasna — sprawdź Stage 1 trace. Czy system poprawnie wyekstrahował encje? Jeśli nie — przeformułuj pytanie z dokładniejszymi nazwami.</p>,
            panelHint: "Chat with Trace → Stage 1",
          },
          {
            title: "Krok 4: Sprawdź Stage 2 jeśli brakuje informacji",
            content: <p>Jeśli odpowiedź mówi 'nie znaleziono' — sprawdź Stage 2 trace. Ile kandydatów? Jeśli 0 — informacja nie jest w wiki. Dodaj więcej źródeł w <strong>Sources</strong>.</p>,
            panelHint: "Chat with Trace → Stage 2",
          },
        ]}
      />
    </div>
  );
}
```

- [ ] **Step 2: Podłącz w TutorialPanel.tsx**

```tsx
import { SectionQuerying } from "./sections/SectionQuerying";
// ...
{activeTab === "querying" && <SectionQuerying />}
```

- [ ] **Step 3: Weryfikacja + commit**

Tutorial → "Jak pytać": 5 kart zasad, tabela 5 wierszy, Walkthrough 4 kroki.
`npx tsc --noEmit` — zero błędów.

```bash
git add frontend/src/components/tutorial/sections/SectionQuerying.tsx frontend/src/components/tutorial/TutorialPanel.tsx
git commit -m "feat(tutorial): section 5 — querying best practices, examples table"
```

---

### Task 8: Sekcja 6 — Interaktywne przewodniki

**Files:**
- Create: `frontend/src/components/tutorial/sections/SectionWalkthroughs.tsx`
- Modify: `frontend/src/components/tutorial/TutorialPanel.tsx`

- [ ] **Step 1: Utwórz SectionWalkthroughs.tsx**

```tsx
import { useState } from "react";
import { Walkthrough, WalkthroughStep } from "../Walkthrough";

interface GuidedWalkthrough {
  id: string;
  icon: string;
  title: string;
  description: string;
  steps: WalkthroughStep[];
}

const WALKTHROUGHS: GuidedWalkthrough[] = [
  {
    id: "first-source",
    icon: "📄",
    title: "Dodaj pierwsze źródło",
    description: "Wgraj dokument i obserwuj jak system buduje wiedzę strukturalną.",
    steps: [
      {
        title: "Otwórz panel Sources",
        content: <p>Kliknij <strong>Sources</strong> w sidebarze. Zobaczysz listę wgranych źródeł (może być pusta przy pierwszej sesji).</p>,
        panelHint: "Sources",
      },
      {
        title: "Wgraj dokument lub wklej URL",
        content: <p>Kliknij <strong>Dodaj źródło</strong>. Możesz wgrać PDF/TXT lub wkleić URL artykułu. Przykład: URL wpisu blogowego o AI lub PDF raportu rocznego firmy.</p>,
        panelHint: "Sources → Dodaj źródło",
      },
      {
        title: "Obserwuj 5 etapów ingestu",
        content: <p>Pasek postępu: Parsowanie → Klasyfikacja (LLM, ~3–5 sek.) → Detekcja konfliktów → Merge → Index. Po zakończeniu źródło ma status <strong>ingested</strong>.</p>,
        panelHint: "Sources → [postęp ingestu]",
      },
      {
        title: "Przejrzyj classification result",
        content: <p>Kliknij wgrane źródło → zakładka <strong>Classification</strong>. Zobaczysz co LLM wyekstrahował: encje, pojęcia, claims, relacje. Sprawdź confidence scores.</p>,
        panelHint: "Sources → Classification",
      },
      {
        title: "Otwórz Knowledge Map — nowe węzły!",
        content: <p>Przejdź do <strong>Knowledge Map → Graph</strong>. Nowe encje powinny pojawić się jako węzły. Kliknij węzeł — zobaczysz claims z proweniencją na Twój dokument.</p>,
        panelHint: "Knowledge Map → Graph",
      },
    ],
  },
  {
    id: "query-trace",
    icon: "💬",
    title: "Zadaj pytanie i analizuj trace",
    description: "Poznaj retrieval pipeline od środka — obserwuj każdy z 5 etapów.",
    steps: [
      {
        title: "Otwórz Chat with Trace",
        content: <p>Kliknij <strong>Chat with Trace</strong> w sidebarze. Upewnij się że masz wgrane co najmniej jedno źródło — retrieval potrzebuje danych w wiki.</p>,
        panelHint: "Chat with Trace",
      },
      {
        title: "Zadaj precyzyjne pytanie",
        content: (
          <div className="space-y-1">
            <p>Wpisz pytanie z konkretną encją z Twojej wiki. Przykłady:</p>
            <ul className="list-disc list-inside text-xs ml-2 space-y-0.5">
              <li><em>"Jaką rolę pełni [osoba] w [organizacji]?"</em></li>
              <li><em>"Kiedy [firma] ogłosiła [produkt]?"</em></li>
              <li><em>"Które źródła mówią o [temacie] z różnych perspektyw?"</em></li>
            </ul>
          </div>
        ),
        panelHint: "Chat with Trace → pole wpisywania",
      },
      {
        title: "Stage 1: Sprawdź parsed intent",
        content: <p>Rozwiń <strong>Stage 1 — Intent</strong>. Sprawdź czy system poprawnie wyekstrahował encje i zakres czasowy. Jeśli nie — przeformułuj pytanie z dokładniejszymi nazwami.</p>,
        panelHint: "Chat with Trace → Stage 1",
      },
      {
        title: "Stage 2–3: Kandydaci i selekcja",
        content: <p>Sprawdź ile kandydatów znaleziono w Stage 2 i które LLM wybrał w Stage 3. Jeśli candidates=0 — brak danych w wiki dla tego pytania.</p>,
        panelHint: "Chat with Trace → Stage 2 + 3",
      },
      {
        title: "Stage 5: Cytowana odpowiedź + Agent Fallback",
        content: <p>Odpowiedź Stage 5 zawiera cytaty <code className="bg-muted px-1 rounded text-xs">[Entity:X]</code> i <code className="bg-muted px-1 rounded text-xs">[Source:Y]</code>. Jeśli uruchomił się Agent — zobaczysz sekcję <strong>Agent</strong> z krokami narzędzi.</p>,
        panelHint: "Chat with Trace → Stage 5 + Agent",
      },
    ],
  },
  {
    id: "lint-fix",
    icon: "🔍",
    title: "Uruchom lint i napraw problem",
    description: "Sprawdź jakość bazy wiedzy — wykryj i napraw problemy automatycznie.",
    steps: [
      {
        title: "Otwórz Lint",
        content: <p>Kliknij <strong>Lint</strong> w sidebarze. Zobaczysz przycisk <strong>Run Lint</strong> i ewentualnie wyniki z poprzedniej sesji.</p>,
        panelHint: "Lint",
      },
      {
        title: "Uruchom Tier 1 + 2 checks",
        content: (
          <div className="space-y-1">
            <p>Kliknij <strong>Run Lint</strong>. System sprawdza 3 grupy:</p>
            <ul className="list-disc list-inside text-xs ml-2 space-y-0.5">
              <li><strong>Proweniencja</strong> (Tier 1): claims bez źródła, brakujące pola</li>
              <li><strong>Integralność</strong> (Tier 2): zduplikowane encje, puste opisy</li>
              <li><strong>Nawigacja</strong> (Tier 2): brakujące linki zwrotne</li>
            </ul>
          </div>
        ),
        panelHint: "Lint → Run Lint",
      },
      {
        title: "Przejrzyj issues — kliknij aby zobaczyć szczegóły",
        content: <p>Każdy problem pokazuje typ (np. <code className="bg-muted px-1 rounded text-xs">empty_description</code>), opis i dotkniętą stronę wiki. Kliknij issue — rozwinie się z sugerowaną poprawką.</p>,
        panelHint: "Lint → lista issues",
      },
      {
        title: "Zastosuj auto-fix",
        content: <p>Przy problemach z <strong>Auto-fix</strong> — kliknij przycisk naprawy. System stosuje zmianę do pliku wiki i odświeża listę. Problemy wymagające ręcznej decyzji (np. <code className="bg-muted px-1 rounded text-xs">unmarked_contradiction</code>) mają tylko reject/wontfix.</p>,
        panelHint: "Lint → [issue] → Auto-fix",
      },
      {
        title: "Włącz Semantic checks (Tier 3)",
        content: <p>Zaznacz checkbox <strong>Semantic checks</strong> i uruchom lint ponownie. Tier 3 sprawdza (LLM): sprzeczności nieoznaczone, kolizje aliasów, brakujące pojęcia, zdezaktualizowane podsumowania. Może potrwać kilka sekund.</p>,
        panelHint: "Lint → Semantic checks toggle",
      },
    ],
  },
];

export function SectionWalkthroughs() {
  const [active, setActive] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-lg font-semibold">Interaktywne przewodniki</h2>
        <p className="text-sm text-muted-foreground">
          Krok-po-kroku przez najważniejsze przepływy pracy. Wybierz przewodnik i wykonuj kroki razem z aplikacją.
        </p>
      </div>

      <div className="space-y-3">
        {WALKTHROUGHS.map(wt => (
          <div key={wt.id} className="border border-border rounded-lg overflow-hidden bg-card">
            <button
              onClick={() => setActive(active === wt.id ? null : wt.id)}
              className="w-full flex items-center gap-3 p-4 text-left hover:bg-muted/40 transition-colors"
            >
              <span className="text-xl">{wt.icon}</span>
              <div className="flex-1">
                <p className="font-medium text-sm text-foreground">{wt.title}</p>
                <p className="text-xs text-muted-foreground">{wt.description}</p>
              </div>
              <span className="text-muted-foreground text-xs">{active === wt.id ? "▲" : "▼"}</span>
            </button>
            {active === wt.id && (
              <div className="border-t border-border px-4 pb-4">
                <Walkthrough steps={wt.steps} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Podłącz w TutorialPanel.tsx**

```tsx
import { SectionWalkthroughs } from "./sections/SectionWalkthroughs";
// ...
{activeTab === "walkthroughs" && <SectionWalkthroughs />}
```

- [ ] **Step 3: Weryfikacja + commit**

Tutorial → "Przewodniki": 3 karty collapse/expand. Kliknij każdą — otwiera Walkthrough. Kliknij ponownie — zamyka. Każdy Walkthrough ma 5 kroków.
`npx tsc --noEmit` — zero błędów.

```bash
git add frontend/src/components/tutorial/sections/SectionWalkthroughs.tsx frontend/src/components/tutorial/TutorialPanel.tsx
git commit -m "feat(tutorial): section 6 — 3 interactive guided walkthroughs"
```

---

### Task 9: Finalizacja TutorialPanel

**Files:**
- Modify: `frontend/src/components/tutorial/TutorialPanel.tsx`

- [ ] **Step 1: Zastąp placeholdery finalnymi importami**

```tsx
import { useState } from "react";
import { SectionIntro } from "./sections/SectionIntro";
import { SectionNaiveRag } from "./sections/SectionNaiveRag";
import { SectionIngest } from "./sections/SectionIngest";
import { SectionRetrieval } from "./sections/SectionRetrieval";
import { SectionQuerying } from "./sections/SectionQuerying";
import { SectionWalkthroughs } from "./sections/SectionWalkthroughs";

type TabId = "intro" | "naive-rag" | "ingest" | "retrieval" | "querying" | "walkthroughs";

const TABS: { id: TabId; label: string }[] = [
  { id: "intro", label: "Knowledge Map RAG" },
  { id: "naive-rag", label: "Dlaczego nie naive RAG" },
  { id: "ingest", label: "Jak działa ingest" },
  { id: "retrieval", label: "Jak działa retrieval" },
  { id: "querying", label: "Jak pytać" },
  { id: "walkthroughs", label: "Przewodniki" },
];

export function TutorialPanel() {
  const [activeTab, setActiveTab] = useState<TabId>("intro");

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-foreground mb-1">RAG 2.0 — Knowledge Map</h1>
        <p className="text-muted-foreground text-sm">Kompletny przewodnik systemu opartego na wiedzy strukturalnej.</p>
      </div>

      <div className="flex gap-0.5 flex-wrap border-b border-border mb-6">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2 text-sm rounded-t transition-colors border-b-2 -mb-px ${
              activeTab === tab.id
                ? "border-primary text-primary font-medium bg-primary/5"
                : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/40"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "intro" && <SectionIntro />}
      {activeTab === "naive-rag" && <SectionNaiveRag />}
      {activeTab === "ingest" && <SectionIngest />}
      {activeTab === "retrieval" && <SectionRetrieval />}
      {activeTab === "querying" && <SectionQuerying />}
      {activeTab === "walkthroughs" && <SectionWalkthroughs />}
    </div>
  );
}
```

- [ ] **Step 2: Upewnij się że żaden plik nie importuje starych helperów z TutorialPanel**

```bash
grep -rn "from.*TutorialPanel" frontend/src --include="*.tsx" --include="*.ts"
```

Oczekiwane: zero wyników (stare helpery `Step`, `PipelineStep`, `Pre`, `Code`, `Note` zostały usunięte z pliku — nie były eksportowane, więc żaden inny plik nie mógł ich importować).

- [ ] **Step 3: Pełna weryfikacja manualna**

Przejdź przez każdą zakładkę:
1. **Knowledge Map RAG** — tabela 5 wierszy + Walkthrough 4 kroki
2. **Dlaczego nie naive RAG** — czerwony/niebieski blok + Walkthrough 4 kroki
3. **Jak działa ingest** — 5 kart stages + Walkthrough 4 kroki
4. **Jak działa retrieval** — 5 kart + Agent Fallback + Walkthrough 5 kroków
5. **Jak pytać** — 5 kart zasad + tabela + Walkthrough 4 kroki
6. **Przewodniki** — 3 collapse'y, każdy z Walkthroughiem 5 kroków

W każdej zakładce: kliknij wszystkie kroki Walkthrough (Dalej/Wstecz/kropki).

`npx tsc --noEmit` — zero błędów.

- [ ] **Step 4: Commit i tag**

```bash
git add frontend/src/components/tutorial/TutorialPanel.tsx
git commit -m "feat(tutorial): finalize Phase 8 — 6-section KM RAG tutorial with walkthroughs"
git tag phase-8-complete
```

---

## Self-review

**Spec coverage:**
- [x] Knowledge map RAG section → Task 3 (SectionIntro)
- [x] Why not naive RAG (case study with hard test) → Task 4 (Anthropic founding date conflict)
- [x] How ingest works → Task 5 (5 stages, LLM vs. deterministyczny)
- [x] How retrieval works → Task 6 (5 stages + Agent Fallback)
- [x] How to query effectively → Task 7 (zasady + tabela przykładów)
- [x] Interactive walkthroughs → każda sekcja ma `<Walkthrough>`, Task 8 to dedykowana sekcja z 3 guided walkthroughami
- [x] Done criterion "each section has click-through demo" → każda z 6 sekcji renderuje `<Walkthrough>` component

**Placeholder scan:** Brak TBD/TODO/placeholder — każda sekcja ma kompletną treść w kodzie.

**Type consistency:**
- `WalkthroughStep` eksportowany z `Walkthrough.tsx`, importowany przez `SectionWalkthroughs.tsx` — spójne
- `TabId` zdefiniowany i używany tylko w `TutorialPanel.tsx` — spójne
- Nazwy eksportów (`SectionIntro`, `SectionNaiveRag`, etc.) zgodne z importami w `TutorialPanel.tsx`
