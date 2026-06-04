import { useState } from "react";
import { AlertTriangle, AlertOctagon, Info, Check, X, Ban, Sparkles, MapPin } from "lucide-react";
import type { LintIssue } from "../../types";

const GRAPH_NODE_PREFIXES = ["entity:", "concept:", "source:"];

function isGraphNodeLocation(location: string): boolean {
  return GRAPH_NODE_PREFIXES.some((p) => location.startsWith(p));
}

const TYPE_LABELS: Record<string, string> = {
  provenance_missing: "Brak proweniencji",
  dangling_source_ref: "Odwołanie do usuniętego źródła",
  dangling_node_ref: "Odwołanie do nieistniejącego węzła",
  corrupted_jsonl: "Uszkodzony plik danych",
  orphan_entity: "Encja bez powiązań",
  orphan_concept: "Koncept bez powiązań",
  empty_questions: "Brak pytań",
  empty_description: "Brak opisu",
  unmarked_contradiction: "Nieoflagowana sprzeczność",
  entity_alias_collision: "Kolizja aliasów encji",
  missing_concept: "Brakujący koncept",
  stale_summary: "Nieaktualny opis",
};

const FIX_DESCRIPTIONS: Record<string, string> = {
  provenance_missing: "Uzupełni brakujące dane proweniencji",
  dangling_source_ref: "Usunie odwołanie do nieistniejącego źródła",
  dangling_node_ref: "Usunie krawędź wskazującą na nieistniejący węzeł",
  orphan_entity: "Oflaguje encję jako izolowaną",
  orphan_concept: "Oflaguje koncept jako izolowany",
  empty_questions: "Wygeneruje pytania pomocne przy wyszukiwaniu (LLM)",
  empty_description: "Zapisze podany opis",
  entity_alias_collision: "Połączy encje z identycznymi aliasami",
  missing_concept: "Doda brakujący koncept do wiki",
};

function formatLocation(location: string): string {
  const prefixes = ["entity:", "concept:", "source:", "claim:", "edge:"];
  let clean = location;
  for (const p of prefixes) {
    if (clean.startsWith(p)) { clean = clean.slice(p.length); break; }
  }
  return clean.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const SEVERITY_ICON = {
  error: AlertOctagon,
  warning: AlertTriangle,
  info: Info,
};

const SEVERITY_COLOR: Record<string, string> = {
  error: "text-red-600 dark:text-red-400",
  warning: "text-yellow-600 dark:text-yellow-400",
  info: "text-blue-500",
};

const STATUS_BADGE: Record<string, string> = {
  open: "bg-muted text-muted-foreground",
  fixed: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  rejected: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  wontfix: "bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
};

interface LintIssueRowProps {
  issue: LintIssue;
  onApply: (issueId: string, editPayload?: { description: string }) => void;
  onReject: (issueId: string) => void;
  onWontFix: (issueId: string) => void;
  onLocationClick?: (location: string) => void;
  busy: boolean;
}

export function LintIssueRow({ issue, onApply, onReject, onWontFix, onLocationClick, busy }: LintIssueRowProps) {
  const Icon = SEVERITY_ICON[issue.severity];
  const isEmptyDescriptionEdit = issue.type === "empty_description" && issue.auto_fixable;
  const isGenerateQuestions = issue.type === "empty_questions" && issue.auto_fixable;
  const [editText, setEditText] = useState("");
  const editValid = editText.trim().length >= 30;
  const closed = issue.status !== "open";
  const entitySlug = typeof issue.payload?.slug === "string" ? issue.payload.slug : "";
  const locationClickable = !!onLocationClick && isGraphNodeLocation(issue.location);

  return (
    <div className="border border-border rounded-md p-3 flex flex-col gap-2 text-xs bg-card">
      <div className="flex items-start gap-2">
        <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${SEVERITY_COLOR[issue.severity]}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-[11px] text-foreground">
              {TYPE_LABELS[issue.type] ?? issue.type}
            </span>
            <span className="text-[11px] text-muted-foreground">·</span>
            {locationClickable ? (
              <button
                onClick={() => onLocationClick!(issue.location)}
                className="flex items-center gap-0.5 text-[11px] text-primary hover:underline truncate"
                title={`Pokaż w Knowledge Map: ${issue.location}`}
              >
                <MapPin className="w-2.5 h-2.5 shrink-0" />
                {formatLocation(issue.location)}
              </button>
            ) : (
              <span className="text-[11px] text-muted-foreground truncate" title={issue.location}>
                {formatLocation(issue.location)}
              </span>
            )}
            <span className={`ml-auto px-2 py-0.5 rounded text-[10px] uppercase ${STATUS_BADGE[issue.status]}`}>
              {issue.status}
            </span>
          </div>
          <p className="mt-1 text-foreground leading-snug">{issue.description}</p>
          {issue.suggested_fix && (
            <p className="mt-1 text-muted-foreground">suggested: {issue.suggested_fix}</p>
          )}
        </div>
      </div>

      {!closed && isEmptyDescriptionEdit && (
        <div className="space-y-1">
          <p className="text-[11px] text-muted-foreground">
            {entitySlug ? <>Opisz: <span className="font-medium text-foreground">{entitySlug}</span>. </> : null}
            Wygeneruj opis automatycznie (AI) lub wpisz własny (≥30 znaków).
          </p>
          <textarea
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            placeholder="Własny opis (≥30 znaków)…"
            rows={2}
            className="w-full px-2 py-1 text-xs border border-border rounded bg-background focus:outline-none focus:ring-1 focus:ring-primary/40"
          />
        </div>
      )}

      {!closed && (
        <div className="flex gap-2 flex-wrap">
          {isEmptyDescriptionEdit ? (
            <>
              <button
                disabled={busy}
                onClick={() => onApply(issue.id)}
                className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-violet-600 text-white hover:opacity-90 transition-opacity disabled:opacity-40"
                title="Wygeneruj opis na podstawie kontekstu encji (LLM)"
              >
                <Sparkles className="w-3 h-3" /> Wygeneruj opis (AI)
              </button>
              <button
                disabled={busy || !editValid}
                onClick={() => onApply(issue.id, { description: editText.trim() })}
                className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Check className="w-3 h-3" /> Zapisz mój opis
              </button>
            </>
          ) : isGenerateQuestions ? (
            <button
              disabled={busy}
              onClick={() => onApply(issue.id)}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-violet-600 text-white hover:opacity-90 transition-opacity disabled:opacity-40"
            >
              <Sparkles className="w-3 h-3" /> Generate Questions
            </button>
          ) : (
            <button
              disabled={busy || !issue.auto_fixable}
              onClick={() => onApply(issue.id)}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
              title={FIX_DESCRIPTIONS[issue.type] ?? (issue.auto_fixable ? "Zastosuj automatyczną poprawkę" : "Brak automatycznej poprawki")}
            >
              <Check className="w-3 h-3" /> Apply Fix
            </button>
          )}
          <button
            disabled={busy}
            onClick={() => onReject(issue.id)}
            className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40"
          >
            <X className="w-3 h-3" /> Reject
          </button>
          <button
            disabled={busy}
            onClick={() => onWontFix(issue.id)}
            className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40"
          >
            <Ban className="w-3 h-3" /> Won't fix
          </button>
        </div>
      )}
    </div>
  );
}
