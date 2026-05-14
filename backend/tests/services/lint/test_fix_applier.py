from pathlib import Path

import pytest

from models.lint_models import LintIssue
from models.wiki_models import Claim, Concept, Edge, Entity, Span
from services.lint.fix_applier import FixError, apply_fix
from services.wiki_store import WikiStore


@pytest.fixture
def store(tmp_path: Path) -> WikiStore:
    return WikiStore(root=tmp_path)


def _claim(store, cid="cl_001", source_id="src_001"):
    c = Claim(id=cid, text="t", subject_id="entity:e_001", source_id=source_id,
              span=Span(start=0, end=1, text="t"), confidence=0.9, polarity="asserts")
    store.append_claim(c)
    return c


def _edge(store, eid="ed_001"):
    e = Edge(id=eid, **{"from": "entity:a"}, to="entity:b", relation="mentions",
             source_id="src_001", span=Span(start=0, end=1, text="x"), confidence=0.9)
    store.append_edge(e)
    return e


def test_apply_fix_dangling_source_ref_claim(store):
    _claim(store, "cl_001")
    issue = LintIssue(
        id="dangling_source_ref:claim:cl_001", type="dangling_source_ref",
        severity="error", location="claims.jsonl:cl_001",
        description="x", suggested_fix="Delete claim", auto_fixable=True,
        payload={"kind": "claim", "claim_id": "cl_001", "source_id": "src_999"},
    )
    apply_fix(store, issue)
    assert store.read_all_claims() == []


def test_apply_fix_dangling_source_ref_edge(store):
    _edge(store, "ed_001")
    issue = LintIssue(
        id="dangling_source_ref:edge:ed_001", type="dangling_source_ref",
        severity="error", location="edges.jsonl:ed_001",
        description="x", suggested_fix="Delete edge", auto_fixable=True,
        payload={"kind": "edge", "edge_id": "ed_001", "source_id": "src_999"},
    )
    apply_fix(store, issue)
    assert store.read_all_edges() == []


def test_apply_fix_dangling_node_ref(store):
    _edge(store, "ed_001")
    issue = LintIssue(
        id="dangling_node_ref:edge:ed_001:to", type="dangling_node_ref",
        severity="error", location="edges.jsonl:ed_001",
        description="x", suggested_fix="Delete edge", auto_fixable=True,
        payload={"edge_id": "ed_001", "endpoint": "to", "missing_id": "entity:b"},
    )
    apply_fix(store, issue)
    assert store.read_all_edges() == []


def test_apply_fix_corrupted_jsonl(store):
    path = store.root / "wiki" / "claims.jsonl"
    path.write_text('{"id":"good"}\nBAD\n', encoding="utf-8")

    issue = LintIssue(
        id="corrupted_jsonl:claims.jsonl:2", type="corrupted_jsonl",
        severity="error", location="claims.jsonl:2",
        description="x", suggested_fix="Delete corrupt line", auto_fixable=True,
        payload={"file": "claims.jsonl", "line_no": 2},
    )
    apply_fix(store, issue)

    assert path.read_text(encoding="utf-8") == '{"id":"good"}\n'
    assert path.with_suffix(".jsonl.bak").exists()


def test_apply_fix_orphan_entity(store):
    e = Entity(id="e_001", type="Place", aliases=[], description="long enough description here.",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")
    issue = LintIssue(
        id="orphan_entity:e_001", type="orphan_entity",
        severity="warning", location="entity:e_001",
        description="x", suggested_fix="Delete entity", auto_fixable=True,
        payload={"entity_id": "e_001", "slug": "e_001", "entity_type": "Place"},
    )
    apply_fix(store, issue)
    assert not store.entity_exists("e_001", "Place")


def test_apply_fix_orphan_concept(store):
    c = Concept(id="c_001", definition="A long concept definition with characters.",
                examples=[], related=[], questions=["q?"], tags=[])
    store.write_concept(c, slug="c_001")
    issue = LintIssue(
        id="orphan_concept:c_001", type="orphan_concept",
        severity="warning", location="concept:c_001",
        description="x", suggested_fix="Delete concept", auto_fixable=True,
        payload={"concept_id": "c_001", "slug": "c_001"},
    )
    apply_fix(store, issue)
    assert not store.concept_exists("c_001")


def test_apply_fix_empty_description_entity(store):
    e = Entity(id="e_001", type="Place", aliases=[], description="short",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")

    issue = LintIssue(
        id="empty_description:entity:e_001", type="empty_description",
        severity="warning", location="entity:e_001",
        description="x", suggested_fix="Edit description inline", auto_fixable=True,
        payload={"node_id": "entity:e_001", "kind": "entity", "slug": "e_001", "entity_type": "Place"},
    )
    apply_fix(store, issue, edit_payload={"description": "A nice long replacement description."})

    assert store.read_entity("e_001", "Place").description == "A nice long replacement description."


def test_apply_fix_empty_description_concept(store):
    c = Concept(id="c_001", definition="short",
                examples=[], related=[], questions=["q?"], tags=[])
    store.write_concept(c, slug="c_001")

    issue = LintIssue(
        id="empty_description:concept:c_001", type="empty_description",
        severity="warning", location="concept:c_001",
        description="x", suggested_fix="Edit definition inline", auto_fixable=True,
        payload={"node_id": "concept:c_001", "kind": "concept", "slug": "c_001"},
    )
    apply_fix(store, issue, edit_payload={"description": "A long replacement concept definition."})

    assert store.read_concept("c_001").definition == "A long replacement concept definition."


def test_apply_fix_provenance_missing_raises(store):
    issue = LintIssue(
        id="provenance_missing:claim:cl_x", type="provenance_missing",
        severity="error", location="claims.jsonl:cl_x",
        description="x", suggested_fix=None, auto_fixable=False,
        payload={"kind": "claim", "claim_id": "cl_x"},
    )
    with pytest.raises(FixError):
        apply_fix(store, issue)


def test_apply_fix_empty_description_without_payload_raises(store):
    e = Entity(id="e_001", type="Place", aliases=[], description="short",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")
    issue = LintIssue(
        id="empty_description:entity:e_001", type="empty_description",
        severity="warning", location="entity:e_001",
        description="x", suggested_fix="Edit description inline", auto_fixable=True,
        payload={"node_id": "entity:e_001", "kind": "entity", "slug": "e_001", "entity_type": "Place"},
    )
    with pytest.raises(FixError):
        apply_fix(store, issue)


from unittest.mock import MagicMock
from models.lint_models import LlmQuestionsResult


def _mock_questions_llm(questions=None):
    questions = questions or ["What is X?", "How does Y work?", "Why Z?"]
    client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.parsed = LlmQuestionsResult(questions=questions)
    client.beta.chat.completions.parse.return_value = resp
    return client


def test_fix_empty_questions_entity(tmp_path):
    from models.wiki_models import Entity
    store = WikiStore(root=tmp_path)
    ent = Entity(id="e_001", type="Person", description="A person.", questions=[], tags=[])
    store.write_entity(ent, "jan")
    issue = LintIssue(
        id="empty_questions:entity:e_001",
        type="empty_questions",
        severity="warning",
        location="entity:e_001",
        description="Empty questions",
        auto_fixable=True,
        payload={"node_id": "entity:e_001", "slug": "jan", "entity_type": "Person"},
    )
    apply_fix(store, issue, llm_client=_mock_questions_llm())
    reloaded = store.read_entity("jan", "Person")
    assert len(reloaded.questions) == 3


def test_fix_empty_questions_concept(tmp_path):
    from models.wiki_models import Concept
    store = WikiStore(root=tmp_path)
    c = Concept(id="c_001", definition="A concept.", examples=[], related=[], questions=[], tags=[])
    store.write_concept(c, "my-concept")
    issue = LintIssue(
        id="empty_questions:concept:c_001",
        type="empty_questions",
        severity="warning",
        location="concept:c_001",
        description="Empty questions",
        auto_fixable=True,
        payload={"node_id": "concept:c_001", "slug": "my-concept"},
    )
    apply_fix(store, issue, llm_client=_mock_questions_llm(["Q1?", "Q2?"]))
    reloaded = store.read_concept("my-concept")
    assert reloaded.questions == ["Q1?", "Q2?"]


def test_fix_unmarked_contradiction_appends_edge(tmp_path):
    store = WikiStore(root=tmp_path)
    issue = LintIssue(
        id="unmarked_contradiction:cl_001:cl_002",
        type="unmarked_contradiction",
        severity="info",
        location="entity:e_001",
        description="Contradiction",
        auto_fixable=True,
        payload={"claim_a_id": "cl_001", "claim_b_id": "cl_002", "source_id": "src_001"},
    )
    apply_fix(store, issue)
    edges = store.read_all_edges()
    assert any(e.relation == "contradicts" for e in edges)
    contradicts = [e for e in edges if e.relation == "contradicts"]
    assert contradicts[0].from_ == "claim:cl_001"
    assert contradicts[0].to == "claim:cl_002"


def test_fix_stale_summary_updates_source(tmp_path):
    from datetime import datetime
    from models.wiki_models import Source
    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="T", type="article", raw_path="r",
        ingested_at=datetime.now(), summary="Old.", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, "test-source")
    issue = LintIssue(
        id="stale_summary:src_001",
        type="stale_summary",
        severity="info",
        location="source:src_001",
        description="Stale",
        auto_fixable=True,
        payload={"slug": "test-source", "source_id": "src_001", "proposed_summary": "New updated summary."},
    )
    apply_fix(store, issue)
    reloaded = store.read_source("test-source")
    assert reloaded.summary == "New updated summary."
