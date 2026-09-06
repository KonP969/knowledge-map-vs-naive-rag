import { Walkthrough } from "../Walkthrough";

const STAGES = [
  { n: 1, name: "Intent parsing", type: "LLM", desc: "The model reads the question: which entities, which concepts, any time range, the query type (fact / comparison / temporal), and whether provenance is required.", out: "ParsedIntent: {entities[], concepts[], time_range?, query_type}" },
  { n: 2, name: "Candidate filtering", type: "deterministic", desc: "A scorer searches the wiki: entity pages matching name/aliases, concept pages, claims with a matching subject/predicate. Each candidate gets a score (0–1). A semantic pass over claim embeddings runs alongside it.", out: "Candidate[]: [{page_id, score, match_type, snippet}]" },
  { n: 3, name: "Selection", type: "LLM", desc: "The model gets the candidate list (id + snippet) and picks the relevant ones, returning a rationale and a confidence score.", out: "Selection: {selected_ids[], rationale, confidence: 0–1}" },
  { n: 4, name: "Context assembly", type: "deterministic", desc: "Loads the full content of the selected pages: the Markdown, the claims with provenance, the edges. Merges it into a structured context.", out: "AssembledContext: {pages[], claims[], relations[], token_count}" },
  { n: 5, name: "Answer generation", type: "LLM", desc: "The model writes the answer from the assembled context, citing every claim it uses as [claim:cl_…] or [source:src_…], and returns a confidence score.", out: "Answer: {text, citations[], confidence: 0–1, tokens_used}" },
];

export function SectionRetrieval() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">How retrieval works</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Retrieval is a 5-stage pipeline that turns a question into a cited answer.
          When confidence is too low or there are no candidates, a 10-tool <strong className="text-foreground">agent fallback</strong> takes over.
        </p>
      </div>

      <div className="space-y-2">
        {STAGES.map((s) => (
          <div key={s.n} className="space-y-1 rounded-lg border border-border bg-card p-3">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary">{s.n}</span>
              <span className="text-sm font-medium text-foreground">{s.name}</span>
              <span className={`ml-auto rounded-full px-2 py-0.5 font-mono text-xs ${s.type === "LLM" ? "bg-warning/20 text-warning" : "bg-muted text-muted-foreground"}`}>{s.type}</span>
            </div>
            <p className="pl-8 text-xs text-muted-foreground">{s.desc}</p>
            <p className="pl-8 font-mono text-xs text-muted-foreground/60">→ {s.out}</p>
          </div>
        ))}
        <div className="space-y-1 rounded-lg border border-warning/30 bg-warning/5 p-3">
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-warning/20 text-xs font-bold text-warning">F</span>
            <span className="text-sm font-medium text-foreground">Agent fallback</span>
            <span className="ml-auto rounded-full bg-warning/20 px-2 py-0.5 font-mono text-xs text-warning">10 tools</span>
          </div>
          <p className="pl-8 text-xs text-muted-foreground">
            Triggers when candidates = 0, selection.confidence &lt; 0.5, or answer.confidence &lt; 0.6.
            The agent loops over tools (<code className="rounded bg-muted px-1">search_entities</code>, <code className="rounded bg-muted px-1">get_claims</code>, <code className="rounded bg-muted px-1">get_relations</code>) until it has an answer.
          </p>
        </div>
      </div>

      <Walkthrough
        steps={[
          {
            title: "Stage 1: ask a question — watch the parsed intent",
            content: (
              <div className="space-y-1">
                <p>Open <strong>Wiki Chat</strong> and ask something like <em>"What role has Dario Amodei held at Anthropic since 2023?"</em></p>
                <p>Stage 1 trace: <code className="rounded bg-muted px-1 text-xs">{`entities: ['Dario Amodei', 'Anthropic'], time_range: {start: 2023}`}</code></p>
              </div>
            ),
            panelHint: "Wiki Chat → Intent Parser",
          },
          {
            title: "Stage 2: candidate filtering — how many pages match?",
            content: <p>The scorer searches the wiki: the Dario Amodei and Anthropic entity pages, plus claims with a matching subject and predicate. The trace shows the candidate count and scores.</p>,
            panelHint: "Wiki Chat → Candidate Filter",
          },
          {
            title: "Stage 3: selection — the LLM picks the best",
            content: <p>The model decides which pages are actually relevant. The trace shows selection.confidence — below 0.5 and the agent fallback kicks in.</p>,
            panelHint: "Wiki Chat → Selection",
          },
          {
            title: "Stage 4: context assembly — what the model gets",
            content: <p>The system loads the full content of the selected pages: the Markdown, claims with provenance, edges. The stage-4 trace shows the <code className="rounded bg-muted px-1 text-xs">token_count</code> — if it's too big, the context is trimmed to the model's limit.</p>,
            panelHint: "Wiki Chat → Context Assembly",
          },
          {
            title: "Stage 5: the answer, with citations",
            content: <p>The answer carries <code className="rounded bg-muted px-1 text-xs">[claim:cl_042]</code> and <code className="rounded bg-muted px-1 text-xs">[source:src_003]</code> markers. Expand a source in the answer to see the exact claims it cited.</p>,
            panelHint: "Wiki Chat → Answer Generator",
          },
          {
            title: "Agent fallback — when retrieval comes up short",
            content: <p>When candidates = 0 or confidence is low, the trace shows an <strong>Agent</strong> section with the tool calls it made, e.g. <code className="rounded bg-muted px-1 text-xs">search_entities('Dario Amodei')</code> → <code className="rounded bg-muted px-1 text-xs">get_claims('entity:e_017')</code>.</p>,
          },
        ]}
      />
    </div>
  );
}
