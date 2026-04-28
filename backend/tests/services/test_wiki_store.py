import pytest
from datetime import datetime
from pathlib import Path
from services.wiki_store import WikiStore
from models.wiki_models import Source, Entity, Concept, Claim, Edge, Span


@pytest.fixture
def store(tmp_path):
    return WikiStore(root=tmp_path)


@pytest.fixture
def sample_source():
    return Source(
        id="src_001",
        title="Skandynawska sypialnia",
        type="article",
        raw_path="raw/skandynawska-sypialnia/parsed.md",
        ingested_at=datetime(2026, 4, 28, 10, 0, 0),
        summary="Krótkie streszczenie.",
        key_takeaways=["pkt 1", "pkt 2"],
        questions=["jakie kolory są typowe?"],
        tags=["sypialnia", "skandynawia"],
    )


def test_read_missing_source_returns_none(store):
    assert store.read_source("nonexistent") is None


def test_read_source_after_write(store, sample_source):
    store.write_source(sample_source, slug="skandynawska-sypialnia")
    loaded = store.read_source("skandynawska-sypialnia")
    assert loaded.id == sample_source.id
    assert loaded.title == sample_source.title
    assert loaded.questions == sample_source.questions


def test_list_sources_empty(store):
    assert store.list_sources() == []


def test_list_sources_after_writes(store, sample_source):
    store.write_source(sample_source, slug="a")
    other = sample_source.model_copy(update={"id": "src_002", "title": "B"})
    store.write_source(other, slug="b")
    slugs = store.list_sources()
    assert sorted(slugs) == ["a", "b"]


# ── entity / concept / claim / edge ──────────────────────────────────────────

@pytest.fixture
def sample_entity():
    return Entity(
        id="e_001", type="Place", aliases=["bedroom"],
        description="Sypialnia.", mentions_count=3,
        questions=["jakie kolory?"], tags=["pomieszczenie"]
    )


@pytest.fixture
def sample_concept():
    return Concept(
        id="c_001", parent_concept=None, definition="Neutralna kolorystyka.",
        examples=["beż", "biel"], related=["minimalizm"],
        questions=["jakie odcienie?"], tags=["kolory"]
    )


@pytest.fixture
def sample_claim():
    return Claim(
        id="cl_001", text="Sypialnia używa kolorów neutralnych.",
        subject_id="entity:e_001", source_id="src_001",
        span=Span(start=100, end=160, text="..."),
        confidence=0.92, polarity="asserts",
    )


@pytest.fixture
def sample_edge():
    return Edge(
        id="ed_001", **{"from": "entity:e_001"}, to="concept:c_001",
        relation="associated_with", source_id="src_001",
        span=Span(start=200, end=260, text="..."), confidence=0.88,
    )


def test_write_and_read_entity(store, sample_entity):
    store.write_entity(sample_entity, slug="sypialnia")
    loaded = store.read_entity(slug="sypialnia", entity_type="Place")
    assert loaded.id == sample_entity.id
    assert loaded.aliases == ["bedroom"]


def test_write_and_read_concept(store, sample_concept):
    store.write_concept(sample_concept, slug="kolory-neutralne")
    loaded = store.read_concept("kolory-neutralne")
    assert loaded.examples == ["beż", "biel"]


def test_append_claim_and_read_back(store, sample_claim):
    store.append_claim(sample_claim)
    claims = store.read_all_claims()
    assert len(claims) == 1
    assert claims[0].text == sample_claim.text


def test_append_multiple_claims(store, sample_claim):
    store.append_claim(sample_claim)
    second = sample_claim.model_copy(update={"id": "cl_002"})
    store.append_claim(second)
    assert len(store.read_all_claims()) == 2


def test_append_edge_and_read_back(store, sample_edge):
    store.append_edge(sample_edge)
    edges = store.read_all_edges()
    assert len(edges) == 1
    assert edges[0].relation == "associated_with"


def test_claims_dedup_by_hash(store, sample_claim):
    store.append_claim(sample_claim)
    store.append_claim(sample_claim)
    claims = store.read_all_claims()
    assert len(claims) == 1


def test_edges_dedup_by_tuple(store, sample_edge):
    store.append_edge(sample_edge)
    store.append_edge(sample_edge)
    edges = store.read_all_edges()
    assert len(edges) == 1


# ── merge operations ──────────────────────────────────────────────────────────

def test_entity_exists_check(store, sample_entity):
    assert not store.entity_exists("sypialnia", "Place")
    store.write_entity(sample_entity, slug="sypialnia")
    assert store.entity_exists("sypialnia", "Place")


def test_merge_entity_combines_aliases(store, sample_entity):
    store.write_entity(sample_entity, slug="sypialnia")
    updated = sample_entity.model_copy(update={
        "aliases": ["bedroom", "schlafzimmer"],
        "mentions_count": 5,
    })
    store.merge_entity(updated, slug="sypialnia")
    loaded = store.read_entity("sypialnia", "Place")
    assert sorted(loaded.aliases) == ["bedroom", "schlafzimmer"]
    assert loaded.mentions_count == 5


def test_merge_concept_combines_examples(store, sample_concept):
    store.write_concept(sample_concept, slug="kolory-neutralne")
    updated = sample_concept.model_copy(update={
        "examples": ["beż", "biel", "szary"],
    })
    store.merge_concept(updated, slug="kolory-neutralne")
    loaded = store.read_concept("kolory-neutralne")
    assert sorted(loaded.examples) == ["beż", "biel", "szary"]
