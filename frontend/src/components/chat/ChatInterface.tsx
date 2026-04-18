import { useState, useRef, useEffect, useCallback } from "react";
import { Send } from "lucide-react";
import type { RetrievedChunk, PromptData } from "../../types";
import { streamChat, api } from "../../api/client";
import { RetrievalPanel } from "./RetrievalPanel";
import { PromptBuilderPanel } from "./PromptBuilderPanel";
import { SourceRef } from "./SourceRef";
import { SourcePopover } from "./SourcePopover";
import { FootnotesList } from "./FootnotesList";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: RetrievedChunk[];
}

interface ActivePopover {
  num: number;
  source: RetrievedChunk;
  anchorRect: DOMRect;
}

function renderAssistantContent(
  content: string,
  sources: RetrievedChunk[],
  activeNum: number | null,
  onActivate: (rect: DOMRect, num: number, source: RetrievedChunk) => void
) {
  const parts = content.split(/(\[Źródło\s+\d+(?::[^\]]+)?\])/g);
  return parts.map((part, i) => {
    const match = part.match(/^\[Źródło\s+(\d+)/);
    if (match) {
      const num = parseInt(match[1], 10);
      const source = sources[num - 1];
      return (
        <SourceRef
          key={i}
          num={num}
          source={source}
          onActivate={onActivate}
          isActive={activeNum === num}
        />
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(8);
  const [temperature, setTemperature] = useState(0.0);
  const [retrieval, setRetrieval] = useState<RetrievedChunk[]>([]);
  const [promptData, setPromptData] = useState<PromptData | null>(null);
  const [activePopover, setActivePopover] = useState<ActivePopover | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Close popover when a new message arrives
  useEffect(() => {
    setActivePopover(null);
  }, [messages.length]);

  const handleClose = useCallback(() => setActivePopover(null), []);

  function handleActivate(rect: DOMRect, num: number, source: RetrievedChunk) {
    setActivePopover((prev) =>
      prev?.num === num ? null : { num, source, anchorRect: rect }
    );
  }

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
                  ? renderAssistantContent(
                      msg.content || (loading && i === messages.length - 1 ? "▋" : ""),
                      msg.sources ?? [],
                      activePopover?.num ?? null,
                      handleActivate
                    )
                  : msg.content}
              </div>
              {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                <div className="max-w-[80%] w-full">
                  <FootnotesList sources={msg.sources} />
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

      {/* Popover */}
      {activePopover && (
        <SourcePopover
          source={activePopover.source}
          anchorRect={activePopover.anchorRect}
          onClose={handleClose}
        />
      )}
    </div>
  );
}
