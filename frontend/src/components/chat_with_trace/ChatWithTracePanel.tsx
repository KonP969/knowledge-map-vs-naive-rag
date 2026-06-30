import { useState, useRef, useEffect } from "react";
import { Send, Brain, Filter, CheckSquare, Layers, Sparkles, Clock, AlertCircle, Trash2, ChevronRight, ChevronDown, FileSearch, X } from "lucide-react";
import { api } from "../../api/client";
import type { QueryTrace, RetrievalStageTrace, AnswerSource, NodeDetailClaim, ClaimContext } from "../../types";

const POLARITY_COLOR: Record<string, string> = {
  asserts: "text-green-600 dark:text-green-400",
  denies: "text-red-600 dark:text-red-400",
};

const STAGE_ICONS = [Brain, Filter, CheckSquare, Layers, Sparkles];
const STAGE_COLORS: Record<string, string> = {
  idle: "text-muted-foreground border-border",
  running: "text-blue-500 border-blue-500/40 bg-blue-500/5 animate-pulse",
  done: "text-green-500 border-green-500/40 bg-green-500/5",
  error: "text-red-500 border-red-500/40 bg-red-500/5",
};

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
  // Fragment-in-context snippet (not the whole document).
  const [snippet, setSnippet] = useState<(ClaimContext & { title: string }) | null>(null);

  async function loadClaims(s: AnswerSource) {
    if (claimsBySource[s.source_id]) return; // cached or in-flight
    if (s.claim_ids.length === 0) {
      setClaimsBySource((p) => ({ ...p, [s.source_id]: [] }));
      return;
    }
    setClaimsBySource((p) => ({ ...p, [s.source_id]: "loading" }));
    try {
      // Fetch exactly the cited claims by id (not a source's first-N window), so claims
      // cited beyond the node-detail cap still show up.
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
      // ignore — button just won't open
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

  // Compact claim list shared by the hover popover and the expanded panel.
  // onOpenDoc is only passed in the expanded panel (the hover popover is transient,
  // so its "jump to document" button would be unreachable).
  function renderClaims(
    claims: NodeDetailClaim[] | "loading" | "error" | undefined,
    onOpenDoc?: (c: NodeDetailClaim) => void,
  ) {
    if (claims === "loading") return <p className="text-muted-foreground animate-pulse py-0.5">Ładuję fragmenty…</p>;
    if (claims === "error") return <p className="text-red-500 py-0.5">Nie udało się wczytać fragmentów.</p>;
    if (Array.isArray(claims) && claims.length === 0) return <p className="text-muted-foreground py-0.5">Brak dopasowanych twierdzeń.</p>;
    if (!Array.isArray(claims)) return null;
    return claims.map((c) => (
      <div key={c.id} className="border-l-2 border-primary/40 pl-2 py-0.5">
        <p className="text-foreground leading-snug">{c.text}</p>
        {c.span?.text && (
          <p className="text-xs italic text-foreground/90 border-l-2 border-amber-400/50 pl-2 mt-1 leading-snug">
            „{c.span.text}"
          </p>
        )}
        <p className={`text-[10px] mt-0.5 ${POLARITY_COLOR[c.polarity] ?? "text-muted-foreground"}`}>
          {c.polarity} · {(c.confidence * 100).toFixed(0)}% · <span className="font-mono text-muted-foreground/60">{c.id}</span>
        </p>
        {onOpenDoc && c.span && (
          <button
            onClick={() => onOpenDoc(c)}
            className="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-primary border border-primary/35 rounded px-1.5 py-0.5 hover:bg-primary/10 transition-colors"
          >
            <FileSearch className="w-3 h-3" />
            Pokaż w dokumencie
          </button>
        )}
      </div>
    ));
  }

  return (
    <div className="space-y-4 pb-4 border-b border-border last:border-b-0">
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
              const isOpen = expanded === s.source_id;
              const hasClaims = s.claim_ids.length > 0;
              const claims = claimsBySource[s.source_id];
              return (
                <div
                  key={s.source_id}
                  className="relative text-xs border border-border rounded-md"
                  onMouseEnter={() => hasClaims && hoverSource(s)}
                  onMouseLeave={() => setHovered(null)}
                >
                  {/* Hover preview popover — quick peek at the fragments */}
                  {hovered === s.source_id && !isOpen && hasClaims && (
                    <div className="absolute z-30 left-0 right-0 bottom-full mb-1 p-2.5 rounded-md border border-border bg-popover shadow-lg space-y-1.5">
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">
                        Fragmenty cytowane w odpowiedzi
                      </p>
                      {renderClaims(claims)}
                    </div>
                  )}
                  <button
                    onClick={() => hasClaims && toggleSource(s)}
                    disabled={!hasClaims}
                    className={`w-full text-left px-3 py-2 space-y-1 rounded-md ${hasClaims ? "hover:bg-muted/50 cursor-pointer" : "cursor-default"} transition-colors`}
                  >
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-foreground flex-1 truncate">{src?.title ?? s.source_id}</p>
                      {hasClaims && (
                        <span className="flex items-center gap-1 shrink-0 text-primary text-[11px] font-medium rounded px-1.5 py-0.5 bg-primary/10">
                          {isOpen ? "Ukryj fragmenty" : `Pokaż ${s.claim_ids.length} ${s.claim_ids.length === 1 ? "fragment" : "fragmenty"}`}
                          {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                        </span>
                      )}
                    </div>
                    {src?.summary && !isOpen && (
                      <p className="text-muted-foreground line-clamp-2">{src.summary}</p>
                    )}
                    <p className="text-muted-foreground/60 font-mono text-[10px]">
                      {s.source_id}{!hasClaims && " · brak fragmentów"}
                    </p>
                  </button>
                  {isOpen && (
                    <div className="px-3 pb-2 pt-1 border-t border-border bg-muted/20 space-y-1.5">
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
                  onClick={() => onPickQuestion(q)}
                  className="text-xs text-primary hover:underline text-left"
                >
                  {q}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex gap-3 text-xs text-muted-foreground pt-2">
        <span>Confidence: {(trace.answer.confidence * 100).toFixed(0)}%</span>
        <span>{trace.total_duration_ms.toFixed(0)} ms</span>
        <span>{trace.total_llm_calls} LLM calls</span>
        <span>{trace.candidates_count} candidates → {trace.selected_count} selected</span>
      </div>
      {snippet && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setSnippet(null)}
        >
          <div
            className="w-full max-w-2xl max-h-[70vh] flex flex-col rounded-lg border border-border bg-card shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
              <span className="text-sm font-medium truncate" title={snippet.title}>
                Fragment w dokumencie: {snippet.title}
              </span>
              <button onClick={() => setSnippet(null)} className="ml-2 text-muted-foreground hover:text-foreground transition-colors shrink-0">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4">
              {!snippet.located && (
                <p className="text-xs text-amber-500 mb-2">
                  Nie udało się dokładnie zlokalizować fragmentu w oryginale (artefakty PDF) — pokazuję wyodrębniony fragment.
                </p>
              )}
              <p className="text-xs leading-relaxed whitespace-pre-wrap break-words font-mono text-foreground">
                {snippet.located && <span className="text-muted-foreground/60">…{snippet.before}</span>}
                <mark className="bg-primary/25 text-foreground rounded-sm px-0.5">{snippet.match}</mark>
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

  // Persist history to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    } catch {
      // Storage full or unavailable — non-fatal
    }
  }, [history]);

  // Load source data on mount
  useEffect(() => {
    api.listWikiSources().then((sources) => {
      const map: Record<string, { title: string; summary: string; slug: string }> = {};
      for (const s of sources) map[s.id] = { title: s.title, summary: s.summary ?? "", slug: s.slug };
      setSourcesData(map);
    }).catch(() => {
      // Non-fatal: fall back to raw IDs
    });
  }, []);

  // Sequential stage replay for the latest trace
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

  // Newest entry is rendered at the top → scroll the conversation back to top
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
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
      // Non-fatal
    }
  }

  const stageStatus = (idx: number): "idle" | "running" | "done" | "error" => {
    if (!latest) return loading && idx === 0 ? "running" : "idle";
    if (revealedStages >= latest.stages.length) return "done";
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
        {/* Left: Conversation history */}
        <div ref={scrollRef} className="flex-1 border border-border rounded-lg bg-card p-4 overflow-auto">
          {history.length === 0 && !loading && (
            <p className="text-sm text-muted-foreground">Ask a question to see the answer here.</p>
          )}
          {history.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  {history.length} {history.length === 1 ? "rozmowa" : "rozmów"} w historii
                </p>
                <button
                  onClick={clearHistory}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-red-500 transition-colors"
                  title="Wyczyść całą historię rozmów"
                >
                  <Trash2 className="w-3 h-3" />
                  Wyczyść historię
                </button>
              </div>
              {loading && (
                <p className="text-sm text-muted-foreground animate-pulse">Running retrieval pipeline…</p>
              )}
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
          {history.length === 0 && loading && (
            <p className="text-sm text-muted-foreground animate-pulse mt-4">Running retrieval pipeline…</p>
          )}
        </div>

        {/* Right: Stage trace (latest conversation) */}
        <div className="w-72 shrink-0 space-y-2 overflow-auto">
          <div className="mb-1">
            <h3 className="text-sm font-semibold">Pipeline Trace</h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">Jak system przetwarza pytanie krok po kroku</p>
          </div>
          {latest ? (
            latest.stages.map((s, i) => (
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
          {latest && (
            <div className="text-xs text-muted-foreground pt-1 border-t border-border">
              <p>Intent: <span className="font-medium">{latest.intent.intent_type}</span></p>
              {latest.intent.entity_mentions.length > 0 && (
                <p>Entities: {latest.intent.entity_mentions.join(", ")}</p>
              )}
              {latest.intent.concept_mentions.length > 0 && (
                <p>Concepts: {latest.intent.concept_mentions.join(", ")}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
