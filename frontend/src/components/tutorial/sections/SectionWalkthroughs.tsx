import { useState } from "react";
import { Walkthrough } from "../Walkthrough";
import type { WalkthroughStep } from "../Walkthrough";

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
    title: "Add your first source",
    description: "Ingest a document and watch the system build structured knowledge.",
    steps: [
      {
        title: "Open the Sources panel",
        content: <p>Click <strong>Sources</strong> in the sidebar. You'll see the list of ingested sources (empty on a first session).</p>,
        panelHint: "Sources",
      },
      {
        title: "Add a document or paste a URL",
        content: <p>Drop in a PDF/DOCX/TXT/MD file, or use <strong>Import from URL</strong> for an article. A blog post about AI or a company's annual report both work well.</p>,
        panelHint: "Sources",
      },
      {
        title: "Watch the 5 ingest stages",
        content: <p>The progress runs: Parse → Classify (LLM, ~3–5s) → Conflict detection → Merge → Reindex. When it's done the source is listed.</p>,
        panelHint: "Sources → ingest progress",
      },
      {
        title: "Review the classification result",
        content: <p>Click the source → its detail view. You'll see what the model extracted: entities, concepts, claims, edges — each with a confidence score.</p>,
        panelHint: "Sources → source detail",
      },
      {
        title: "Open the Knowledge Map — new nodes",
        content: <p>Go to <strong>Knowledge Map → Graph</strong>. The new entities show up as nodes. Click one to see its claims, each tracing back to your document.</p>,
        panelHint: "Knowledge Map → Graph",
      },
    ],
  },
  {
    id: "query-trace",
    icon: "💬",
    title: "Ask a question and read the trace",
    description: "See the retrieval pipeline from the inside — every one of the 5 stages.",
    steps: [
      {
        title: "Open Wiki Chat",
        content: <p>Click <strong>Wiki Chat</strong> in the sidebar. Make sure you have at least one source ingested — retrieval needs data in the wiki.</p>,
        panelHint: "Wiki Chat",
      },
      {
        title: "Ask a precise question",
        content: (
          <div className="space-y-1">
            <p>Ask about a specific entity from your wiki. For example:</p>
            <ul className="ml-2 list-inside list-disc space-y-0.5 text-xs">
              <li><em>"What role does [person] hold at [organization]?"</em></li>
              <li><em>"When did [company] announce [product]?"</em></li>
              <li><em>"Which sources cover [topic] from different angles?"</em></li>
            </ul>
          </div>
        ),
        panelHint: "Wiki Chat → question box",
      },
      {
        title: "Stage 1: check the parsed intent",
        content: <p>Look at the <strong>Intent Parser</strong> station. Did it pull out the right entities and time range? If not, rephrase with more precise names.</p>,
        panelHint: "Wiki Chat → Intent Parser",
      },
      {
        title: "Stages 2–3: candidates and selection",
        content: <p>See how many candidates stage 2 found and which the model picked in stage 3. Zero candidates means the wiki has no data for this question.</p>,
        panelHint: "Wiki Chat → Candidate Filter + Selection",
      },
      {
        title: "Stage 5: cited answer + agent fallback",
        content: <p>The answer carries <code className="rounded bg-muted px-1 text-xs">[claim:cl_…]</code> and <code className="rounded bg-muted px-1 text-xs">[source:src_…]</code> markers. If the agent ran, the trace shows its tool calls.</p>,
        panelHint: "Wiki Chat → Answer Generator",
      },
    ],
  },
  {
    id: "lint-fix",
    icon: "🔍",
    title: "Run Lint and fix an issue",
    description: "Check the knowledge base for problems and fix them.",
    steps: [
      {
        title: "Open Lint",
        content: <p>Click <strong>Lint</strong> in the sidebar. You'll see a <strong>Run Lint</strong> button and any results from a previous run.</p>,
        panelHint: "Lint",
      },
      {
        title: "Run the tier 1 + 2 checks",
        content: (
          <div className="space-y-1">
            <p>Click <strong>Run Lint</strong>. It checks three groups:</p>
            <ul className="ml-2 list-inside list-disc space-y-0.5 text-xs">
              <li><strong>Provenance</strong> (tier 1): claims with no source, missing fields</li>
              <li><strong>Integrity</strong> (tier 2): duplicate entities, empty descriptions</li>
              <li><strong>Navigability</strong> (tier 2): orphan nodes, missing back-links</li>
            </ul>
          </div>
        ),
        panelHint: "Lint → Run Lint",
      },
      {
        title: "Review the issues — click one for detail",
        content: <p>Each issue shows a type (e.g. <code className="rounded bg-muted px-1 text-xs">empty_description</code>), a description, and the affected page. Click it to expand with the suggested fix.</p>,
        panelHint: "Lint → issue list",
      },
      {
        title: "Apply an auto-fix",
        content: <p>Issues with an <strong>Apply Fix</strong> button write the change straight to the wiki file and refresh the list. Issues that need a human call (e.g. <code className="rounded bg-muted px-1 text-xs">unmarked_contradiction</code>) only offer reject / won't fix.</p>,
        panelHint: "Lint → issue → Apply Fix",
      },
      {
        title: "Turn on the semantic checks (tier 3)",
        content: <p>Enable <strong>Semantic checks</strong> and run Lint again. Tier 3 uses the LLM: unflagged contradictions, alias collisions, missing concepts, stale summaries. It takes a few seconds.</p>,
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
        <h2 className="text-lg font-semibold">Guided walkthroughs</h2>
        <p className="text-sm text-muted-foreground">
          Step by step through the main workflows. Pick one and follow along in the app.
        </p>
      </div>

      <div className="space-y-3">
        {WALKTHROUGHS.map((wt) => (
          <div key={wt.id} className="overflow-hidden rounded-lg border border-border bg-card">
            <button
              onClick={() => setActive(active === wt.id ? null : wt.id)}
              className="flex w-full items-center gap-3 p-4 text-left transition-colors hover:bg-muted/40"
            >
              <span className="text-xl">{wt.icon}</span>
              <div className="flex-1">
                <p className="text-sm font-medium text-foreground">{wt.title}</p>
                <p className="text-xs text-muted-foreground">{wt.description}</p>
              </div>
              <span className="text-xs text-muted-foreground">{active === wt.id ? "▲" : "▼"}</span>
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
