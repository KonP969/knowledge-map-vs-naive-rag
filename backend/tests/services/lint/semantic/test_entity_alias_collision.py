from unittest.mock import MagicMock

from models.lint_models import AliasMergeJudgement
from models.wiki_models import Entity
from services.lint.checks.semantic.entity_alias_collision import (
    _edit_distance,
    check_entity_alias_collision,
)
from services.wiki_store import WikiStore


def _mock_llm(should_merge: bool, canonical: str = "jan-kowalski"):
    client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.parsed = AliasMergeJudgement(
        should_merge=should_merge,
        explanation="test",
        suggested_canonical=canonical,
    )
    client.beta.chat.completions.parse.return_value = resp
    return client


def _write_entity(store, slug, entity_type="Person", entity_id=None):
    ent = Entity(
        id=entity_id or f"e_{slug}",
        type=entity_type,
        description="A person.",
        questions=[],
        tags=[],
    )
    store.write_entity(ent, slug)
    return ent


def test_edit_distance_same():
    assert _edit_distance("abc", "abc") == 0


def test_edit_distance_one_insertion():
    assert _edit_distance("abc", "abcd") == 1


def test_edit_distance_substitution():
    assert _edit_distance("abc", "axc") == 1


def test_detects_collision(tmp_path):
    store = WikiStore(root=tmp_path)
    _write_entity(store, "jan-kowalski", entity_id="e_001")
    _write_entity(store, "jan-kowalsky", entity_id="e_002")
    issues = check_entity_alias_collision(store, llm_client=_mock_llm(True, "jan-kowalski"))
    assert len(issues) == 1
    assert issues[0].type == "entity_alias_collision"
    assert issues[0].auto_fixable is False
    assert "jan-kowalski" in issues[0].suggested_fix


def test_no_issue_when_llm_says_keep_separate(tmp_path):
    store = WikiStore(root=tmp_path)
    _write_entity(store, "jan-kowalski", entity_id="e_001")
    _write_entity(store, "jan-kowalsky", entity_id="e_002")
    issues = check_entity_alias_collision(store, llm_client=_mock_llm(False))
    assert issues == []


def test_no_issue_when_distance_gte_3(tmp_path):
    store = WikiStore(root=tmp_path)
    _write_entity(store, "jan-kowalski", entity_id="e_001")
    _write_entity(store, "anna-nowak", entity_id="e_002")
    mock = _mock_llm(True)
    issues = check_entity_alias_collision(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_empty_store_returns_no_issues(tmp_path):
    store = WikiStore(root=tmp_path)
    issues = check_entity_alias_collision(store, llm_client=_mock_llm(True))
    assert issues == []


def test_respects_cap(tmp_path):
    store = WikiStore(root=tmp_path)
    for i in range(30):
        _write_entity(store, f"jan-{i:02d}", entity_id=f"e_{i:03d}")
    mock = _mock_llm(True)
    check_entity_alias_collision(store, llm_client=mock)
    assert mock.beta.chat.completions.parse.call_count <= 50
