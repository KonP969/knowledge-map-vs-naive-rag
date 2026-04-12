import { useState, useEffect } from "react";
import type { PromptData } from "../../types";
import { api } from "../../api/client";

interface PromptBuilderPanelProps {
  promptData: PromptData | null;
}

export function PromptBuilderPanel({ promptData }: PromptBuilderPanelProps) {
  const [editing, setEditing] = useState(false);
  const [sysPrompt, setSysPrompt] = useState("");

  useEffect(() => {
    if (promptData?.system_message) setSysPrompt(promptData.system_message);
  }, [promptData?.system_message]);

  async function saveSystemPrompt() {
    await api.updateSystemPrompt(sysPrompt);
    setEditing(false);
  }

  return (
    <div className="border rounded-lg bg-white p-4 space-y-3">
      <h3 className="text-sm font-semibold">Prompt Builder</h3>

      {promptData ? (
        <>
          <div className="grid grid-cols-4 gap-2">
            {(["system", "context", "query", "total"] as const).map((key) => (
              <div key={key} className="text-center border rounded p-2">
                <p className="text-xs text-muted-foreground capitalize">{key}</p>
                <p className="text-sm font-semibold">{promptData.token_counts[key]}</p>
              </div>
            ))}
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">System prompt</span>
              <button
                onClick={() => setEditing(!editing)}
                className="text-xs text-primary hover:underline"
              >
                {editing ? "Cancel" : "Edit"}
              </button>
            </div>
            {editing ? (
              <div className="space-y-1">
                <textarea
                  value={sysPrompt}
                  onChange={(e) => setSysPrompt(e.target.value)}
                  rows={4}
                  className="w-full text-xs border border-border rounded p-2 font-mono resize-none"
                />
                <button
                  onClick={saveSystemPrompt}
                  className="text-xs bg-primary text-white px-2 py-1 rounded hover:bg-primary/90"
                >
                  Save
                </button>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground line-clamp-2 font-mono">
                {promptData.system_message}
              </p>
            )}
          </div>

          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Full prompt</p>
            <pre className="text-xs bg-muted/50 rounded p-2 overflow-auto max-h-32 whitespace-pre-wrap font-mono leading-relaxed">
              {promptData.full_prompt}
            </pre>
          </div>
        </>
      ) : (
        <p className="text-xs text-muted-foreground">Ask a question to see the assembled prompt.</p>
      )}
    </div>
  );
}
