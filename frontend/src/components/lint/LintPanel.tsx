import { useEffect, useState } from "react";
import { Play, RefreshCw, ShieldCheck, Wand2 } from "lucide-react";
import { api } from "../../api/client";
import type { IssueSeverity, IssueStatus, LintReport } from "../../types";
import { LintIssueRow } from "./LintIssueRow";

// Types that need manual input (description) or a slow LLM call — excluded from bulk Fix all.
const NON_BULK_TYPES = new Set(["empty_description", "empty_questions"]);

type SeverityFilter = "all" | IssueSeverity;
type StatusFilter = "all" | IssueStatus;

interface LintPanelProps {
  onLocationClick?: (location: string) => void;
}

export function LintPanel({ onLocationClick }: LintPanelProps = {}) {
  const [report, setReport] = useState<LintReport | null>(null);
  const [running, setRunning] = useState(false);
  const [busyIssueId, setBusyIssueId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("open");
  const [includeSemantic, setIncludeSemantic] = useState(false);
  const [confirmFixAll, setConfirmFixAll] = useState(false);
  const [fixingAll, setFixingAll] = useState(false);
  const [fixAllProgress, setFixAllProgress] = useState({ current: 0, total: 0 });

  async function loadLatestReport() {
    try {
      const summaries = await api.listLintReports();
      if (summaries.length === 0) { setReport(null); return; }
      const latest = await api.getLintReport(summaries[0].id);
      setReport(latest);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => { loadLatestReport(); }, []);

  async function runNow() {
    setRunning(true);
    setError(null);
    try {
      const fresh = await api.runLint(includeSemantic);
      setReport(fresh);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  async function applyAction(
    issueId: string,
    action: "apply" | "reject" | "wontfix",
    editPayload?: { description: string },
  ) {
    if (!report) return;
    setBusyIssueId(issueId);
    setError(null);
    try {
      await api.applyLintFix({ report_id: report.id, issue_id: issueId, action, edit_payload: editPayload });
      const refreshed = await api.getLintReport(report.id);
      setReport(refreshed);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyIssueId(null);
    }
  }

  const issues = report?.issues ?? [];
  const filtered = issues.filter((i) => {
    if (severityFilter !== "all" && i.severity !== severityFilter) return false;
    if (statusFilter !== "all" && i.status !== statusFilter) return false;
    return true;
  });

  const bulkFixable = issues.filter(
    (i) => i.status === "open" && i.auto_fixable && !NON_BULK_TYPES.has(i.type),
  );

  async function fixAll() {
    if (!report) return;
    setConfirmFixAll(false);
    setFixingAll(true);
    setError(null);
    const targets = bulkFixable;
    setFixAllProgress({ current: 0, total: targets.length });
    let done = 0;
    let failures = 0;
    for (const issue of targets) {
      try {
        await api.applyLintFix({ report_id: report.id, issue_id: issue.id, action: "apply" });
      } catch {
        failures++;
      }
      done++;
      setFixAllProgress({ current: done, total: targets.length });
    }
    try {
      const refreshed = await api.getLintReport(report.id);
      setReport(refreshed);
    } catch (e) {
      setError((e as Error).message);
    }
    if (failures > 0) setError(`${failures} of ${targets.length} fixes failed.`);
    setFixingAll(false);
  }

  const sev = report?.counts_by_severity ?? { error: 0, warning: 0, info: 0 };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border shrink-0 flex-wrap">
        <ShieldCheck className="w-4 h-4 text-primary" />
        <h2 className="text-sm font-medium">Lint</h2>
        <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
          <input
            type="checkbox"
            checked={includeSemantic}
            onChange={(e) => setIncludeSemantic(e.target.checked)}
            className="rounded"
          />
          Semantic checks{" "}
          <span className="text-muted-foreground/60">(LLM, ~30–60s)</span>
        </label>
        <div className="ml-auto flex items-center gap-2">
          {fixingAll ? (
            <span className="flex items-center gap-1.5 text-xs text-primary">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              Fixing {fixAllProgress.current}/{fixAllProgress.total}…
            </span>
          ) : confirmFixAll ? (
            <span className="flex items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">Fix all {bulkFixable.length}?</span>
              <button onClick={fixAll} className="text-primary hover:underline font-medium px-1">
                Yes
              </button>
              <button onClick={() => setConfirmFixAll(false)} className="text-muted-foreground hover:text-foreground px-1">
                No
              </button>
            </span>
          ) : (
            bulkFixable.length > 0 && (
              <button
                onClick={() => setConfirmFixAll(true)}
                disabled={running}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md border border-primary/40 text-primary hover:bg-primary/10 transition-colors disabled:opacity-40"
                title="Apply every automatic fix at once (no LLM, no manual edits)"
              >
                <Wand2 className="w-3.5 h-3.5" />
                Fix all ({bulkFixable.length})
              </button>
            )
          )}
          <button
            onClick={runNow}
            disabled={running || fixingAll}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            {running ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
            {running ? "Running…" : "Run Now"}
          </button>
        </div>
      </div>

      {/* Summary + filters */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border shrink-0 flex-wrap">
        {report ? (
          <span className="text-xs text-muted-foreground">
            Report{" "}
            <span className="font-mono text-foreground">{report.id}</span> ·{" "}
            <span className="text-error">{sev.error} errors</span> ·{" "}
            <span className="text-warning">{sev.warning} warnings</span> ·{" "}
            <span className="text-foreground/80">{sev.info ?? 0} info</span> ·{" "}
            {issues.length} total
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">
            No report yet.
          </span>
        )}
        <div className="flex gap-1 ml-auto">
          {(["all", "error", "warning", "info"] as SeverityFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setSeverityFilter(s)}
              className={`px-2 py-0.5 rounded text-xs capitalize transition-colors ${
                severityFilter === s
                  ? "bg-primary/15 text-primary font-medium"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <span className="text-muted-foreground text-xs">|</span>
        <div className="flex gap-1">
          {(["open", "fixed", "rejected", "wontfix", "all"] as StatusFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-2 py-0.5 rounded text-xs capitalize transition-colors ${
                statusFilter === s
                  ? "bg-primary/15 text-primary font-medium"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Panel explanation */}
      <div className="px-4 py-2.5 bg-muted/40 border-b border-border text-xs text-muted-foreground shrink-0">
        <span className="font-medium text-foreground">What is Lint?</span>{" "}
        Automatic quality checks over the wiki — missing descriptions, contradictory claims, duplicates.
        Run it, then <span className="font-medium text-foreground">Apply Fix</span> or{" "}
        <span className="font-medium text-foreground">Reject</span> on each issue.
      </div>

      {error && (
        <div className="px-4 py-2 text-xs text-error bg-error/10 border-b border-error/30">
          {error}
        </div>
      )}

      {/* Issue list */}
      <div className="flex-1 overflow-auto p-4 flex flex-col gap-2">
        {!report && !error && (
          <div className="m-auto max-w-sm py-16 text-center">
            <p className="text-sm font-medium text-foreground">
              {running ? "Checking the wiki…" : "No lint report yet"}
            </p>
            <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
              Lint walks every node, claim and edge and lists what needs attention: missing
              descriptions, orphaned nodes, duplicates and contradictions.
            </p>
            {!running && (
              <button
                onClick={runNow}
                disabled={fixingAll}
                className="mt-5 inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-40"
              >
                <Play className="h-3.5 w-3.5" />
                Run the first check
              </button>
            )}
          </div>
        )}
        {report && filtered.length === 0 && (
          <div className="text-center text-muted-foreground text-sm py-12">
            {issues.length === 0 ? "No issues found." : "No issues match the current filter."}
          </div>
        )}
        {filtered.map((issue) => (
          <LintIssueRow
            key={issue.id}
            issue={issue}
            busy={busyIssueId === issue.id}
            onApply={(id, payload) => applyAction(id, "apply", payload)}
            onReject={(id) => applyAction(id, "reject")}
            onWontFix={(id) => applyAction(id, "wontfix")}
            onLocationClick={onLocationClick}
          />
        ))}
      </div>
    </div>
  );
}
