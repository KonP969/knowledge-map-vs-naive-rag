from datetime import datetime
from pathlib import Path

import pytest

from models.wiki_models import Claim, Edge, Entity, Source, Span
from services.lint.checks.provenance import (
    check_corrupted_jsonl,
    check_dangling_node_ref,
    check_dangling_source_ref,
    check_provenance_missing,
)
from services.wiki_index import regenerate_index
from services.wiki_store import WikiStore


@pytest.fixture
def store(tmp_path: Path) -> WikiStore:
    return WikiStore(root=tmp_path)


def _add_source(store: WikiStore, source_id: str = "src_001") -> None:
    src = Source(
        id=source_id, title="T", type="txt",
        raw_path="r/x.md", ingested_at=datetime(2026, 5, 1),
        summary="S", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, slug=source_id)


def _add_entity(store: WikiStore, entity_id: str = "e_001", type_: str = "Place") -> None:
    e = Entity(
        id=entity_id, type=type_, aliases=[], description="A description.",
        mentions_count=0, questions=[], tags=[],
    )
    store.write_entity(e, slug=entity_id)


# -- provenance_missing -----------------------------------------------------

def test_provenance_missing_detects_claim_without_source_id(store: WikiStore):
    # Bypass Pydantic by writing raw JSONL line missing source_id
    bad_line = '{"id":"cl_x","text":"x","subject_id":"entity:e_001","span":{"start":0,"end":1,"text":"x"},"confidence":0.9,"polarity":"asserts"}\n'
    (store.root / "wiki" / "claims.jsonl").write_text(bad_line, encoding="utf-8")
    issues = check_provenance_missing(store)
    assert any(i.type == "provenance_missing" for i in issues)


def test_provenance_missing_detects_edge_without_span(store: WikiStore):
    bad_line = '{"id":"e_x","from":"entity:a","to":"entity:b","relation":"mentions","source_id":"src_001","confidence":0.9}\n'
    (store.root / "wiki" / "edges.jsonl").write_text(bad_line, encoding="utf-8")
    issues = check_provenance_missing(store)
    assert any(i.type == "provenance_missing" and "e_x" in i.location for i in issues)


def test_provenance_missing_clean_returns_empty(store: WikiStore):
    _add_source(store)
    claim = Claim(
        id="cl_001", text="t", subject_id="entity:e_001", source_id="src_001",
        span=Span(start=0, end=1, text="t"), confidence=0.9, polarity="asserts",
    )
    store.append_claim(claim)
    assert check_provenance_missing(store) == []


# -- dangling_source_ref ----------------------------------------------------

def test_dangling_source_ref_detects_missing_source_for_claim(store: WikiStore):
    claim = Claim(
        id="cl_001", text="t", subject_id="entity:e_001", source_id="src_999",
        span=Span(start=0, end=1, text="t"), confidence=0.9, polarity="asserts",
    )
    store.append_claim(claim)
    regenerate_index(store)
    issues = check_dangling_source_ref(store)
    assert len(issues) == 1
    assert issues[0].payload == {"kind": "claim", "claim_id": "cl_001", "source_id": "src_999"}


def test_dangling_source_ref_detects_missing_source_for_edge(store: WikiStore):
    edge = Edge(
        id="ed_001", **{"from": "entity:a"}, to="entity:b", relation="mentions",
        source_id="src_999", span=Span(start=0, end=1, text="x"), confidence=0.9,
    )
    store.append_edge(edge)
    regenerate_index(store)
    issues = check_dangling_source_ref(store)
    assert len(issues) == 1
    assert issues[0].payload["kind"] == "edge"


def test_dangling_source_ref_clean_when_source_exists(store: WikiStore):
    _add_source(store)
    claim = Claim(
        id="cl_001", text="t", subject_id="entity:e_001", source_id="src_001",
        span=Span(start=0, end=1, text="t"), confidence=0.9, polarity="asserts",
    )
    store.append_claim(claim)
    regenerate_index(store)
    assert check_dangling_source_ref(store) == []


# -- dangling_node_ref ------------------------------------------------------

def test_dangling_node_ref_detects_missing_to(store: WikiStore):
    _add_source(store)
    _add_entity(store, "e_001")
    edge = Edge(
        id="ed_001", **{"from": "entity:e_001"}, to="entity:e_999",
        relation="mentions", source_id="src_001",
        span=Span(start=0, end=1, text="x"), confidence=0.9,
    )
    store.append_edge(edge)
    regenerate_index(store)
    issues = check_dangling_node_ref(store)
    assert len(issues) == 1
    assert issues[0].payload["missing_id"] == "entity:e_999"


def test_dangling_node_ref_clean_when_both_nodes_exist(store: WikiStore):
    _add_source(store)
    _add_entity(store, "e_001")
    _add_entity(store, "e_002")
    edge = Edge(
        id="ed_001", **{"from": "entity:e_001"}, to="entity:e_002",
        relation="mentions", source_id="src_001",
        span=Span(start=0, end=1, text="x"), confidence=0.9,
    )
    store.append_edge(edge)
    regenerate_index(store)
    assert check_dangling_node_ref(store) == []


# -- corrupted_jsonl --------------------------------------------------------

def test_corrupted_jsonl_detects_unparseable_line(store: WikiStore):
    (store.root / "wiki" / "claims.jsonl").write_text(
        '{"id":"cl_001"}\nthis is not json\n', encoding="utf-8"
    )
    issues = check_corrupted_jsonl(store)
    assert len(issues) == 1
    assert "claims.jsonl:2" in issues[0].location


def test_corrupted_jsonl_handles_missing_files(store: WikiStore):
    # No claims.jsonl, no edges.jsonl -- should not raise
    assert check_corrupted_jsonl(store) == []


def test_corrupted_jsonl_skips_blank_lines(store: WikiStore):
    (store.root / "wiki" / "claims.jsonl").write_text(
        '{"id":"x"}\n\n   \n', encoding="utf-8"
    )
    assert check_corrupted_jsonl(store) == []
