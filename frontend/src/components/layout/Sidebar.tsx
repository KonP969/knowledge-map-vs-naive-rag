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
    <nav data-tour="nav" className="flex shrink-0 overflow-x-auto border-b border-border bg-card md:w-48 md:flex-col md:overflow-visible md:border-b-0 md:border-r md:pt-3">
      {NAV.map(({ id, label, icon: Icon }) => {
        const on = active === id;
        return (
          <button
            key={id}
            data-tour={`nav-${id}`}
            onClick={() => onChange(id)}
            aria-current={on ? "page" : undefined}
            className={`flex shrink-0 items-center gap-2 whitespace-nowrap border-b-2 px-3 py-3 text-sm transition-colors md:gap-3 md:border-b-0 md:border-l-2 md:px-4 md:py-2.5 ${
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
