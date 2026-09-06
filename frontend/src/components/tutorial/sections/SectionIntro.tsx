import { Walkthrough } from "../Walkthrough";

export function SectionIntro() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">What is Knowledge-Map RAG?</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          Knowledge-Map RAG answers questions from <strong className="text-foreground">structured knowledge</strong> rather
          than vector similarity. At ingest time it builds a graph — entities, concepts, claims (each with provenance),
          and edges. Instead of the top-K chunks, an answer cites specific claims from that graph.
        </p>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-border bg-error/5 p-4">
            <p className="mb-2 text-xs font-semibold text-error">Naive RAG</p>
            <ol className="list-inside list-decimal space-y-1 text-xs text-muted-foreground">
              <li>Split the document into chunks</li>
              <li>Embed each chunk into a vector</li>
              <li>Store the vectors</li>
              <li>Query → cosine similarity → top-K</li>
              <li>Stuff the chunks into the prompt → answer</li>
            </ol>
          </div>
          <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
            <p className="mb-2 text-xs font-semibold text-primary">Knowledge-Map RAG</p>
            <ol className="list-inside list-decimal space-y-1 text-xs text-muted-foreground">
              <li>Parse the document</li>
              <li>Classify (LLM) → entities, claims, edges</li>
              <li>Check for conflicts with what's already known</li>
              <li>Write to the wiki (Markdown + JSONL)</li>
              <li>Query → intent → graph → cited answer</li>
            </ol>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-foreground">The key differences</h3>
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="bg-muted">
              <th className="border border-border px-3 py-2 text-left">Aspect</th>
              <th className="border border-border px-3 py-2 text-left text-error">Naive RAG</th>
              <th className="border border-border px-3 py-2 text-left text-primary">KM RAG</th>
            </tr>
          </thead>
          <tbody>
            {[
              ["Source tracking", "None — a chunk could be from anywhere", "Every claim carries provenance (source_id, section)"],
              ["Contradictions", "Invisible — both chunks land in the prompt", "Detected at ingest, flagged in the wiki"],
              ["Temporal queries", "Weak — chunks have no date structure", "Claims have date_start / date_end fields"],
              ["Relationships", "None — every chunk is isolated", "A graph of edges: X –[CEO_OF]→ Y"],
              ["Scaling", "More vectors → quality degrades", "A bigger wiki → every entity enriches the graph"],
            ].map(([feature, naive, km]) => (
              <tr key={feature} className="border-b border-border odd:bg-card even:bg-muted/20">
                <td className="border border-border px-3 py-2 font-medium">{feature}</td>
                <td className="border border-border px-3 py-2 text-muted-foreground">{naive}</td>
                <td className="border border-border px-3 py-2 text-muted-foreground">{km}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Walkthrough
        steps={[
          {
            title: "Open the Knowledge Map",
            content: <p>Click <strong>Knowledge Map</strong> in the sidebar. You'll see the graph built from every ingested source — each node is an entity or a concept.</p>,
            panelHint: "Knowledge Map → Browser",
          },
          {
            title: "Click a node",
            content: <p>On the <strong>Graph</strong> tab, click any node. A drawer opens with the full wiki page: its claims with provenance, and its edges to other nodes.</p>,
            panelHint: "Knowledge Map → Graph",
          },
          {
            title: "Compare with the Browser list",
            content: <p>The <strong>Browser</strong> tab lists every entity and concept in a table with its claim count. Search by name — each hit links to the wiki page.</p>,
            panelHint: "Knowledge Map → Browser",
          },
          {
            title: "The wiki on disk",
            content: <p>Knowledge lives in Markdown files under <code className="rounded bg-muted px-1 text-xs">wiki_data/default/</code>. Each entity is an <code className="rounded bg-muted px-1 text-xs">entity_*.md</code> with YAML frontmatter, plus <code className="rounded bg-muted px-1 text-xs">claims.jsonl</code>.</p>,
          },
        ]}
      />
    </div>
  );
}
