import { useState } from "react";

export interface WalkthroughStep {
  title: string;
  content: React.ReactNode;
  panelHint?: string;
}

export function Walkthrough({ steps }: { steps: WalkthroughStep[] }) {
  const [current, setCurrent] = useState(0);
  const step = steps[current];

  return (
    <div className="border border-primary/30 rounded-lg overflow-hidden bg-primary/5 mt-4">
      <div className="flex items-center gap-2 px-4 py-2 bg-primary/10 border-b border-primary/20">
        <span className="text-xs font-mono text-primary font-medium">Krok po kroku</span>
        <span className="ml-auto text-xs text-muted-foreground">{current + 1} / {steps.length}</span>
      </div>
      <div className="p-4 space-y-3 min-h-[100px]">
        <h4 className="font-semibold text-sm text-foreground">{step.title}</h4>
        <div className="text-sm text-muted-foreground space-y-2">{step.content}</div>
        {step.panelHint && (
          <div className="flex items-center gap-2 bg-muted rounded px-3 py-1.5 text-xs mt-2">
            <span className="text-muted-foreground">Panel →</span>
            <span className="font-mono font-semibold text-foreground">{step.panelHint}</span>
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 px-4 py-3 border-t border-primary/20 bg-card/50">
        <div className="flex gap-1.5 mr-auto">
          {steps.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrent(i)}
              className={`w-2 h-2 rounded-full transition-colors ${
                i === current ? "bg-primary" : "bg-muted-foreground/30 hover:bg-muted-foreground/60"
              }`}
            />
          ))}
        </div>
        <button
          onClick={() => setCurrent(c => Math.max(0, c - 1))}
          disabled={current === 0}
          className="px-3 py-1 text-xs rounded border border-border disabled:opacity-30 hover:bg-muted transition-colors"
        >
          ← Wstecz
        </button>
        <button
          onClick={() => setCurrent(c => Math.min(steps.length - 1, c + 1))}
          disabled={current === steps.length - 1}
          className="px-3 py-1 text-xs rounded bg-primary text-primary-foreground disabled:opacity-30 hover:bg-primary/90 transition-colors"
        >
          Dalej →
        </button>
      </div>
    </div>
  );
}
