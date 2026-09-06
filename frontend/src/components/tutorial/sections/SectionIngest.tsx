import { Walkthrough } from "../Walkthrough";

const STAGES = [
  { n: 1, name: "Parse", type: "deterministic", desc: "Pulls clean text out of the file (PDF, DOCX, TXT, MD, or a crawled URL). No LLM calls.", out: "raw_text: string" },
  { n: 2, name: "Classify", type: "LLM", desc: "The model reads the text: document type, entities (people / orgs / places), concepts, claims with polarity and confidence, and edges between entities.", out: "SourceClassification: {entities[], concepts[], claims[], relations[]}" },
  { n: 3, name: "Conflict detection", type: "LLM (conditional)", desc: "Runs only when the new claims touch an entity already in the wiki. The model compares the new claims against the existing ones and flags contradictions.", out: "ConflictReport: {conflicts[], severity}" },
  { n: 4, name: "Merge into the wiki store", type: "deterministic", desc: "New entities get their own entity_*.md files. Existing entities get their new claims appended to claims.jsonl with provenance. Edges go to edges.jsonl.", out: "wiki_data/: new / updated MD and JSONL files" },
  { n: 5, name: "Reindex", type: "deterministic", desc: "Regenerates index.md (human-readable) and index.json (used by retrieval stage 2). The edge graph is rebuilt.", out: "index.md, index.json, edge graph" },
];

export function SectionIngest() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">How ingest works</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Ingest is a 5-stage pipeline that turns a raw document into structured knowledge.
          Stage 2 always calls the LLM. Stage 3 runs only when the entity already exists in the wiki.
        </p>
      </div>

      <div className="space-y-2">
        {STAGES.map((s) => (
          <div key={s.n} className="space-y-1 rounded-lg border border-border bg-card p-3">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary">{s.n}</span>
              <span className="text-sm font-medium text-foreground">{s.name}</span>
              <span className={`ml-auto rounded-full px-2 py-0.5 font-mono text-xs ${s.type.startsWith("LLM") ? "bg-warning/20 text-warning" : "bg-muted text-muted-foreground"}`}>{s.type}</span>
            </div>
            <p className="pl-8 text-xs text-muted-foreground">{s.desc}</p>
            <p className="pl-8 font-mono text-xs text-muted-foreground/60">→ {s.out}</p>
          </div>
        ))}
      </div>

      <Walkthrough
        steps={[
          {
            title: "Stage 1: add a document — no LLM",
            content: <p>Go to <strong>Sources</strong> and drop in a PDF, DOCX, TXT, or MD file, or import from a URL. The text is extracted with zero API calls.</p>,
            panelHint: "Sources",
          },
          {
            title: "Stage 2: classify (one LLM call)",
            content: (
              <div className="space-y-1">
                <p>The model returns structured JSON:</p>
                <ul className="ml-2 list-inside list-disc space-y-0.5 text-xs">
                  <li>Entities: <code className="rounded bg-muted px-1">{`[{name: 'Anthropic', type: 'organization'}]`}</code></li>
                  <li>Claims: <code className="rounded bg-muted px-1">{`[{subject: 'Anthropic', predicate: 'founded', object: '2021'}]`}</code></li>
                  <li>Edges: <code className="rounded bg-muted px-1">{`[{from: 'Dario Amodei', relation: 'CEO_OF', to: 'Anthropic'}]`}</code></li>
                </ul>
              </div>
            ),
            panelHint: "Sources → pick a source → Classification",
          },
          {
            title: "Stage 3: conflict detection (conditional LLM)",
            content: <p>If Anthropic is already in the wiki with a claim <code className="rounded bg-muted px-1 text-xs">founded: 2022</code> and the new source says <code className="rounded bg-muted px-1 text-xs">founded: 2021</code>, the model flags the conflict. Check the report in Sources.</p>,
            panelHint: "Sources → Conflict Report",
          },
          {
            title: "Stages 4 + 5: it lands in the wiki",
            content: (
              <div className="space-y-1">
                <p>The file <code className="rounded bg-muted px-1 text-xs">wiki_data/default/wiki/20-Entities/&lt;type&gt;/anthropic.md</code> holds the YAML frontmatter and its claims. Open <strong>Knowledge Map → Browser</strong> — the new entity is in the list.</p>
              </div>
            ),
            panelHint: "Knowledge Map → Browser",
          },
        ]}
      />
    </div>
  );
}
