import { useEffect, useState } from "react";
import { Play, RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "../../api/client";
import type { IssueSeverity, IssueStatus, LintReport } from "../../types";
import { LintIssueRow } from "./LintIssueRow";

type SeverityFilter = "all" | IssueSeverity;
type StatusFilter = "all" | IssueStatus;

export function LintPanel() {
  const [report, setReport] = useState<LintReport | null>(null);
  const [running, setRunning] = useState(false);
  const [busyIssueId, setBusyIssueId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("open");
  const [includeSemantic, setIncludeSemantic] = useState(false);

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
        <button
          onClick={runNow}
          disabled={running}
          className="flex items-center gap-1.5 ml-auto px-3 py-1.5 text-xs rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {running ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {running ? "Running…" : "Run Now"}
        </button>
      </div>

      {/* Summary + filters */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border shrink-0 flex-wrap">
        {report ? (
          <span className="text-xs text-muted-foreground">
            Report{" "}
            <span className="font-mono text-foreground">{report.id}</span> ·{" "}
            <span className="text-red-600">{sev.error} errors</span> ·{" "}
            <span className="text-yellow-600">{sev.warning} warnings</span> ·{" "}
            <span className="text-blue-500">{sev.info ?? 0} info</span> ·{" "}
            {issues.length} total
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">
            No lint reports yet. Click <span className="font-medium">Run Now</span>.
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

      {error && (
        <div className="px-4 py-2 text-xs text-red-600 bg-red-100/40 border-b border-red-200">
          {error}
        </div>
      )}

      {/* Issue list */}
      <div className="flex-1 overflow-auto p-4 flex flex-col gap-2">
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
          />
        ))}
      </div>
    </div>
  );
}
