import { useState, useRef, useEffect } from "react";
import { Send, Brain, Filter, CheckSquare, Layers, Sparkles, Clock, AlertCircle } from "lucide-react";
import { api } from "../../api/client";
import type { QueryTrace, RetrievalStageTrace } from "../../types";

const STAGE_ICONS = [Brain, Filter, CheckSquare, Layers, Sparkles];
const STAGE_COLORS: Record<string, string> = {
  idle: "text-muted-foreground border-border",
  running: "text-blue-500 border-blue-500/40 bg-blue-500/5 animate-pulse",
  done: "text-green-500 border-green-500/40 bg-green-500/5",
  error: "text-red-500 border-red-500/40 bg-red-500/5",
};

function StageCard({ stage, status }: { stage: RetrievalStageTrace; status: "idle" | "running" | "done" | "error" }) {
  const Icon = STAGE_ICONS[stage.stage - 1] ?? Brain;
  return (
    <div className={`border rounded-md p-2.5 text-xs transition-colors ${STAGE_COLORS[status]}`}>
      <div className="flex items-center gap-1.5 font-medium mb-1">
        <Icon className="w-3 h-3" />
        Stage {stage.stage}: {stage.name}
        {stage.llm_called && <span className="ml-auto text-[10px] bg-muted px-1 rounded">LLM</span>}
      </div>
      {status === "done" && (
        <>
          <p className="text-muted-foreground truncate">{stage.output_summary}</p>
          <p className="text-muted-foreground/60 mt-0.5">
            <Clock className="w-2.5 h-2.5 inline mr-0.5" />
            {stage.duration_ms.toFixed(0)} ms
          </p>
        </>
      )}
    </div>
  );
}

export function ChatWithTracePanel() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [trace, setTrace] = useState<QueryTrace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sourcesData, setSourcesData] = useState<Record<string, { title: string; summary: string }>>({});
  const [revealedStages, setRevealedStages] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load source data on mount
  useEffect(() => {
    api.listWikiSources().then((sources) => {
      const map: Record<string, { title: string; summary: string }> = {};
      for (const s of sources) map[s.id] = { title: s.title, summary: s.summary ?? "" };
      setSourcesData(map);
    }).catch(() => {
      // Non-fatal: fall back to raw IDs
    });
  }, []);

  // Sequential stage replay after trace arrives
  useEffect(() => {
    if (!trace) {
      setRevealedStages(0);
      return;
    }
    setRevealedStages(0);
    const timeouts: ReturnType<typeof setTimeout>[] = [];
    trace.stages.forEach((_, i) => {
      timeouts.push(setTimeout(() => setRevealedStages(i + 1), (i + 1) * 450));
    });
    return () => timeouts.forEach(clearTimeout);
  }, [trace]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || loading) return;
    setLoading(true);
    setError(null);
    setTrace(null);
    try {
      const result = await api.queryWiki(question.trim());
      setTrace(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Query failed.");
    } finally {
      setLoading(false);
    }
  }

  const stageStatus = (idx: number): "idle" | "running" | "done" | "error" => {
    if (!trace) return loading && idx === 0 ? "running" : "idle";
    if (revealedStages >= trace.stages.length) return "done";
    if (idx < revealedStages - 1) return "done";
    if (idx === revealedStages - 1) return "running";
    return "idle";
  };

  return (
    <div className="h-full flex flex-col p-6 gap-4">
      {/* Query bar */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your wiki…"
          className="flex-1 px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!question.trim() || loading}
          className="px-3 py-2 rounded-md bg-primary text-primary-foreground disabled:opacity-50 hover:bg-primary/90 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-500 border border-red-500/30 rounded-md p-3">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="flex-1 flex gap-4 overflow-hidden min-h-0">
        {/* Left: Answer */}
        <div className="flex-1 border border-border rounded-lg bg-card p-4 overflow-auto">
          {!trace && !loading && (
            <p className="text-sm text-muted-foreground">Ask a question to see the answer here.</p>
          )}
          {loading && (
            <p className="text-sm text-muted-foreground animate-pulse">Running retrieval pipeline…</p>
          )}
          {trace && (
            <div className="space-y-4">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Question</p>
                <p className="text-sm font-medium">{trace.question}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Answer</p>
                <p className="text-sm whitespace-pre-wrap">{trace.answer.final_answer}</p>
              </div>
              {trace.answer.sources.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Sources</p>
                  <div className="space-y-1.5">
                    {trace.answer.sources.map((s) => {
                      const src = sourcesData[s.source_id];
                      return (
                        <div key={s.source_id} className="text-xs border border-border rounded-md px-3 py-2 space-y-0.5">
                          <p className="font-medium text-foreground">{src?.title ?? s.source_id}</p>
                          {src?.summary && (
                            <p className="text-muted-foreground line-clamp-2">{src.summary}</p>
                          )}
                          <p className="text-muted-foreground/60 font-mono text-[10px]">
                            {s.source_id} · {s.claim_ids.length} claim(s)
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {trace.answer.reasoning_steps.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Reasoning</p>
                  <ol className="text-xs space-y-0.5 list-decimal list-inside text-muted-foreground">
                    {trace.answer.reasoning_steps.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ol>
                </div>
              )}
              {trace.answer.related_questions.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Related questions</p>
                  <ul className="space-y-1">
                    {trace.answer.related_questions.map((q, i) => (
                      <li key={i}>
                        <button
                          onClick={() => setQuestion(q)}
                          className="text-xs text-primary hover:underline text-left"
                        >
                          {q}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="flex gap-3 text-xs text-muted-foreground pt-2 border-t border-border">
                <span>Confidence: {(trace.answer.confidence * 100).toFixed(0)}%</span>
                <span>{trace.total_duration_ms.toFixed(0)} ms</span>
                <span>{trace.total_llm_calls} LLM calls</span>
                <span>{trace.candidates_count} candidates → {trace.selected_count} selected</span>
              </div>
            </div>
          )}
        </div>

        {/* Right: Stage trace */}
        <div className="w-72 shrink-0 space-y-2 overflow-auto">
          <div className="mb-1">
            <h3 className="text-sm font-semibold">Pipeline Trace</h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">Jak system przetwarza pytanie krok po kroku</p>
          </div>
          {trace ? (
            trace.stages.map((s, i) => (
              <StageCard key={s.stage} stage={s} status={stageStatus(i)} />
            ))
          ) : (
            [
              { name: "Intent Parser", desc: "Analizuje pytanie, wyciąga encje i koncepty" },
              { name: "Candidate Filter", desc: "Szuka pasujących wpisów w wiki" },
              { name: "Selection", desc: "Wybiera najlepiej pasujące wyniki" },
              { name: "Context Assembly", desc: "Składa kontekst dla modelu" },
              { name: "Answer Generator", desc: "Generuje odpowiedź na podstawie kontekstu" },
            ].map((info, i) => (
              <div key={i} className="border border-border rounded-md p-2.5 text-xs opacity-50">
                <p className="font-medium">Stage {i + 1}: {info.name}</p>
                <p className="text-muted-foreground mt-0.5">{info.desc}</p>
              </div>
            ))
          )}
          {trace && (
            <div className="text-xs text-muted-foreground pt-1 border-t border-border">
              <p>Intent: <span className="font-medium">{trace.intent.intent_type}</span></p>
              {trace.intent.entity_mentions.length > 0 && (
                <p>Entities: {trace.intent.entity_mentions.join(", ")}</p>
              )}
              {trace.intent.concept_mentions.length > 0 && (
                <p>Concepts: {trace.intent.concept_mentions.join(", ")}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
