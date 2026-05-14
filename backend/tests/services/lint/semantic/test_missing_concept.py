from unittest.mock import MagicMock

from models.lint_models import MissingConceptJudgement
from models.wiki_models import Claim, Entity, Span
from services.lint.checks.semantic.missing_concept import check_missing_concept
from services.wiki_store import WikiStore


def _make_claim(id_, subject_id, source_id="src_001"):
    return Claim(
        id=id_, text=f"Claim text {id_}.", subject_id=subject_id, source_id=source_id,
        span=Span(start=0, end=10, text="test"), confidence=0.9, polarity="asserts",
    )


def _mock_llm(has_concept: bool, concept_name: str = "oświetlenie"):
    client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.parsed = MissingConceptJudgement(
        has_missing_concept=has_concept,
        concept_name=concept_name,
        explanation="many claims about topic",
    )
    client.beta.chat.completions.parse.return_value = resp
    return client


def test_detects_missing_concept(tmp_path):
    store = WikiStore(root=tmp_path)
    ent = Entity(id="e_001", type="Person", description="Entity.", questions=[], tags=[])
    store.write_entity(ent, "test-entity")
    for i in range(5):
        store.append_claim(_make_claim(f"cl_{i:03d}", "entity:e_001"))
    issues = check_missing_concept(store, llm_client=_mock_llm(True))
    assert len(issues) == 1
    assert issues[0].type == "missing_concept"
    assert issues[0].auto_fixable is False
    assert "oświetlenie" in issues[0].suggested_fix


def test_no_issue_below_threshold(tmp_path):
    store = WikiStore(root=tmp_path)
    for i in range(4):
        store.append_claim(_make_claim(f"cl_{i}", "entity:e_001"))
    mock = _mock_llm(True)
    issues = check_missing_concept(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_no_issue_when_llm_says_no_concept(tmp_path):
    store = WikiStore(root=tmp_path)
    for i in range(5):
        store.append_claim(_make_claim(f"cl_{i}", "entity:e_001"))
    issues = check_missing_concept(store, llm_client=_mock_llm(False))
    assert issues == []


def test_skips_non_entity_subjects(tmp_path):
    store = WikiStore(root=tmp_path)
    for i in range(5):
        store.append_claim(_make_claim(f"cl_{i}", "concept:c_001"))
    mock = _mock_llm(True)
    issues = check_missing_concept(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_empty_store_returns_no_issues(tmp_path):
    store = WikiStore(root=tmp_path)
    issues = check_missing_concept(store, llm_client=_mock_llm(True))
    assert issues == []
