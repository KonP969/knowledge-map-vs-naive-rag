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
            title: "Stage 4: Context assembly — co LLM dostaje",
            content: <p>System ładuje pełną zawartość wybranych stron wiki: treść MD, claims z proweniencją, relacje. Trace w Stage 4 pokazuje <code className="bg-muted px-1 rounded text-xs">token_count</code> — jeśli zbyt duży, context jest przycinany do limitu modelu.</p>,
            panelHint: "Chat with Trace → Stage 4",
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
