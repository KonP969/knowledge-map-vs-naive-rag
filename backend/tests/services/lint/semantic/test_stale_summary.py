from datetime import datetime
from unittest.mock import MagicMock

from models.lint_models import StaleSummaryJudgement
from models.wiki_models import Claim, Source, Span
from services.lint.checks.semantic.stale_summary import check_stale_summary
from services.wiki_store import WikiStore


def _make_source(slug, source_id="src_001"):
    return Source(
        id=source_id, title="Test Source", type="article", raw_path=f"raw/{slug}",
        ingested_at=datetime.now(), summary="Original summary.",
        key_takeaways=[], questions=[], tags=[],
    )


def _make_claim(id_, source_id="src_001"):
    return Claim(
        id=id_, text="New important fact.", subject_id="entity:e_001", source_id=source_id,
        span=Span(start=0, end=10, text="test"), confidence=0.9, polarity="asserts",
    )


def _mock_llm(is_stale: bool, proposed="Updated summary."):
    client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.parsed = StaleSummaryJudgement(
        is_stale=is_stale, proposed_summary=proposed, explanation="missing facts",
    )
    client.beta.chat.completions.parse.return_value = resp
    return client


def test_detects_stale_summary(tmp_path):
    store = WikiStore(root=tmp_path)
    store.write_source(_make_source("test"), "test")
    store.append_claim(_make_claim("cl_001"))
    issues = check_stale_summary(store, llm_client=_mock_llm(True, "Updated summary."))
    assert len(issues) == 1
    assert issues[0].type == "stale_summary"
    assert issues[0].auto_fixable is True
    assert issues[0].payload["proposed_summary"] == "Updated summary."
    assert issues[0].payload["slug"] == "test"


def test_no_issue_when_llm_says_fresh(tmp_path):
    store = WikiStore(root=tmp_path)
    store.write_source(_make_source("test"), "test")
    store.append_claim(_make_claim("cl_001"))
    issues = check_stale_summary(store, llm_client=_mock_llm(False))
    assert issues == []


def test_skips_source_with_no_claims(tmp_path):
    store = WikiStore(root=tmp_path)
    store.write_source(_make_source("test"), "test")
    mock = _mock_llm(True)
    issues = check_stale_summary(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_empty_store_returns_no_issues(tmp_path):
    store = WikiStore(root=tmp_path)
    issues = check_stale_summary(store, llm_client=_mock_llm(True))
    assert issues == []


def test_respects_cap(tmp_path):
    store = WikiStore(root=tmp_path)
    for i in range(60):
        src = _make_source(f"s{i}", source_id=f"src_{i:03d}")
        store.write_source(src, f"s{i}")
        store.append_claim(_make_claim(f"cl_{i}", source_id=f"src_{i:03d}"))
    mock = _mock_llm(True)
    check_stale_summary(store, llm_client=mock)
    assert mock.beta.chat.completions.parse.call_count <= 50
