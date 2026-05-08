import json
from datetime import datetime
from pathlib import Path

import pytest

from models.wiki_models import Claim, Entity, Source, Span
from services.lint.runner import (
    list_reports,
    load_report,
    run_lint,
    save_report,
    update_issue_status,
)
from services.wiki_index import regenerate_index
from services.wiki_store import WikiStore


@pytest.fixture
def store(tmp_path: Path) -> WikiStore:
    return WikiStore(root=tmp_path)


def test_run_lint_returns_empty_report_for_empty_wiki(store):
    report = run_lint(store)
    assert report.issues == []
    assert report.counts_by_severity == {"error": 0, "warning": 0, "info": 0}


def test_run_lint_detects_dangling_source_ref(store):
    claim = Claim(id="cl_001", text="t", subject_id="entity:e_001", source_id="src_999",
                  span=Span(start=0, end=1, text="t"), confidence=0.9, polarity="asserts")
    store.append_claim(claim)
    regenerate_index(store)

    report = run_lint(store)
    types = [i.type for i in report.issues]
    assert "dangling_source_ref" in types


def test_run_lint_writes_report_file_and_appends_log(store):
    e = Entity(id="e_001", type="Place", aliases=[], description="long enough description here.",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")

    report = run_lint(store)

    report_path = store.root / "wiki" / "lint_reports" / f"{report.id}.json"
    assert report_path.exists()
    parsed = json.loads(report_path.read_text(encoding="utf-8"))
    assert parsed["id"] == report.id

    log_path = store.root / "wiki" / "log.md"
    assert log_path.exists()
    log = log_path.read_text(encoding="utf-8")
    assert "lint" in log and report.id in log


def test_run_lint_aggregates_counts(store):
    e = Entity(id="e_001", type="Place", aliases=[], description="long enough description here.",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")
    claim = Claim(id="cl_001", text="t", subject_id="entity:e_999", source_id="src_999",
                  span=Span(start=0, end=1, text="t"), confidence=0.9, polarity="asserts")
    store.append_claim(claim)
    regenerate_index(store)

    report = run_lint(store)
    assert report.counts_by_severity["error"] >= 1
    assert report.counts_by_severity["warning"] >= 1


def test_list_reports_returns_summaries(store):
    r1 = run_lint(store)
    r2 = run_lint(store)
    summaries = list_reports(store)
    ids = {s["id"] for s in summaries}
    assert r1.id in ids and r2.id in ids


def test_load_report_returns_full_object(store):
    written = run_lint(store)
    loaded = load_report(store, written.id)
    assert loaded.id == written.id
    assert len(loaded.issues) == len(written.issues)


def test_update_issue_status_persists(store):
    e = Entity(id="e_001", type="Place", aliases=[], description="long enough description here.",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")
    report = run_lint(store)
    issue = next(i for i in report.issues if i.type == "orphan_entity")

    update_issue_status(store, report.id, issue.id, "rejected")

    reloaded = load_report(store, report.id)
    matched = next(i for i in reloaded.issues if i.id == issue.id)
    assert matched.status == "rejected"


def test_save_report_round_trip(store):
    report = run_lint(store)
    save_report(store, report)
    loaded = load_report(store, report.id)
    assert loaded.id == report.id
