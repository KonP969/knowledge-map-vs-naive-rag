from datetime import datetime

import pytest
from pydantic import ValidationError

from models.lint_models import LintIssue, LintReport


def test_lint_issue_minimal_fields():
    issue = LintIssue(
        id="dangling_source_ref:claim:cl_001",
        type="dangling_source_ref",
        severity="error",
        location="claims.jsonl:cl_001",
        description="Claim cl_001 references missing source src_999",
        suggested_fix="Delete claim",
        auto_fixable=True,
        payload={"claim_id": "cl_001"},
    )
    assert issue.status == "open"
    assert issue.severity == "error"


def test_lint_issue_invalid_severity_rejected():
    with pytest.raises(ValidationError):
        LintIssue(
            id="x",
            type="orphan_entity",
            severity="critical",  # not in literal
            location="entity:e_001",
            description="x",
            suggested_fix=None,
            auto_fixable=False,
        )


def test_lint_issue_invalid_type_rejected():
    with pytest.raises(ValidationError):
        LintIssue(
            id="x",
            type="not_a_real_type",
            severity="error",
            location="x",
            description="x",
            suggested_fix=None,
            auto_fixable=False,
        )


def test_lint_report_with_issues():
    issue = LintIssue(
        id="orphan_entity:e_001",
        type="orphan_entity",
        severity="warning",
        location="entity:e_001",
        description="Entity has no claims and no edges",
        suggested_fix="Delete entity",
        auto_fixable=True,
        payload={"entity_id": "e_001", "slug": "test", "entity_type": "Person"},
    )
    report = LintReport(
        id="2026-05-07T14-30-00",
        created_at=datetime(2026, 5, 7, 14, 30, 0),
        issues=[issue],
        counts_by_severity={"error": 0, "warning": 1, "info": 0},
        counts_by_type={"orphan_entity": 1},
    )
    assert len(report.issues) == 1
    assert report.counts_by_severity["warning"] == 1


def test_lint_issue_status_can_be_updated():
    issue = LintIssue(
        id="x",
        type="orphan_concept",
        severity="warning",
        location="concept:c_001",
        description="x",
        suggested_fix="Delete concept",
        auto_fixable=True,
    )
    issue.status = "fixed"
    assert issue.status == "fixed"
