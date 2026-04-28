import pytest
from datetime import datetime
from models.wiki_models import (
    Source, Entity, Concept, Claim, Edge,
    EntityType, RelationType, Polarity, Span
)


def test_source_minimal_valid():
    src = Source(
        id="src_001",
        title="Skandynawska sypialnia",
        type="article",
        raw_path="raw/skandynawska-sypialnia/parsed.md",
        ingested_at=datetime(2026, 4, 28, 10, 0, 0),
        summary="Krótkie streszczenie.",
        key_takeaways=["pkt 1"],
        questions=["jakie kolory?"],
        tags=["sypialnia"],
    )
    assert src.id == "src_001"


def test_entity_requires_valid_type():
    with pytest.raises(ValueError):
        Entity(id="e_001", type="UnknownType", description="x", questions=[], tags=[])


def test_entity_aliases_default_empty():
    e = Entity(id="e_001", type="Person", description="x", questions=[], tags=[])
    assert e.aliases == []


def test_concept_parent_optional():
    c = Concept(id="c_001", definition="def", examples=[], related=[], questions=[], tags=[])
    assert c.parent_concept is None


def test_claim_polarity_valid():
    span = Span(start=10, end=42, text="excerpt")
    cl = Claim(
        id="cl_001", text="X is Y", subject_id="entity:e_001",
        source_id="src_001", span=span, confidence=0.9, polarity="asserts"
    )
    assert cl.polarity == "asserts"


def test_claim_polarity_invalid_rejected():
    span = Span(start=0, end=10, text="x")
    with pytest.raises(ValueError):
        Claim(id="cl_001", text="X", subject_id="entity:e_001",
              source_id="src_001", span=span, confidence=0.5, polarity="maybe")


def test_claim_confidence_bounds():
    span = Span(start=0, end=10, text="x")
    with pytest.raises(ValueError):
        Claim(id="cl_001", text="X", subject_id="entity:e_001",
              source_id="src_001", span=span, confidence=1.5, polarity="asserts")


def test_edge_relation_must_be_in_closed_list():
    span = Span(start=0, end=10, text="x")
    with pytest.raises(ValueError):
        Edge(id="ed_001", from_="entity:a", to="entity:b",
             relation="randomly_invented", source_id="src_001",
             span=span, confidence=0.8)


def test_edge_with_valid_relation():
    span = Span(start=0, end=10, text="x")
    ed = Edge(id="ed_001", from_="entity:a", to="concept:c1",
              relation="associated_with", source_id="src_001",
              span=span, confidence=0.8)
    assert ed.relation == "associated_with"
