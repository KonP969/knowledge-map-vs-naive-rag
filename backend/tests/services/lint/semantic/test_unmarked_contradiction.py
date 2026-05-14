from datetime import datetime
from unittest.mock import MagicMock

import pytest

from models.lint_models import ContradictionJudgement
from models.wiki_models import Claim, Edge, Span
from services.lint.checks.semantic.unmarked_contradiction import check_unmarked_contradiction
from services.wiki_store import WikiStore


def _make_span():
    return Span(start=0, end=10, text="test")


def _make_claim(id_, subject_id, polarity, text="Some claim.", source_id="src_001"):
    return Claim(
        id=id_, text=text, subject_id=subject_id, source_id=source_id,
        span=_make_span(), confidence=0.9, polarity=polarity,
    )


def _mock_llm(is_contradiction: bool):
    client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.parsed = ContradictionJudgement(
        is_contradiction=is_contradiction,
        explanation="test explanation",
    )
    client.beta.chat.completions.parse.return_value = resp
    return client


def _store_with_claims(tmp_path, claims, edges=None):
    store = WikiStore(root=tmp_path)
    for c in claims:
        store.append_claim(c)
    for e in edges or []:
        store.append_edge(e)
    return store


def test_detects_contradiction(tmp_path):
    claims = [
        _make_claim("cl_001", "entity:e_001", "asserts", "Entity is great."),
        _make_claim("cl_002", "entity:e_001", "denies", "Entity is not great."),
    ]
    store = _store_with_claims(tmp_path, claims)
    issues = check_unmarked_contradiction(store, llm_client=_mock_llm(True))
    assert len(issues) == 1
    assert issues[0].type == "unmarked_contradiction"
    assert issues[0].severity == "info"
    assert issues[0].auto_fixable is True
    assert issues[0].payload["claim_a_id"] == "cl_001"
    assert issues[0].payload["claim_b_id"] == "cl_002"


def test_no_issue_when_llm_says_not_contradiction(tmp_path):
    claims = [
        _make_claim("cl_001", "entity:e_001", "asserts"),
        _make_claim("cl_002", "entity:e_001", "denies"),
    ]
    store = _store_with_claims(tmp_path, claims)
    issues = check_unmarked_contradiction(store, llm_client=_mock_llm(False))
    assert issues == []


def test_no_issue_when_same_polarity(tmp_path):
    claims = [
        _make_claim("cl_001", "entity:e_001", "asserts"),
        _make_claim("cl_002", "entity:e_001", "asserts"),
    ]
    store = _store_with_claims(tmp_path, claims)
    mock = _mock_llm(True)
    issues = check_unmarked_contradiction(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_no_issue_when_contradicts_edge_exists(tmp_path):
    claims = [
        _make_claim("cl_001", "entity:e_001", "asserts"),
        _make_claim("cl_002", "entity:e_001", "denies"),
    ]
    edge = Edge(
        id="e_c01",
        **{"from": "claim:cl_001"},
        to="claim:cl_002",
        relation="contradicts",
        source_id="src_001",
        span=_make_span(),
        confidence=1.0,
    )
    store = _store_with_claims(tmp_path, claims, edges=[edge])
    mock = _mock_llm(True)
    issues = check_unmarked_contradiction(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_empty_store_returns_no_issues(tmp_path):
    store = WikiStore(root=tmp_path)
    issues = check_unmarked_contradiction(store, llm_client=_mock_llm(True))
    assert issues == []


def test_respects_cap(tmp_path):
    # 60 subjects each with one asserts + one denies claim = 60 pairs
    claims = []
    for i in range(60):
        claims.append(_make_claim(f"ca_{i}", f"entity:e_{i:03d}", "asserts"))
        claims.append(_make_claim(f"cd_{i}", f"entity:e_{i:03d}", "denies"))
    store = _store_with_claims(tmp_path, claims)
    mock = _mock_llm(True)
    issues = check_unmarked_contradiction(store, llm_client=mock)
    assert mock.beta.chat.completions.parse.call_count <= 50
    assert len(issues) <= 50
