import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import { RetrievedChunk, PromptData } from "../../types";
import { streamChat, api } from "../../api/client";
import { RetrievalPanel } from "./RetrievalPanel";
import { PromptBuilderPanel } from "./PromptBuilderPanel";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(5);
  const [retrieval, setRetrieval] = useState<RetrievedChunk[]>([]);
  const [promptData, setPromptData] = useState<PromptData | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

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
          })
          .catch(console.error);
      },
    );
  }

  return (
    <div className="h-full flex gap-4 p-6">
      {/* Chat column */}
      <div className="flex-1 flex flex-col border rounded-lg bg-white overflow-hidden">
        <div className="flex-1 overflow-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground text-center mt-8">
              Ask a question about your uploaded documents.
            </p>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  msg.role === "user" ? "bg-primary text-white" : "bg-muted text-foreground"
                }`}
              >
                {msg.content || (loading && i === messages.length - 1 ? "▋" : "")}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        <div className="border-t p-3 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            placeholder="Ask a question..."
            className="flex-1 text-sm border border-border rounded-md px-3 py-1.5 outline-none focus:border-primary"
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="p-2 bg-primary text-white rounded-md hover:bg-primary/90 disabled:opacity-50 transition-colors"
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
