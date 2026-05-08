from datetime import datetime
from pathlib import Path

import pytest

from models.wiki_models import Claim, Concept, Edge, Entity, Source, Span
from services.lint.checks.navigability import (
    check_empty_description,
    check_empty_questions,
    check_orphan_concept,
    check_orphan_entity,
)
from services.wiki_store import WikiStore


@pytest.fixture
def store(tmp_path: Path) -> WikiStore:
    return WikiStore(root=tmp_path)


def _src(store, sid="src_001"):
    s = Source(
        id=sid, title="T", type="txt", raw_path="r/x.md",
        ingested_at=datetime(2026, 5, 1), summary="A long summary that is well over thirty characters total.",
        key_takeaways=[], questions=["q?"], tags=[],
    )
    store.write_source(s, slug=sid)


# ── orphan_entity ──────────────────────────────────────────────────────────

def test_orphan_entity_detects_entity_with_no_edges_and_no_claims(store):
    e = Entity(id="e_001", type="Place", aliases=[], description="A long description with enough chars.",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")
    issues = check_orphan_entity(store)
    assert len(issues) == 1
    assert issues[0].payload == {"entity_id": "e_001", "slug": "e_001", "entity_type": "Place"}


def test_orphan_entity_skips_entity_with_claim(store):
    _src(store)
    e = Entity(id="e_001", type="Place", aliases=[], description="Long enough description here.",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")
    claim = Claim(id="cl_001", text="t", subject_id="entity:e_001", source_id="src_001",
                  span=Span(start=0, end=1, text="t"), confidence=0.9, polarity="asserts")
    store.append_claim(claim)
    assert check_orphan_entity(store) == []


def test_orphan_entity_skips_entity_with_incoming_edge(store):
    _src(store)
    e = Entity(id="e_001", type="Place", aliases=[], description="Long enough description here.",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")
    edge = Edge(id="ed_001", **{"from": "concept:c_999"}, to="entity:e_001",
                relation="mentions", source_id="src_001",
                span=Span(start=0, end=1, text="x"), confidence=0.9)
    store.append_edge(edge)
    assert check_orphan_entity(store) == []


# ── orphan_concept ─────────────────────────────────────────────────────────

def test_orphan_concept_detects_concept_with_no_incoming_edges(store):
    c = Concept(id="c_001", definition="A long concept definition with enough characters.",
                examples=[], related=[], questions=["q?"], tags=[])
    store.write_concept(c, slug="c_001")
    issues = check_orphan_concept(store)
    assert len(issues) == 1
    assert issues[0].payload == {"concept_id": "c_001", "slug": "c_001"}


def test_orphan_concept_skips_concept_with_incoming_edge(store):
    _src(store)
    c = Concept(id="c_001", definition="A long concept definition with enough characters.",
                examples=[], related=[], questions=["q?"], tags=[])
    store.write_concept(c, slug="c_001")
    edge = Edge(id="ed_001", **{"from": "entity:e_999"}, to="concept:c_001",
                relation="associated_with", source_id="src_001",
                span=Span(start=0, end=1, text="x"), confidence=0.9)
    store.append_edge(edge)
    assert check_orphan_concept(store) == []


# ── empty_questions ────────────────────────────────────────────────────────

def test_empty_questions_detects_entity_with_no_questions(store):
    e = Entity(id="e_001", type="Place", aliases=[], description="Long enough description here.",
               mentions_count=0, questions=[], tags=[])
    store.write_entity(e, slug="e_001")
    issues = check_empty_questions(store)
    assert any(i.payload.get("node_id") == "entity:e_001" for i in issues)


def test_empty_questions_detects_concept_with_no_questions(store):
    c = Concept(id="c_001", definition="A long concept definition with enough characters.",
                examples=[], related=[], questions=[], tags=[])
    store.write_concept(c, slug="c_001")
    issues = check_empty_questions(store)
    assert any(i.payload.get("node_id") == "concept:c_001" for i in issues)


def test_empty_questions_detects_source_with_no_questions(store):
    s = Source(id="src_001", title="T", type="txt", raw_path="r/x.md",
               ingested_at=datetime(2026, 5, 1),
               summary="A long summary that has over thirty characters in it.",
               key_takeaways=[], questions=[], tags=[])
    store.write_source(s, slug="src_001")
    issues = check_empty_questions(store)
    assert any(i.payload.get("node_id") == "source:src_001" for i in issues)


# ── empty_description ──────────────────────────────────────────────────────

def test_empty_description_flags_short_entity_description(store):
    e = Entity(id="e_001", type="Place", aliases=[], description="too short",
               mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(e, slug="e_001")
    issues = check_empty_description(store)
    assert any(i.payload.get("node_id") == "entity:e_001" for i in issues)


def test_empty_description_passes_long_concept_definition(store):
    c = Concept(id="c_001", definition="A long concept definition with plenty of characters here.",
                examples=[], related=[], questions=["q?"], tags=[])
    store.write_concept(c, slug="c_001")
    issues = check_empty_description(store)
    assert all(i.payload.get("node_id") != "concept:c_001" for i in issues)


def test_empty_description_flags_short_source_summary(store):
    s = Source(id="src_001", title="T", type="txt", raw_path="r/x.md",
               ingested_at=datetime(2026, 5, 1), summary="too short",
               key_takeaways=[], questions=["q?"], tags=[])
    store.write_source(s, slug="src_001")
    issues = check_empty_description(store)
    assert any(i.payload.get("node_id") == "source:src_001" for i in issues)
