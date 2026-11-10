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
    assert r1.id != r2.id, "report IDs should be unique even on rapid back-to-back runs"
    summaries = list_reports(store)
    ids = {s["id"] for s in summaries}
    assert r1.id in ids and r2.id in ids
    assert len(summaries) == 2


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


# ---------------------------------------------------------------------------
# Tier 3 / include_semantic tests
# ---------------------------------------------------------------------------
from unittest.mock import MagicMock, patch
from models.lint_models import (
    ContradictionJudgement, AliasMergeJudgement,
    MissingConceptJudgement, StaleSummaryJudgement,
)


def _make_noop_llm():
    """LLM client that always returns 'no issue' for all Tier 3 checks."""
    client = MagicMock()
    resp = MagicMock()
    # Return negative results for all check types
    resp.choices[0].message.parsed = ContradictionJudgement(is_contradiction=False, explanation="")
    client.beta.chat.completions.parse.return_value = resp
    return client


def test_run_lint_without_semantic_does_not_call_llm(tmp_path):
    store = WikiStore(root=tmp_path)
    with patch("services.lint.runner.make_client") as mock_openai:
        report = run_lint(store, include_semantic=False)
    mock_openai.assert_not_called()
    assert report.counts_by_severity.get("info", 0) == 0


def test_run_lint_with_semantic_calls_tier3(tmp_path):
    from models.wiki_models import Claim, Span
    store = WikiStore(root=tmp_path)
    # Add contradicting claims to trigger unmarked_contradiction check
    for i, polarity in enumerate(["asserts", "denies"]):
        store.append_claim(Claim(
            id=f"cl_{i}", text=f"Claim {i}.", subject_id="entity:e_001",
            source_id="src_001", span=Span(start=0, end=5, text="test"),
            confidence=0.9, polarity=polarity,
        ))

    noop = _make_noop_llm()
    with patch("services.lint.runner.make_client", return_value=noop):
        report = run_lint(store, include_semantic=True)
    # LLM was called at least once (for unmarked_contradiction check)
    assert noop.beta.chat.completions.parse.called


def test_run_lint_semantic_issues_have_info_severity(tmp_path):
    from datetime import datetime
    from models.wiki_models import Claim, Source, Span
    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="T", type="article", raw_path="r",
        ingested_at=datetime.now(), summary="Summary.", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, "test")
    store.append_claim(Claim(
        id="cl_001", text="Fact.", subject_id="entity:e_001", source_id="src_001",
        span=Span(start=0, end=4, text="Fact"), confidence=0.9, polarity="asserts",
    ))

    # Mock stale_summary to return True
    stale_client = MagicMock()
    stale_resp = MagicMock()
    stale_resp.choices[0].message.parsed = StaleSummaryJudgement(
        is_stale=True, proposed_summary="Updated.", explanation="missing facts",
    )
    stale_client.beta.chat.completions.parse.return_value = stale_resp

    with patch("services.lint.runner.make_client", return_value=stale_client):
        report = run_lint(store, include_semantic=True)

    info_issues = [i for i in report.issues if i.severity == "info"]
    assert len(info_issues) >= 1
    assert all(i.severity == "info" for i in info_issues)
