import { Walkthrough } from "../Walkthrough";

const EXAMPLES = [
  { bad: "What is AI?", good: "How did OpenAI define AI safety in its 2023 documents?", reason: "Specific entity + time range" },
  { bad: "Tell me about the project", good: "Which milestones did project X hit in Q3 2024?", reason: "Entity + temporal scope" },
  { bad: "Why did the company fail?", good: "What reasons for company Y's collapse does the 2023 Annual Report give vs. article Z?", reason: "Comparison of specific sources" },
  { bad: "Who runs the company?", good: "Who is Anthropic's CEO according to the 2024 documents?", reason: "Entity + role + year" },
  { bad: "Tell me everything about X", good: "What claims are there about company X's revenue from 2022–2024?", reason: "Topic scope + temporal" },
];

export function SectionQuerying() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">How to ask</h2>
        <p className="text-sm leading-relaxed text-muted-foreground">
          KM RAG works best with questions that name specific entities, give a time range, or ask you to
          compare sources. Vague questions do worse — the stage-1 intent parser can't pull out precise filters.
        </p>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold">What makes a question work</h3>
        {[
          ["Name specific entities", "Write \"Anthropic\", not \"the company\". The system searches by name and alias in the wiki."],
          ["Add a time range", "\"in 2023\", \"from Q1 to Q3 2024\", \"after 2020\" — stage 1 extracts time_range and filters the claims."],
          ["Ask about relationships directly", "\"How are X and Y connected?\" → retrieval searches edges.jsonl."],
          ["Ask for a source comparison", "\"What does document A say vs. B about X?\" → claims from both, with their provenance."],
          ["Ask about contradictions", "\"Which sources disagree about X?\" → the conflict detector flagged them at ingest."],
        ].map(([rule, desc]) => (
          <div key={rule} className="flex gap-3 rounded-lg border border-border bg-card p-3">
            <span className="mt-0.5 flex-shrink-0 text-sm text-primary">→</span>
            <div>
              <p className="text-sm font-medium text-foreground">{rule}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-semibold">Weak vs. strong questions</h3>
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="bg-muted">
              <th className="border border-border px-3 py-2 text-left text-error">Weak question</th>
              <th className="border border-border px-3 py-2 text-left text-primary">Stronger question</th>
              <th className="border border-border px-3 py-2 text-left">Why</th>
            </tr>
          </thead>
          <tbody>
            {EXAMPLES.map(({ bad, good, reason }) => (
              <tr key={bad} className="border-b border-border odd:bg-card even:bg-muted/20">
                <td className="border border-border px-3 py-2 italic text-muted-foreground">{bad}</td>
                <td className="border border-border px-3 py-2 text-foreground">{good}</td>
                <td className="border border-border px-3 py-2 text-muted-foreground">{reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Walkthrough
        steps={[
          {
            title: "Step 1: check what's in the wiki first",
            content: <p>Open <strong>Knowledge Map → Browser</strong>. Asking about an entity that isn't in the wiki gives a weak answer or triggers the agent fallback with nothing to return.</p>,
            panelHint: "Knowledge Map → Browser",
          },
          {
            title: "Step 2: phrase the question around a specific entity",
            content: (
              <div className="space-y-1">
                <p>Instead of: <em className="text-muted-foreground">"Who runs the company?"</em></p>
                <p>Write: <em className="font-medium text-foreground">"Who is Anthropic's CEO according to the 2024 documents?"</em></p>
                <p>Stage 1: <code className="rounded bg-muted px-1 text-xs">{`entities: ['Anthropic'], time_range: {start: 2024}`}</code></p>
              </div>
            ),
            panelHint: "Wiki Chat",
          },
          {
            title: "Step 3: read the stage-1 trace if the answer is weak",
            content: <p>If the answer is vague, check the stage-1 trace. Did the system pull out the right entities? If not, rephrase with more precise names.</p>,
            panelHint: "Wiki Chat → Intent Parser",
          },
          {
            title: "Step 4: check stage 2 if information is missing",
            content: <p>If the answer says "not found", check the stage-2 trace. How many candidates? Zero means the information isn't in the wiki — add more sources under <strong>Sources</strong>.</p>,
            panelHint: "Wiki Chat → Candidate Filter",
          },
        ]}
      />
    </div>
  );
}
