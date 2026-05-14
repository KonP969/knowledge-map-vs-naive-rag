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
