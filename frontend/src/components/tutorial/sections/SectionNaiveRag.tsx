import { Walkthrough } from "../Walkthrough";

export function SectionNaiveRag() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Why naive RAG fails</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Naive RAG is fine for a simple single-fact lookup. It breaks down when a question needs
          <strong className="text-foreground"> synthesis across sources</strong>,
          <strong className="text-foreground"> tracking a contradiction</strong>, or
          <strong className="text-foreground"> temporal reasoning</strong>.
        </p>
      </div>

      <div className="space-y-3 rounded-lg border border-error/30 bg-error/5 p-4">
        <p className="text-xs font-semibold text-error">Case study — a hard question</p>
        <p className="rounded border border-border bg-background p-3 font-mono text-sm text-foreground">
          "Which sources give different founding dates for Anthropic — and which one is more current?"
        </p>
        <div className="space-y-2">
          <p className="text-xs font-semibold text-foreground">Why naive RAG can't answer it:</p>
          <ul className="list-none space-y-1.5 text-xs text-muted-foreground">
            {[
              ["Chunking cuts the context", "\"Anthropic founded in 2021\" might sit in chunk A and \"in 2022\" in chunk B — they never reach the prompt together"],
              ["No entity linking", "Both chunks are about the same company, but the vector store doesn't know that"],
              ["No provenance", "You can't tell which source (Report A vs. Article B) gave which date"],
              ["No recency comparison", "Cosine similarity ignores publication dates — nothing says which document is newer"],
            ].map(([problem, explanation]) => (
              <li key={problem} className="flex gap-2">
                <span className="mt-0.5 flex-shrink-0 text-error">✗</span>
                <span><strong className="text-foreground">{problem}:</strong> {explanation}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="space-y-3 rounded-lg border border-primary/30 bg-primary/5 p-4">
        <p className="text-xs font-semibold text-primary">How KM RAG handles it</p>
        <ul className="list-none space-y-1.5 text-xs text-muted-foreground">
          {[
            ["Ingest stage 3 catches the conflict", "The LLM sees a new claim \"founded in 2022\", compares it to the existing \"founded in 2021\", and files a conflict report"],
            ["Claims carry provenance", "Every claim: {source_id: 'report_a', date_extracted: '2024-01', confidence: 0.9}"],
            ["Retrieval stage 1 parses intent", "Question → ParsedIntent: {entities: ['Anthropic'], query_type: 'comparison', requires_provenance: true}"],
            ["The answer generator cites both sources", "\"Report A (2021) says 2021, Article B (2024) says 2022 — the newer one points to 2022\""],
          ].map(([step, explanation]) => (
            <li key={step} className="flex gap-2">
              <span className="mt-0.5 flex-shrink-0 text-primary">✓</span>
              <span><strong className="text-foreground">{step}:</strong> {explanation}</span>
            </li>
          ))}
        </ul>
      </div>

      <Walkthrough
        steps={[
          {
            title: "Picture two documents that disagree",
            content: (
              <div className="space-y-2">
                <p>Document A (2021): <em>"Anthropic Inc. was founded in February 2021 by former OpenAI staff."</em></p>
                <p>Document B (2024): <em>"Anthropic, founded in 2022, announced…"</em></p>
              </div>
            ),
          },
          {
            title: "In naive RAG the chunks land separately in the vector store",
            content: (
              <p>"When was Anthropic founded?" → cosine similarity → top-K. You might get one chunk, or both with nothing to say which is more reliable. The answer comes out inconsistent.</p>
            ),
          },
          {
            title: "In KM RAG the conflict detector catches it at ingest",
            content: (
              <p>After Document B is ingested, stage 3 finds that the new claim <code className="rounded bg-muted px-1 text-xs">founded_date: 2022</code> collides with the existing <code className="rounded bg-muted px-1 text-xs">founded_date: 2021</code>. The conflict report shows up in Sources.</p>
            ),
            panelHint: "Sources → Conflict Report",
          },
          {
            title: "Ask in Wiki Chat — retrieval pulls both claims with provenance",
            content: (
              <p>Ask: <em>"Which sources give different founding dates for Anthropic?"</em> — stage 1 parses the intent → stage 2 pulls the Anthropic wiki page with both claims → stage 5 cites both sources with their publication dates.</p>
            ),
            panelHint: "Wiki Chat",
          },
        ]}
      />
    </div>
  );
}
