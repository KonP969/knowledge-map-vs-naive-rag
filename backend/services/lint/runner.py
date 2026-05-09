import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from models.lint_models import IssueStatus, LintIssue, LintReport
from services.lint.checks.navigability import (
    check_empty_description,
    check_empty_questions,
    check_orphan_concept,
    check_orphan_entity,
)
from services.lint.checks.provenance import (
    check_corrupted_jsonl,
    check_dangling_node_ref,
    check_dangling_source_ref,
    check_provenance_missing,
)
from services.wiki_log import append_log_entry
from services.wiki_store import WikiStore


def _reports_dir(store: WikiStore) -> Path:
    d = store.root / "wiki" / "lint_reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_report_id(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H-%M-%S-%f")


def _aggregate_issues(issues: List[LintIssue]) -> Tuple[Dict[str, int], Dict[str, int]]:
    sev = {"error": 0, "warning": 0, "info": 0}
    by_type: Dict[str, int] = {}
    for i in issues:
        sev[i.severity] = sev.get(i.severity, 0) + 1
        by_type[i.type] = by_type.get(i.type, 0) + 1
    return sev, by_type


def run_lint(store: WikiStore) -> LintReport:
    issues: List[LintIssue] = []
    issues.extend(check_corrupted_jsonl(store))
    issues.extend(check_provenance_missing(store))
    issues.extend(check_dangling_source_ref(store))
    issues.extend(check_dangling_node_ref(store))
    issues.extend(check_orphan_entity(store))
    issues.extend(check_orphan_concept(store))
    issues.extend(check_empty_questions(store))
    issues.extend(check_empty_description(store))

    now = datetime.now()
    report_id = _make_report_id(now)
    sev, by_type = _aggregate_issues(issues)

    report = LintReport(
        id=report_id,
        created_at=now,
        issues=issues,
        counts_by_severity=sev,
        counts_by_type=by_type,
    )

    save_report(store, report)
    append_log_entry(
        store,
        op="lint",
        source_id=None,
        details=f"run {report_id} | found: {len(issues)} ({sev['error']} errors, {sev['warning']} warnings)",
        timestamp=now,
    )
    return report


def save_report(store: WikiStore, report: LintReport) -> None:
    path = _reports_dir(store) / f"{report.id}.json"
    payload = report.model_dump(mode="json")
    store._atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False))


def load_report(store: WikiStore, report_id: str) -> LintReport:
    path = _reports_dir(store) / f"{report_id}.json"
    return LintReport.model_validate_json(path.read_text(encoding="utf-8"))


def list_reports(store: WikiStore) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in sorted(_reports_dir(store).glob("*.json"), reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        out.append({
            "id": data.get("id", p.stem),
            "created_at": data.get("created_at"),
            "counts_by_severity": data.get("counts_by_severity", {}),
            "total": len(data.get("issues", [])),
        })
    return out


def update_issue_status(
    store: WikiStore,
    report_id: str,
    issue_id: str,
    new_status: IssueStatus,
) -> LintReport:
    report = load_report(store, report_id)
    found = False
    for i in report.issues:
        if i.id == issue_id:
            i.status = new_status
            found = True
            break
    if not found:
        raise KeyError(f"Issue {issue_id} not found in report {report_id}")
    save_report(store, report)
    return report
