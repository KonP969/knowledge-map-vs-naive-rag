import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.lint_models import LintReport
from services.lint.fix_applier import FixError, apply_fix
from services.lint.runner import (
    list_reports,
    load_report,
    run_lint,
    update_issue_status,
)
from services.wiki_store import WikiStore


router = APIRouter(prefix="/api/lint", tags=["lint"])

_WIKI_DATA_DIR = Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default"))


def _get_store() -> WikiStore:
    return WikiStore(root=_WIKI_DATA_DIR)


class RunLintBody(BaseModel):
    pass


class FixBody(BaseModel):
    report_id: str
    issue_id: str
    action: Literal["apply", "reject", "wontfix"]
    edit_payload: Optional[Dict[str, Any]] = None


@router.post("/run", response_model=LintReport)
def post_run_lint(_body: RunLintBody = RunLintBody()):
    store = _get_store()
    return run_lint(store)


@router.get("/reports", response_model=List[Dict[str, Any]])
def get_reports():
    store = _get_store()
    return list_reports(store)


@router.get("/report/{report_id}", response_model=LintReport)
def get_report(report_id: str):
    store = _get_store()
    try:
        return load_report(store, report_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")


@router.post("/fix", response_model=Dict[str, Any])
def post_fix(body: FixBody):
    store = _get_store()
    try:
        report = load_report(store, body.report_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Report {body.report_id} not found")

    issue = next((i for i in report.issues if i.id == body.issue_id), None)
    if issue is None:
        raise HTTPException(status_code=404, detail=f"Issue {body.issue_id} not found")

    if body.action == "apply":
        try:
            apply_fix(store, issue, edit_payload=body.edit_payload)
        except FixError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        new_status = "fixed"
    elif body.action == "reject":
        new_status = "rejected"
    else:
        new_status = "wontfix"

    update_issue_status(store, body.report_id, body.issue_id, new_status)
    return {"id": body.issue_id, "status": new_status}
