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
