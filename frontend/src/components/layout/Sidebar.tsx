import { BarChart2, BookOpen, Database, Zap, MessageSquareText, Map, ShieldCheck } from "lucide-react";
import type { Panel } from "../../types";

const NAV = [
  { id: "ingest" as Panel, label: "Ingest", icon: Zap },
  { id: "sources" as Panel, label: "Sources", icon: Database },
  { id: "chat_trace" as Panel, label: "Wiki Chat", icon: MessageSquareText },
  { id: "knowledge_map" as Panel, label: "Knowledge Map", icon: Map },
  { id: "lint" as Panel, label: "Lint", icon: ShieldCheck },
  { id: "metrics" as Panel, label: "Metrics", icon: BarChart2 },
  { id: "tutorial" as Panel, label: "Tutorial", icon: BookOpen },
];

interface SidebarProps {
  active: Panel;
  onChange: (panel: Panel) => void;
}

export function Sidebar({ active, onChange }: SidebarProps) {
  return (
    <nav className="flex w-48 shrink-0 flex-col border-r border-border bg-card pt-3">
      {NAV.map(({ id, label, icon: Icon }) => {
        const on = active === id;
        return (
          <button
            key={id}
            onClick={() => onChange(id)}
            className={`flex items-center gap-3 border-l-2 px-4 py-2.5 text-sm transition-colors ${
              on
                ? "border-primary bg-primary/10 font-medium text-foreground"
                : "border-transparent text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
          >
            <Icon className={`h-4 w-4 ${on ? "text-primary" : ""}`} />
            {label}
          </button>
        );
      })}
    </nav>
  );
}
