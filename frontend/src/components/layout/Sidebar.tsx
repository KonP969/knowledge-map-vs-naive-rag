import { FileText, Layers, ScatterChart, MessageSquare, BarChart2, BookOpen, Database, Zap, MessageSquareText, Map, ShieldCheck } from "lucide-react";
import type { Panel } from "../../types";

const NAV = [
  { id: "documents" as Panel, label: "Documents", icon: FileText },
  { id: "chunks" as Panel, label: "Chunking Lab", icon: Layers },
  { id: "embeddings" as Panel, label: "Embeddings", icon: ScatterChart },
  { id: "chat" as Panel, label: "Chat", icon: MessageSquare },
  { id: "metrics" as Panel, label: "Metrics", icon: BarChart2 },
  { id: "tutorial" as Panel, label: "Tutorial", icon: BookOpen },
  { id: "sources" as Panel, label: "Sources", icon: Database },
  { id: "ingest" as Panel, label: "Ingest", icon: Zap },
  { id: "chat_trace" as Panel, label: "Wiki Chat", icon: MessageSquareText },
  { id: "knowledge_map" as Panel, label: "Knowledge Map", icon: Map },
  { id: "lint" as Panel, label: "Lint", icon: ShieldCheck },
];

interface SidebarProps {
  active: Panel;
  onChange: (panel: Panel) => void;
}

export function Sidebar({ active, onChange }: SidebarProps) {
  return (
    <nav className="w-48 border-r border-border bg-card flex flex-col pt-4 shrink-0">
      {NAV.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onChange(id)}
          className={`flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
            active === id
              ? "bg-primary/15 text-primary font-medium"
              : "text-muted-foreground hover:bg-muted hover:text-foreground"
          }`}
        >
          <Icon className="w-4 h-4" />
          {label}
        </button>
      ))}
    </nav>
  );
}
