import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import type { RetrievedChunk, PromptData, HighlightRange } from "../../types";
import { streamChat, api } from "../../api/client";
import { RetrievalPanel } from "./RetrievalPanel";
import { PromptBuilderPanel } from "./PromptBuilderPanel";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: RetrievedChunk[];
}

function renderAssistantContent(content: string) {
  // Split on [Źródło N] or [Źródło N: name] references and render as chips
  const parts = content.split(/(\[Źródło\s+\d+(?::[^\]]+)?\])/g);
  return parts.map((part, i) => {
    if (/^\[Źródło\s+\d+/.test(part)) {
      return (
        <span key={i} className="inline-block bg-primary/20 text-primary text-xs font-medium px-1.5 py-0.5 rounded mx-0.5">
          {part}
        </span>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

function renderWithHighlights(content: string, ranges: HighlightRange[]) {
  if (!ranges || ranges.length === 0) return <span>{content}</span>;
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  for (const range of ranges) {
    if (cursor < range.start) {
      parts.push(<span key={`t-${cursor}`}>{content.slice(cursor, range.start)}</span>);
    }
    parts.push(
      <mark
        key={`h-${range.start}`}
        className="bg-primary/25 text-foreground font-medium rounded px-0.5"
      >
        {content.slice(range.start, range.end)}
      </mark>
    );
    cursor = range.end;
  }
  if (cursor < content.length) {
    parts.push(<span key="t-end">{content.slice(cursor)}</span>);
  }
  return <>{parts}</>;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(8);
  const [temperature, setTemperature] = useState(0.0);
  const [retrieval, setRetrieval] = useState<RetrievedChunk[]>([]);
  const [promptData, setPromptData] = useState<PromptData | null>(null);
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  function toggleSource(key: string) {
    setExpandedSources((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSend() {
    const query = input.trim();
    if (!query || loading) return;
    setInput("");
    setLoading(true);

    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    abortRef.current = streamChat(
      query,
      topK,
      (token) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = { ...last, content: last.content + token };
          return updated;
        });
      },
      () => {
        setLoading(false);
        Promise.all([api.getRetrieval(), api.getPrompt()])
          .then(([ret, prompt]) => {
            setRetrieval(ret);
            setPromptData(prompt);
            if (ret.length > 0) {
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  updated[updated.length - 1] = { ...last, sources: ret };
                }
                return updated;
              });
            }
          })
          .catch(console.error);
      },
      undefined,
      temperature,
    );
  }

  return (
    <div className="h-full flex gap-4 p-6">
      {/* Chat column */}
      <div className="flex-1 flex flex-col border border-border rounded-lg bg-card overflow-hidden">
        <div className="flex-1 overflow-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground text-center mt-8">
              Ask a question about your uploaded documents.
            </p>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted text-foreground"
                }`}
              >
                {msg.role === "assistant"
                  ? renderAssistantContent(msg.content || (loading && i === messages.length - 1 ? "▋" : ""))
                  : msg.content}
              </div>
              {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                <div className="max-w-[80%] mt-1 space-y-1">
                  <p className="text-xs text-muted-foreground font-medium px-1">Źródła:</p>
                  {msg.sources.map((chunk) => {
                    const key = `${i}-${chunk.chunk_id}`;
                    const isExpanded = expandedSources.has(key);
                    return (
                      <div key={chunk.chunk_id} className="bg-muted border border-border rounded-md px-2 py-1.5 text-xs">
                        <div className="flex items-center justify-between gap-2 mb-0.5">
                          <span className="font-medium text-primary truncate">
                            {chunk.document_name || chunk.document_id.slice(0, 12)}
                          </span>
                          <span className="text-muted-foreground shrink-0">#{chunk.rank} · {chunk.score.toFixed(3)}</span>
                        </div>
                        {!isExpanded ? (
                          <>
                            <p className="text-muted-foreground line-clamp-2 leading-relaxed">
                              {chunk.content.slice(0, 120)}…
                            </p>
                            <button
                              onClick={() => toggleSource(key)}
                              className="mt-1 text-primary/70 hover:text-primary transition-colors"
                            >
                              Rozwiń ▼
                            </button>
                          </>
                        ) : (
                          <>
                            <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                              {renderWithHighlights(chunk.content, chunk.highlighted_ranges ?? [])}
                            </p>
                            <button
                              onClick={() => toggleSource(key)}
                              className="mt-1 text-primary/70 hover:text-primary transition-colors"
                            >
                              Zwiń ▲
                            </button>
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        <div className="border-t px-3 pt-2 pb-0 flex items-center gap-3 text-xs text-muted-foreground">
          <span>Temperatura:</span>
          <input
            type="range" min={0} max={1} step={0.1} value={temperature}
            onChange={(e) => setTemperature(Number(e.target.value))}
            className="w-24 accent-primary"
          />
          <span className="w-6 text-center font-medium text-foreground">{temperature.toFixed(1)}</span>
          <span className="text-xs ml-1">(0 = deterministyczny, 1 = kreatywny)</span>
        </div>
        <div className="px-3 pb-3 pt-2 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Ask a question..."
            className="flex-1 text-sm border border-border rounded-md px-3 py-1.5 bg-muted text-foreground outline-none focus:border-primary"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="p-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Right panels */}
      <div className="w-80 flex flex-col gap-4 overflow-auto">
        <RetrievalPanel chunks={retrieval} topK={topK} onTopKChange={setTopK} />
        <PromptBuilderPanel promptData={promptData} />
      </div>
    </div>
  );
}
