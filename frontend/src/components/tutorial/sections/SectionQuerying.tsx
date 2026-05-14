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
