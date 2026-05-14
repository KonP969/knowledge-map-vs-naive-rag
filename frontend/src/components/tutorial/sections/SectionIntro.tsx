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
