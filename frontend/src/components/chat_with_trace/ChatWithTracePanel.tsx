import { useState, useRef, useEffect, Fragment } from "react";
import { Send, Brain, Filter, CheckSquare, Layers, Sparkles, AlertCircle, Trash2, ChevronRight, ChevronDown, FileSearch, X } from "lucide-react";
import { api } from "../../api/client";
import type { QueryTrace, RetrievalStageTrace, AnswerSource, NodeDetailClaim, ClaimContext } from "../../types";

const POLARITY_COLOR: Record<string, string> = {
  asserts: "text-green-600 dark:text-green-400",
  denies: "text-red-600 dark:text-red-400",
};

const STAGE_ICONS = [Brain, Filter, CheckSquare, Layers, Sparkles];
type StageStatus = "idle" | "running" | "done" | "error";

// One fixed hue per stage, cool → warm as the signal moves down the chain.
const STAGE_HUE = ["#4a9e8f", "#6fa8c4", "#8e9cc8", "#c99b6e", "#d0714c"];

const HISTORY_KEY = "wikiChatHistory";
const HISTORY_LIMIT = 20;

function loadHistory(): QueryTrace[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

// Turn "[claim:cl_065]" / "[source:src_001]" in an answer into small superscript
// markers so the prose stays readable and the provenance is still one glance away.
function renderAnswer(text: string) {
  const parts = text.split(/(\[(?:claim|source):[A-Za-z0-9_]+\])/g);
  return parts.map((part, i) => {
    const m = part.match(/^\[(claim|source):([A-Za-z0-9_]+)\]$/);
    if (!m) return <Fragment key={i}>{part}</Fragment>;
    return (
      <sup
        key={i}
        title={`${m[1]} ${m[2]}`}
        className="mx-0.5 rounded-sm bg-primary/15 px-1 text-[0.65em] font-medium text-primary"
      >
        {m[1] === "claim" ? "cl" : "src"}
      </sup>
    );
  });
}

function SignalStation({
  stage,
  index,
  status,
  isLast,
}: {
  stage: RetrievalStageTrace | { stage: number; name: string; hint: string };
  index: number;
  status: StageStatus;
  isLast: boolean;
}) {
  const Icon = STAGE_ICONS[index] ?? Brain;
  const hue = STAGE_HUE[index] ?? "#8e9cc8";
  const live = status === "running";
  const done = status === "done";
  const hasTrace = "duration_ms" in stage;

  return (
    <div className="flex min-w-0 flex-1 items-start gap-2">
      <div className="flex flex-col items-center pt-0.5">
        <span
          className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border transition-colors ${live ? "animate-pulse" : ""}`}
          style={{
            borderColor: done || live ? hue : "var(--tw-border, #33343a)",
            background: done || live ? `${hue}22` : "transparent",
            color: done || live ? hue : "#8a8a82",
          }}
        >
          <Icon className="h-3 w-3" />
        </span>
      </div>
      <div className="min-w-0 flex-1 pb-1">
        <div className="flex items-baseline gap-1.5">
          <span className={`text-xs font-semibold ${done || live ? "text-foreground" : "text-muted-foreground"}`}>
            {stage.name}
          </span>
          {hasTrace && (stage as RetrievalStageTrace).llm_called && (
            <span className="rounded bg-muted px-1 text-[9px] font-medium text-muted-foreground">LLM</span>
          )}
        </div>
        {hasTrace && done ? (
          <>
            <p className="truncate text-[11px] text-muted-foreground" title={(stage as RetrievalStageTrace).output_summary}>
              {(stage as RetrievalStageTrace).output_summary}
            </p>
            <p className="font-mono text-[10px] text-muted-foreground/60">
              {(stage as RetrievalStageTrace).duration_ms.toFixed(0)} ms
            </p>
          </>
        ) : (
          <p className="text-[11px] text-muted-foreground/70">
            {hasTrace ? (live ? "running…" : "") : (stage as { hint: string }).hint}
          </p>
        )}
      </div>
      {!isLast && <div className="mt-3 hidden h-px flex-1 self-start bg-border sm:block" style={{ maxWidth: 24 }} />}
    </div>
  );
}

const IDLE_STAGES = [
  { stage: 1, name: "Intent Parser", hint: "Reads the question; pulls out entities and concepts" },
  { stage: 2, name: "Candidate Filter", hint: "Lexical + semantic search over the graph" },
  { stage: 3, name: "Selection", hint: "Picks the artifacts most likely to answer it" },
  { stage: 4, name: "Context Assembly", hint: "Builds the context from the selected claims" },
  { stage: 5, name: "Answer Generator", hint: "Writes the answer, cites every claim" },
];

function SignalChain({
  latest,
  loading,
  revealedStages,
}: {
  latest: QueryTrace | null;
  loading: boolean;
  revealedStages: number;
}) {
  const stageStatus = (idx: number): StageStatus => {
    if (!latest) return loading && idx === 0 ? "running" : "idle";
    if (revealedStages >= latest.stages.length) return "done";
    if (idx < revealedStages - 1) return "done";
    if (idx === revealedStages - 1) return "running";
    return "idle";
  };

  const stages = latest ? latest.stages : IDLE_STAGES;

  return (
    <div data-tour="pipeline" className="rounded-lg border border-border bg-card p-3">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-xs font-semibold text-muted-foreground">Pipeline</h3>
        {latest && (
          <div className="flex gap-3 font-mono text-[10px] text-muted-foreground">
            <span>{latest.intent.intent_type}</span>
            <span>{latest.total_llm_calls} LLM</span>
            <span>{latest.total_duration_ms.toFixed(0)} ms</span>
            <span>{latest.candidates_count}→{latest.selected_count}</span>
          </div>
        )}
      </div>
      <div className="flex flex-col gap-3 sm:flex-row sm:gap-1">
        {stages.map((s, i) => (
          <SignalStation key={s.stage} stage={s} index={i} status={stageStatus(i)} isLast={i === stages.length - 1} />
        ))}
      </div>
      {latest && (latest.intent.entity_mentions.length > 0 || latest.intent.concept_mentions.length > 0) && (
        <div className="mt-2 flex flex-wrap gap-1 border-t border-border pt-2">
          {latest.intent.entity_mentions.map((e) => (
            <span key={`e-${e}`} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">{e}</span>
          ))}
          {latest.intent.concept_mentions.map((c) => (
            <span key={`c-${c}`} className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground/80">{c}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function ChatEntry({
  trace,
  sourcesData,
  onPickQuestion,
}: {
  trace: QueryTrace;
  sourcesData: Record<string, { title: string; summary: string; slug: string }>;
  onPickQuestion: (q: string) => void;
}) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [claimsBySource, setClaimsBySource] = useState<
    Record<string, NodeDetailClaim[] | "loading" | "error">
  >({});
  const [snippet, setSnippet] = useState<(ClaimContext & { title: string }) | null>(null);

  async function loadClaims(s: AnswerSource) {
    if (claimsBySource[s.source_id]) return;
    if (s.claim_ids.length === 0) {
      setClaimsBySource((p) => ({ ...p, [s.source_id]: [] }));
      return;
    }
    setClaimsBySource((p) => ({ ...p, [s.source_id]: "loading" }));
    try {
      const claims = await api.getClaimsByIds(s.claim_ids);
      setClaimsBySource((p) => ({ ...p, [s.source_id]: claims }));
    } catch {
      setClaimsBySource((p) => ({ ...p, [s.source_id]: "error" }));
    }
  }

  async function openDoc(claim: NodeDetailClaim, title: string) {
    try {
      const ctx = await api.getClaimContext(claim.id);
      setSnippet({ ...ctx, title });
    } catch {
      /* button just won't open */
    }
  }

  function toggleSource(s: AnswerSource) {
    if (expanded === s.source_id) {
      setExpanded(null);
      return;
    }
    setExpanded(s.source_id);
    loadClaims(s);
  }

  function hoverSource(s: AnswerSource) {
    setHovered(s.source_id);
    loadClaims(s);
  }

  function renderClaims(
    claims: NodeDetailClaim[] | "loading" | "error" | undefined,
    onOpenDoc?: (c: NodeDetailClaim) => void,
  ) {
    if (claims === "loading") return <p className="animate-pulse py-0.5 text-muted-foreground">Loading claims…</p>;
    if (claims === "error") return <p className="py-0.5 text-red-500">Couldn't load the claims.</p>;
    if (Array.isArray(claims) && claims.length === 0) return <p className="py-0.5 text-muted-foreground">No matched claims.</p>;
    if (!Array.isArray(claims)) return null;
    return claims.map((c) => (
      <div key={c.id} className="border-l-2 border-primary/40 pl-2 py-0.5">
        <p className="leading-snug text-foreground">{c.text}</p>
        {c.span?.text && (
          <p className="mt-1 border-l-2 border-amber-400/50 pl-2 text-xs italic leading-snug text-foreground/90">
            “{c.span.text}”
          </p>
        )}
        <p className={`mt-0.5 text-[10px] ${POLARITY_COLOR[c.polarity] ?? "text-muted-foreground"}`}>
          {c.polarity} · {(c.confidence * 100).toFixed(0)}% · <span className="font-mono text-muted-foreground/60">{c.id}</span>
        </p>
        {onOpenDoc && c.span && (
          <button
            onClick={() => onOpenDoc(c)}
            className="mt-1 inline-flex items-center gap-1 rounded border border-primary/35 px-1.5 py-0.5 text-[11px] font-medium text-primary transition-colors hover:bg-primary/10"
          >
            <FileSearch className="h-3 w-3" />
            Show in document
          </button>
        )}
      </div>
    ));
  }

  return (
    <div className="space-y-4 border-b border-border pb-4 last:border-b-0">
      <div>
        <p className="mb-1 text-xs font-medium text-muted-foreground">Question</p>
        <p className="text-sm font-medium">{trace.question}</p>
      </div>
      <div>
        <p className="mb-1 text-xs font-medium text-muted-foreground">Answer</p>
        <p className="max-w-[70ch] whitespace-pre-wrap font-serif text-[15px] leading-relaxed">
          {renderAnswer(trace.answer.final_answer)}
        </p>
      </div>
      {trace.answer.sources.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-muted-foreground">Sources</p>
          <div className="space-y-1.5">
            {trace.answer.sources.map((s) => {
              const src = sourcesData[s.source_id];
              const isOpen = expanded === s.source_id;
              const hasClaims = s.claim_ids.length > 0;
              const claims = claimsBySource[s.source_id];
              return (
                <div
                  key={s.source_id}
                  className="relative rounded-md border border-border text-xs"
                  onMouseEnter={() => hasClaims && hoverSource(s)}
                  onMouseLeave={() => setHovered(null)}
                >
                  {hovered === s.source_id && !isOpen && hasClaims && (
                    <div className="absolute bottom-full left-0 right-0 z-30 mb-1 space-y-1.5 rounded-md border border-border bg-popover p-2.5 shadow-lg">
                      <p className="text-[10px] font-medium text-muted-foreground">
                        Claims cited in this answer
                      </p>
                      {renderClaims(claims)}
                    </div>
                  )}
                  <button
                    onClick={() => hasClaims && toggleSource(s)}
                    disabled={!hasClaims}
                    className={`w-full space-y-1 rounded-md px-3 py-2 text-left transition-colors ${hasClaims ? "cursor-pointer hover:bg-muted/50" : "cursor-default"}`}
                  >
                    <div className="flex items-center gap-2">
                      <p className="flex-1 truncate font-medium text-foreground">{src?.title ?? s.source_id}</p>
                      {hasClaims && (
                        <span className="flex shrink-0 items-center gap-1 rounded bg-primary/10 px-1.5 py-0.5 text-[11px] font-medium text-primary">
                          {isOpen ? "Hide claims" : `${s.claim_ids.length} ${s.claim_ids.length === 1 ? "claim" : "claims"}`}
                          {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                        </span>
                      )}
                    </div>
                    {src?.summary && !isOpen && (
                      <p className="line-clamp-2 text-muted-foreground">{src.summary}</p>
                    )}
                    <p className="font-mono text-[10px] text-muted-foreground/60">
                      {s.source_id}{!hasClaims && " · no claims"}
                    </p>
                  </button>
                  {isOpen && (
                    <div className="space-y-1.5 border-t border-border bg-muted/20 px-3 pb-2 pt-1">
                      {renderClaims(claims, (c) => openDoc(c, src?.title ?? s.source_id))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
      {trace.answer.reasoning_steps.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-muted-foreground">Reasoning</p>
          <ol className="list-inside list-decimal space-y-0.5 text-xs text-muted-foreground">
            {trace.answer.reasoning_steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </div>
      )}
      {trace.answer.related_questions.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-muted-foreground">Follow-ups</p>
          <ul className="space-y-1">
            {trace.answer.related_questions.map((q, i) => (
              <li key={i}>
                <button
                  onClick={() => onPickQuestion(q)}
                  className="text-left text-xs text-primary hover:underline"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex gap-3 pt-2 font-mono text-[11px] text-muted-foreground">
        <span>confidence {(trace.answer.confidence * 100).toFixed(0)}%</span>
        <span>{trace.total_duration_ms.toFixed(0)} ms</span>
        <span>{trace.total_llm_calls} LLM calls</span>
        <span>{trace.candidates_count} → {trace.selected_count}</span>
      </div>
      {snippet && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setSnippet(null)}
        >
          <div
            className="flex max-h-[70vh] w-full max-w-2xl flex-col rounded-lg border border-border bg-card shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex shrink-0 items-center justify-between border-b border-border px-4 py-3">
              <span className="truncate text-sm font-medium" title={snippet.title}>
                In document: {snippet.title}
              </span>
              <button onClick={() => setSnippet(null)} className="ml-2 shrink-0 text-muted-foreground transition-colors hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              {!snippet.located && (
                <p className="mb-2 text-xs text-amber-500">
                  Couldn't pin the fragment exactly in the original (PDF artifacts) — showing the extracted text.
                </p>
              )}
              <p className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-foreground">
                {snippet.located && <span className="text-muted-foreground/60">…{snippet.before}</span>}
                <mark className="rounded-sm bg-primary/25 px-0.5 text-foreground">{snippet.match}</mark>
                {snippet.located && <span className="text-muted-foreground/60">{snippet.after}…</span>}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function ChatWithTracePanel() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<QueryTrace[]>(loadHistory);
  const [error, setError] = useState<string | null>(null);
  const [sourcesData, setSourcesData] = useState<Record<string, { title: string; summary: string; slug: string }>>({});
  const [revealedStages, setRevealedStages] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const latest = history.length > 0 ? history[history.length - 1] : null;

  useEffect(() => {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    } catch {
      /* storage full or unavailable — non-fatal */
    }
  }, [history]);

  useEffect(() => {
    api.listWikiSources().then((sources) => {
      const map: Record<string, { title: string; summary: string; slug: string }> = {};
      for (const s of sources) map[s.id] = { title: s.title, summary: s.summary ?? "", slug: s.slug };
      setSourcesData(map);
    }).catch(() => {
      /* non-fatal: fall back to raw IDs */
    });
  }, []);

  useEffect(() => {
    if (!latest) {
      setRevealedStages(0);
      return;
    }
    setRevealedStages(0);
    const timeouts: ReturnType<typeof setTimeout>[] = [];
    latest.stages.forEach((_, i) => {
      timeouts.push(setTimeout(() => setRevealedStages(i + 1), (i + 1) * 450));
    });
    return () => timeouts.forEach(clearTimeout);
  }, [latest]);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [history, loading]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || loading) return;
    const asked = question.trim();
    setLoading(true);
    setError(null);
    try {
      const result = await api.queryWiki(asked);
      setHistory((prev) => [...prev, result].slice(-HISTORY_LIMIT));
      setQuestion("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Query failed.");
    } finally {
      setLoading(false);
    }
  }

  function clearHistory() {
    setHistory([]);
    setError(null);
    try {
      localStorage.removeItem(HISTORY_KEY);
    } catch {
      /* non-fatal */
    }
  }

  return (
    <div className="flex h-full flex-col gap-4 p-6">
      <form onSubmit={handleSubmit} data-tour="chat-input" className="flex gap-2">
        <input
          ref={inputRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your wiki…"
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!question.trim() || loading}
          className="rounded-md bg-primary px-3 py-2 text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>

      {error && (
        <div className="flex items-center gap-2 rounded-md border border-red-500/30 p-3 text-sm text-red-500">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      <SignalChain latest={latest} loading={loading} revealedStages={revealedStages} />

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-auto rounded-lg border border-border bg-card p-4">
        {history.length === 0 && !loading && (
          <p className="text-sm text-muted-foreground">Ask a question to see the answer and its trace here.</p>
        )}
        {loading && (
          <p className="animate-pulse text-sm text-muted-foreground">Running the retrieval pipeline…</p>
        )}
        {history.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                {history.length} {history.length === 1 ? "question" : "questions"} in this session
              </p>
              <button
                onClick={clearHistory}
                className="flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-red-500"
                title="Clear the conversation history"
              >
                <Trash2 className="h-3 w-3" />
                Clear history
              </button>
            </div>
            {[...history].reverse().map((t) => (
              <ChatEntry
                key={t.query_id}
                trace={t}
                sourcesData={sourcesData}
                onPickQuestion={setQuestion}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
