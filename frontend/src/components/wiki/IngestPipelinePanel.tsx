import { useState } from "react";
import {
  CheckCircle, Circle, Loader, AlertCircle,
  Upload, Brain, GitMerge, Shield, Save,
} from "lucide-react";
import { api } from "../../api/client";
import type { IngestResult } from "../../types";

type StageStatus = "idle" | "running" | "done" | "error" | "skipped";

interface Stage {
  id: number;
  name: string;
  description: string;
  icon: React.ElementType;
  status: StageStatus;
  detail?: string;
}

const INITIAL_STAGES: Stage[] = [
  {
    id: 1, name: "Parse", icon: Upload,
    description: "Extract text from file. Write parsed.md + manifest.json.",
    status: "idle",
  },
  {
    id: 2, name: "Classify", icon: Brain,
    description: "LLM structured output: entities, concepts, claims.",
    status: "idle",
  },
  {
    id: 3, name: "Resolve", icon: GitMerge,
    description: "Map mentions to wiki store. Create or merge.",
    status: "idle",
  },
  {
    id: 4, name: "Conflicts", icon: Shield,
    description: "Conditional LLM: check denying claims vs existing assertions.",
    status: "idle",
  },
  {
    id: 5, name: "Save + Reindex", icon: Save,
    description: "Write source, claims, edges. Append log. Regenerate index.",
    status: "idle",
  },
];

function StageRow({ stage }: { stage: Stage }) {
  const Icon = stage.icon;
  const colors: Record<StageStatus, string> = {
    idle: "text-muted-foreground",
    running: "text-blue-500 animate-pulse",
    done: "text-green-500",
    error: "text-red-500",
    skipped: "text-muted-foreground opacity-50",
  };
  const StatusIcon = {
    idle: Circle,
    running: Loader,
    done: CheckCircle,
    error: AlertCircle,
    skipped: Circle,
  }[stage.status];

  return (
    <div className={`flex items-start gap-3 p-3 rounded-md border ${
      stage.status === "running" ? "border-blue-500/30 bg-blue-500/5" :
      stage.status === "done" ? "border-green-500/30 bg-green-500/5" :
      stage.status === "error" ? "border-red-500/30 bg-red-500/5" :
      "border-border"
    }`}>
      <div className={`mt-0.5 ${colors[stage.status]}`}>
        <StatusIcon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <Icon className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-sm font-medium">Stage {stage.id}: {stage.name}</span>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">{stage.description}</p>
        {stage.detail && (
          <p className={`text-xs mt-1 ${stage.status === "error" ? "text-red-500" : "text-green-600"}`}>
            {stage.detail}
          </p>
        )}
      </div>
    </div>
  );
}

export function IngestPipelinePanel() {
  const [stages, setStages] = useState<Stage[]>(INITIAL_STAGES);
  const [result, setResult] = useState<IngestResult | null>(null);
  const [running, setRunning] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  function setStageStatus(id: number, status: StageStatus, detail?: string) {
    setStages((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status, detail } : s))
    );
  }

  async function handleIngest() {
    if (!selectedFile || running) return;
    setRunning(true);
    setResult(null);
    setStages(INITIAL_STAGES);

    setStageStatus(1, "running");
    await new Promise((r) => setTimeout(r, 150));
    setStageStatus(1, "done", "Text extracted.");

    setStageStatus(2, "running");
    setStageStatus(3, "running");

    let ingestResult: IngestResult;
    try {
      ingestResult = await api.ingestSource(selectedFile);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setStageStatus(2, "error", msg);
      setStageStatus(3, "idle");
      setRunning(false);
      return;
    }

    if (ingestResult.status === "error") {
      setStageStatus(2, "error", ingestResult.error ?? "Pipeline error");
      setRunning(false);
      return;
    }

    setStageStatus(2, "done", `${ingestResult.llm_calls} LLM call(s)`);
    setStageStatus(3, "done",
      `+${ingestResult.entities_created} entities, +${ingestResult.concepts_created} concepts`
    );

    if (ingestResult.conflicts.length > 0) {
      setStageStatus(4, "done",
        `${ingestResult.conflicts.length} conflict(s) detected`
      );
    } else {
      setStageStatus(4, "skipped", "No conflicts — skipped");
    }

    setStageStatus(5, "done",
      `+${ingestResult.claims_added} claims, +${ingestResult.edges_added} edges, index updated`
    );

    setResult(ingestResult);
    setRunning(false);
  }

  return (
    <div className="p-6 h-full flex gap-6">
      {/* Left: file selector + trigger */}
      <div className="w-72 shrink-0 space-y-4">
        <div className="text-xs text-muted-foreground bg-muted/40 rounded-md p-2.5 border-l-2 border-primary/50 mb-4">
          This panel is for watching the pipeline run, one stage at a time. To
          actually add files to your wiki, use{" "}
          <span className="font-medium text-primary">Sources</span>.
        </div>

        <h2 className="font-semibold text-sm">Pipeline visualizer</h2>
        <p className="text-xs text-muted-foreground">
          Pick a file and run the ingest pipeline to see each stage execute in real time.
        </p>

        <div className="space-y-2">
          <label className="block text-xs font-medium">File</label>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            className="block w-full text-xs text-muted-foreground file:mr-2 file:py-1 file:px-2 file:rounded file:border file:border-border file:text-xs file:bg-muted hover:file:bg-muted/80"
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <button
          onClick={handleIngest}
          disabled={!selectedFile || running}
          className="w-full py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
        >
          {running ? "Running…" : "Run Ingest Pipeline"}
        </button>

        {result && result.status === "ok" && (
          <div className="text-xs space-y-1 border border-border rounded-md p-3">
            <p className="font-medium text-green-600">Pipeline complete</p>
            <p>Source: <code className="font-mono">{result.slug}</code></p>
            <p>{result.duration_ms.toFixed(0)} ms total</p>
          </div>
        )}
      </div>

      {/* Right: stage list */}
      <div className="flex-1 space-y-2">
        <h3 className="font-semibold text-sm mb-3">5-Stage Pipeline</h3>
        {stages.map((stage) => (
          <StageRow key={stage.id} stage={stage} />
        ))}
      </div>
    </div>
  );
}
