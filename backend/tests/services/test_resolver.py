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


# ── deterministic span grounding (offsets recomputed from verbatim text) ──────

def test_resolve_grounds_claim_span_offsets_from_source_text(store, simple_classification):
    # The LLM returned correct verbatim text but bogus offsets (start=999/end=1000).
    bad = simple_classification.model_copy(deep=True)
    bad.claims[0].span = Span(start=999, end=1000, text="Sypialnia uses neutral palette")
    source_text = "Intro line.\nSypialnia uses neutral palette here."

    result = resolve_classification(
        classification=bad, source_id="src_001", store=store, source_text=source_text,
    )

    span = result["claims"][0].span
    assert source_text[span.start:span.end] == "Sypialnia uses neutral palette"
    assert span.start == source_text.index("Sypialnia uses neutral palette")
    assert span.text == "Sypialnia uses neutral palette"


def test_resolve_leaves_span_when_text_not_in_source(store, simple_classification):
    bad = simple_classification.model_copy(deep=True)
    bad.claims[0].span = Span(start=5, end=12, text="NOT PRESENT VERBATIM")
    source_text = "Completely different document content."

    result = resolve_classification(
        classification=bad, source_id="src_001", store=store, source_text=source_text,
    )

    span = result["claims"][0].span
    assert span.start == 5 and span.end == 12  # unchanged
    assert span.text == "NOT PRESENT VERBATIM"


def test_resolve_without_source_text_leaves_span_unchanged(store, simple_classification):
    # Backward compatible: no source_text passed → spans pass through verbatim.
    result = resolve_classification(
        classification=simple_classification, source_id="src_001", store=store,
    )
    span = result["claims"][0].span
    assert span.start == 0 and span.end == 30


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


def test_resolve_claim_id_seeds_from_max_not_count(store, simple_classification):
    # A gap in the claim sequence (only cl_005 present) must not cause id reuse.
    from models.wiki_models import Claim, Span
    store.append_claim(Claim(
        id="cl_005", text="x", subject_id="entity:e_001", source_id="src_000",
        span=Span(start=0, end=1, text="x"), confidence=0.9, polarity="asserts",
    ))
    result = resolve_classification(
        classification=simple_classification, source_id="src_001", store=store,
    )
    new_ids = [c.id for c in result["claims"]]
    assert "cl_005" not in new_ids       # no collision
    assert new_ids == ["cl_006"]         # max(5)+1, not len(1)+1


def test_resolve_no_overwrite_preserves_existing_entity(store, simple_classification):
    existing = Entity(
        id="e_001", type="Place", aliases=["room"],
        description="Manually edited description.",
        questions=[], tags=["old"],
    )
    store.write_entity(existing, slug="sypialnia")

    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
        overwrite_existing=False,
    )

    entity = store.read_entity("sypialnia", "Place")
    assert entity.description == "Manually edited description."  # preserved, not overwritten
    assert entity.aliases == ["room"]                            # not merged
    # claim still links to the existing entity's id
    assert result["claims"][0].subject_id == "entity:e_001"


def test_resolve_no_overwrite_still_creates_missing_concept(store, simple_classification):
    # The concept does not exist yet; it MUST be created so concept-claims can link.
    resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
        overwrite_existing=False,
    )
    assert store.concept_exists("neutral-palette")


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


# ── node resolution across the whole store (aliases, prefixes, types) ─────────
# A claim's subject is often phrased differently from the entity's name
# ("drzwi ukryte PORTA HIDE" vs "PORTA HIDE"), and often refers to a node that an
# EARLIER document created. Exact in-document matching left most subjects dangling.

def _claim_only(subject_name, subject_type="entity"):
    return SourceClassification(
        title="Doc", description="d", tags=[], questions=[], key_takeaways=[],
        entity_mentions=[], concept_mentions=[],
        claims=[ClaimExtraction(
            text=f"{subject_name} is great.", subject_name=subject_name,
            subject_type=subject_type, span=Span(start=0, end=1, text="x"),
            confidence=0.9, polarity="asserts",
        )],
    )


def _existing(store, slug, eid, etype="Product", aliases=None):
    store.write_entity(Entity(id=eid, type=etype, aliases=aliases or [],
                              description="Existing node.", questions=[], tags=[]), slug=slug)


def test_claim_subject_links_to_entity_created_by_earlier_document(store):
    _existing(store, "porta-hide", "e_006")
    result = resolve_classification(_claim_only("PORTA HIDE"), "src_002", store)
    assert result["claims"][0].subject_id == "entity:e_006"


def test_claim_subject_with_descriptive_prefix_links_to_core_entity(store):
    _existing(store, "porta-hide", "e_006")
    for phrase in ("drzwi ukryte PORTA HIDE", "modele z kolekcji PORTA HIDE"):
        result = resolve_classification(_claim_only(phrase), "src_002", store)
        assert result["claims"][0].subject_id == "entity:e_006", phrase


def test_claim_subject_matches_existing_alias(store):
    _existing(store, "porta-hide", "e_006", aliases=["drzwi bezprzylgowe HIDE"])
    result = resolve_classification(_claim_only("drzwi bezprzylgowe HIDE"), "src_002", store)
    assert result["claims"][0].subject_id == "entity:e_006"


def test_claim_subject_typed_as_concept_links_to_matching_entity(store):
    _existing(store, "porta-hide", "e_006")
    result = resolve_classification(_claim_only("PORTA HIDE", "concept"), "src_002", store)
    assert result["claims"][0].subject_id == "entity:e_006"


def test_longer_product_name_is_not_collapsed_into_shorter_one(store):
    # "PORTA SYSTEM ELEGANCE" is a different product than "PORTA SYSTEM".
    _existing(store, "porta-system", "e_010")
    result = resolve_classification(_claim_only("PORTA SYSTEM ELEGANCE"), "src_002", store)
    assert result["claims"][0].subject_id != "entity:e_010"


def test_single_word_node_does_not_swallow_longer_names(store):
    _existing(store, "porta", "e_001", etype="Org")
    result = resolve_classification(_claim_only("drzwi PORTA HIDE"), "src_002", store)
    assert result["claims"][0].subject_id != "entity:e_001"


def test_entity_mention_with_other_type_merges_into_existing_node(store):
    _existing(store, "porta-hide", "e_006", etype="Product")
    cls = SourceClassification(
        title="Doc", description="d", tags=[], questions=[], key_takeaways=[],
        entity_mentions=[EntityMention(name="PORTA HIDE", type="Org", aliases=[],
                                       description="Hidden doors.",
                                       span=Span(start=0, end=10, text="PORTA HIDE"))],
        concept_mentions=[], claims=[],
    )
    result = resolve_classification(cls, "src_002", store)
    assert not store.entity_exists("porta-hide", "Org")
    assert result["entities_created"] == 0 and result["entities_merged"] == 1
    assert result["edges"][0].to == "entity:e_006"


def test_generic_leading_words_are_stripped_before_matching(store):
    _existing(store, "porta", "e_001", etype="Org")
    result = resolve_classification(_claim_only("drzwi wewnętrzne PORTA"), "src_002", store)
    assert result["claims"][0].subject_id == "entity:e_001"


def test_unmatched_subject_becomes_a_concept_node(store):
    result = resolve_classification(_claim_only("zielona łazienka", "concept"), "src_001", store)
    subject = result["claims"][0].subject_id
    concept = store.read_concept("zielona-lazienka")
    assert concept is not None
    assert subject == f"concept:{concept.id}"
    assert concept.definition  # seeded from the claim text, not empty
    assert any(e.to == subject for e in result["edges"])  # source -> new node edge


def test_same_topic_in_two_documents_lands_on_one_node(store):
    r1 = resolve_classification(_claim_only("zielona łazienka", "concept"), "src_001", store)
    r2 = resolve_classification(_claim_only("Zielona łazienka", "concept"), "src_002", store)
    assert r1["claims"][0].subject_id == r2["claims"][0].subject_id
