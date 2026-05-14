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
