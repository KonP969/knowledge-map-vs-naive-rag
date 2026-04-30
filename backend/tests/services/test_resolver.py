import pytest
from services.wiki_store import WikiStore
from models.ingest_models import (
    SourceClassification, EntityMention, ConceptMention, ClaimExtraction,
)
from models.wiki_models import Entity, Concept, Span
from services.resolver import resolve_classification


@pytest.fixture
def store(tmp_path):
    return WikiStore(root=tmp_path)


@pytest.fixture
def simple_classification():
    return SourceClassification(
        title="Scandinavian Bedroom",
        description="Article about bedroom design.",
        tags=["bedroom"],
        questions=["What materials?"],
        key_takeaways=["Wood dominates."],
        entity_mentions=[
            EntityMention(
                name="Sypialnia",
                type="Place",
                aliases=["bedroom"],
                description="A Scandinavian bedroom.",
                span=Span(start=0, end=8, text="Sypialnia"),
            )
        ],
        concept_mentions=[
            ConceptMention(
                name="neutral palette",
                definition="Whites, beiges, and grays.",
                span=Span(start=10, end=24, text="neutral palette"),
            )
        ],
        claims=[
            ClaimExtraction(
                text="Sypialnia uses neutral palette.",
                subject_name="Sypialnia",
                subject_type="entity",
                span=Span(start=0, end=30, text="Sypialnia uses neutral palette."),
                confidence=0.9,
                polarity="asserts",
            )
        ],
    )


def test_resolve_creates_new_entity(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    assert result["entities_created"] == 1
    assert result["entities_merged"] == 0


def test_resolve_creates_new_concept(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    assert result["concepts_created"] == 1
    assert result["concepts_merged"] == 0


def test_resolve_entity_persisted_in_store(store, simple_classification):
    resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    entity = store.read_entity("sypialnia", "Place")
    assert entity is not None
    assert entity.type == "Place"


def test_resolve_concept_persisted_in_store(store, simple_classification):
    resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    concept = store.read_concept("neutral-palette")
    assert concept is not None


def test_resolve_merges_existing_entity(store, simple_classification):
    # Pre-create entity with same name
    existing = Entity(
        id="e_001", type="Place", aliases=["room"],
        description="Existing description.",
        questions=[], tags=["old-tag"],
    )
    store.write_entity(existing, slug="sypialnia")

    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    assert result["entities_created"] == 0
    assert result["entities_merged"] == 1
    # aliases should be merged
    entity = store.read_entity("sypialnia", "Place")
    assert "bedroom" in entity.aliases
    assert "room" in entity.aliases


def test_resolve_merges_existing_concept(store, simple_classification):
    existing = Concept(
        id="c_001",
        definition="Old definition.",
        examples=["white"], related=[],
        questions=[], tags=["old"],
    )
    store.write_concept(existing, slug="neutral-palette")

    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    assert result["concepts_created"] == 0
    assert result["concepts_merged"] == 1


def test_resolve_creates_claims(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    assert len(result["claims"]) == 1
    assert result["claims"][0].polarity == "asserts"


def test_resolve_creates_mentions_edges(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    # One edge per entity mention + one per concept mention
    assert len(result["edges"]) >= 1
    relations = [e.relation for e in result["edges"]]
    assert "mentions" in relations


def test_resolve_claim_subject_id_uses_resolved_entity_id(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    claim = result["claims"][0]
    # subject_id must start with "entity:" or "concept:"
    assert claim.subject_id.startswith("entity:") or claim.subject_id.startswith("concept:")


def test_resolve_entity_id_format(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    entity = store.read_entity("sypialnia", "Place")
    assert entity.id.startswith("e_")


def test_resolve_concept_id_format(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    concept = store.read_concept("neutral-palette")
    assert concept.id.startswith("c_")


def test_resolve_entity_id_is_e001_in_empty_store(store, simple_classification):
    resolve_classification(simple_classification, "src_001", store)
    entity = store.read_entity("sypialnia", "Place")
    assert entity.id == "e_001"


def test_resolve_entity_id_seeds_correctly_with_preexisting(store, simple_classification):
    # Pre-create entity with id e_003 (simulating a gap)
    pre = Entity(
        id="e_003", type="Place", aliases=[],
        description="Pre-existing.", questions=[], tags=[],
    )
    store.write_entity(pre, slug="preexisting")
    # Now resolve a new entity — it should get e_004, not e_001 or e_002
    result = resolve_classification(simple_classification, "src_001", store)
    entity = store.read_entity("sypialnia", "Place")
    assert entity.id == "e_004"


def test_resolve_edge_count_matches_mentions(store, simple_classification):
    result = resolve_classification(simple_classification, "src_001", store)
    # simple_classification has 1 entity mention + 1 concept mention = 2 edges
    assert len(result["edges"]) == 2
