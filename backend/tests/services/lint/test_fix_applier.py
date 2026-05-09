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
