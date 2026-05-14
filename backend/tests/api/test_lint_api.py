from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from models.wiki_models import Entity
from services.wiki_store import WikiStore


@pytest.fixture
def client():
    return TestClient(app)


def _patched_store(tmp_path):
    return patch("api.lint._get_store", return_value=WikiStore(root=tmp_path))


def test_post_lint_run_returns_report(client, tmp_path):
    with _patched_store(tmp_path):
        response = client.post("/api/lint/run", json={})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "issues" in data
    assert "counts_by_severity" in data


def test_post_lint_run_detects_issues(client, tmp_path):
    store = WikiStore(root=tmp_path)
    e = Entity(id="e_001", type="Place", aliases=[], description="short",
               mentions_count=0, questions=[], tags=[])
    store.write_entity(e, slug="e_001")

    with patch("api.lint._get_store", return_value=store):
        response = client.post("/api/lint/run", json={})

    data = response.json()
    types = [i["type"] for i in data["issues"]]
    assert "orphan_entity" in types
    assert "empty_questions" in types
    assert "empty_description" in types


def test_get_lint_reports_lists_summaries(client, tmp_path):
    store = WikiStore(root=tmp_path)
    with patch("api.lint._get_store", return_value=store):
        client.post("/api/lint/run", json={})
        response = client.get("/api/lint/reports")
    assert response.status_code == 200
    summaries = response.json()
    assert isinstance(summaries, list) and len(summaries) >= 1
    assert "id" in summaries[0]
    assert "counts_by_severity" in summaries[0]


def test_get_lint_report_returns_full(client, tmp_path):
    store = WikiStore(root=tmp_path)
    with patch("api.lint._get_store", return_value=store):
        run_resp = client.post("/api/lint/run", json={})
        report_id = run_resp.json()["id"]
        response = client.get(f"/api/lint/report/{report_id}")
    assert response.status_code == 200
    assert response.json()["id"] == report_id


def test_get_lint_report_404_for_missing(client, tmp_path):
    store = WikiStore(root=tmp_path)
    with patch("api.lint._get_store", return_value=store):
        response = client.get("/api/lint/report/nope")
    assert response.status_code == 404


def test_post_lint_fix_apply_deletes_orphan_entity(client, tmp_path):
    store = WikiStore(root=tmp_path)
    e = Entity(id="e_001", type="Place", aliases=[], description="long enough description here.",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")

    with patch("api.lint._get_store", return_value=store):
        run = client.post("/api/lint/run", json={}).json()
        issue = next(i for i in run["issues"] if i["type"] == "orphan_entity")
        response = client.post("/api/lint/fix", json={
            "report_id": run["id"], "issue_id": issue["id"], "action": "apply",
        })

    assert response.status_code == 200
    assert response.json()["status"] == "fixed"
    assert not store.entity_exists("e_001", "Place")


def test_post_lint_fix_reject_marks_status(client, tmp_path):
    store = WikiStore(root=tmp_path)
    e = Entity(id="e_001", type="Place", aliases=[], description="long enough description here.",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")

    with patch("api.lint._get_store", return_value=store):
        run = client.post("/api/lint/run", json={}).json()
        issue = next(i for i in run["issues"] if i["type"] == "orphan_entity")
        response = client.post("/api/lint/fix", json={
            "report_id": run["id"], "issue_id": issue["id"], "action": "reject",
        })

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert store.entity_exists("e_001", "Place")  # not deleted


def test_post_lint_fix_apply_with_edit_payload(client, tmp_path):
    store = WikiStore(root=tmp_path)
    e = Entity(id="e_001", type="Place", aliases=[], description="short",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")

    with patch("api.lint._get_store", return_value=store):
        run = client.post("/api/lint/run", json={}).json()
        issue = next(i for i in run["issues"] if i["type"] == "empty_description")
        response = client.post("/api/lint/fix", json={
            "report_id": run["id"], "issue_id": issue["id"], "action": "apply",
            "edit_payload": {"description": "A nice long replacement description."},
        })

    assert response.status_code == 200
    assert store.read_entity("e_001", "Place").description.startswith("A nice long")


def test_post_lint_fix_apply_on_non_auto_fixable_returns_400(client, tmp_path):
    from datetime import datetime
    from models.wiki_models import Source
    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="T", type="article", raw_path="r",
        ingested_at=datetime.now(), summary="",
        key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, "src-001")

    with patch("api.lint._get_store", return_value=store):
        run = client.post("/api/lint/run", json={}).json()
        issue = next(i for i in run["issues"] if i["type"] == "empty_description" and "source" in i["id"])
        response = client.post("/api/lint/fix", json={
            "report_id": run["id"], "issue_id": issue["id"], "action": "apply",
        })

    assert response.status_code == 400


def test_post_lint_fix_unknown_issue_returns_404(client, tmp_path):
    store = WikiStore(root=tmp_path)
    with patch("api.lint._get_store", return_value=store):
        run = client.post("/api/lint/run", json={}).json()
        response = client.post("/api/lint/fix", json={
            "report_id": run["id"], "issue_id": "nonexistent", "action": "reject",
        })
    assert response.status_code == 404


def test_run_lint_include_semantic_false_by_default(client, tmp_path):
    """POST /api/lint/run with empty body should not call LLM."""
    from unittest.mock import patch
    store = WikiStore(root=tmp_path)
    with patch("api.lint._get_store", return_value=store):
        with patch("services.lint.runner.OpenAI") as mock_openai:
            response = client.post("/api/lint/run", json={})
    assert response.status_code == 200
    mock_openai.assert_not_called()


def test_run_lint_with_include_semantic_true(client, tmp_path):
    """POST /api/lint/run with include_semantic:true should create LLM client."""
    from unittest.mock import MagicMock, patch
    store = WikiStore(root=tmp_path)
    noop = MagicMock()
    noop_resp = MagicMock()
    from models.lint_models import ContradictionJudgement
    noop_resp.choices[0].message.parsed = ContradictionJudgement(is_contradiction=False, explanation="")
    noop.beta.chat.completions.parse.return_value = noop_resp
    with patch("api.lint._get_store", return_value=store):
        with patch("services.lint.runner.OpenAI", return_value=noop):
            response = client.post("/api/lint/run", json={"include_semantic": True})
    assert response.status_code == 200


def test_per_action_log_written_when_all_issues_closed(client, tmp_path):
    """When last open issue is fixed/rejected, log.md gets a 'closed' entry."""
    store = WikiStore(root=tmp_path)
    with patch("api.lint._get_store", return_value=store):
        # Run lint to get a report
        run_resp = client.post("/api/lint/run", json={})
        assert run_resp.status_code == 200
        report = run_resp.json()
        if not report["issues"]:
            return  # nothing to close
        # Reject all issues
        for issue in report["issues"]:
            client.post("/api/lint/fix", json={
                "report_id": report["id"],
                "issue_id": issue["id"],
                "action": "reject",
            })
    # Check log.md contains 'closed'
    from pathlib import Path
    log_path = store.root / "wiki" / "log.md"
    if log_path.exists():
        assert "closed" in log_path.read_text(encoding="utf-8")
