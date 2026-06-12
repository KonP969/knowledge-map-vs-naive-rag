from datetime import datetime

import pytest

from models.ingest_models import ClaimExtraction, ConceptMention, EntityMention, SourceClassification
from models.wiki_models import Claim, Entity, Source, Span
from services.claim_backfill import reextract_claims_all, reextract_claims_for_source
from services.wiki_store import WikiStore


def _classification(claims):
    """A SourceClassification carrying the given ClaimExtractions, with one Azura entity mention."""
    return SourceClassification(
        title="Azura",
        description="desc",
        tags=["t"],
        questions=["q?"],
        key_takeaways=["k"],
        entity_mentions=[
            EntityMention(
                name="Azura", type="Product", aliases=[],
                description="A product line.", span=Span(start=0, end=5, text="Azura"),
            )
        ],
        concept_mentions=[],
        claims=claims,
    )


def _seed_source_with_raw(store, slug="azura-src", source_id="src_001", text="Azura is gold. Azura is matte."):
    src = Source(
        id=source_id, title="Azura", type="txt",
        raw_path=f"raw/{slug}/parsed.md",
        ingested_at=datetime(2026, 5, 1), source_url=None,
        summary="S", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, slug=slug)
    raw_file = store.root / "raw" / slug / "parsed.md"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_text(text, encoding="utf-8")


def _existing_entity(store):
    store.write_entity(
        Entity(id="e_001", type="Product", aliases=[], description="A product line.",
               mentions_count=1, questions=[], tags=[]),
        slug="azura",
    )


def test_reextract_all_isolates_failing_source(tmp_path):
    # One source whose classification blows up must not kill the others.
    store = WikiStore(root=tmp_path)
    _seed_source_with_raw(store, slug="good-src", source_id="src_001", text="Azura is gold.")
    _seed_source_with_raw(store, slug="bad-src", source_id="src_002", text="BOOM trigger text")
    _existing_entity(store)

    def classify(text):
        if "BOOM" in text:
            raise RuntimeError("connection lost")
        return _classification([
            ClaimExtraction(text="Azura is available in gold.", subject_name="Azura",
                            subject_type="entity", span=Span(start=0, end=14, text="Azura is gold"),
                            confidence=0.9, polarity="asserts"),
        ])

    results = reextract_claims_all(store, apply=True, classify_fn=classify)
    by_slug = {r.slug: r for r in results}
    assert by_slug["good-src"].applied is True
    assert by_slug["bad-src"].applied is False
    assert "connection lost" in (by_slug["bad-src"].skipped_reason or "")
    # good source's claims actually landed
    assert any(c.source_id == "src_001" for c in store.read_all_claims())


@pytest.fixture
def fake_classify():
    claims = [
        ClaimExtraction(text="Azura is available in gold.", subject_name="Azura",
                        subject_type="entity", span=Span(start=0, end=14, text="Azura is gold"),
                        confidence=0.9, polarity="asserts"),
        ClaimExtraction(text="Azura is available in matte black.", subject_name="Azura",
                        subject_type="entity", span=Span(start=15, end=30, text="Azura is matte"),
                        confidence=0.9, polarity="asserts"),
    ]
    return lambda text: _classification(claims)


def test_dry_run_reports_counts_without_writing(tmp_path, fake_classify):
    store = WikiStore(root=tmp_path)
    _existing_entity(store)
    _seed_source_with_raw(store)
    # one stale claim already on this source
    store.append_claim(Claim(id="cl_001", text="old", subject_id="entity:e_001",
                             source_id="src_001", span=Span(start=0, end=1, text="o"),
                             confidence=0.5, polarity="asserts"))

    result = reextract_claims_for_source("azura-src", store, apply=False, classify_fn=fake_classify)

    assert result.old_count == 1
    assert result.new_count == 2
    assert result.applied is False
    # store untouched in dry-run
    assert [c.id for c in store.read_all_claims()] == ["cl_001"]


def test_apply_replaces_source_claims_and_maps_existing_entity(tmp_path, fake_classify):
    store = WikiStore(root=tmp_path)
    _existing_entity(store)
    _seed_source_with_raw(store)
    store.append_claim(Claim(id="cl_001", text="old", subject_id="entity:e_001",
                             source_id="src_001", span=Span(start=0, end=1, text="o"),
                             confidence=0.5, polarity="asserts"))
    # an unrelated claim on another source must survive
    store.append_claim(Claim(id="cl_900", text="other", subject_id="entity:e_002",
                             source_id="src_002", span=Span(start=0, end=1, text="x"),
                             confidence=0.9, polarity="asserts"))

    result = reextract_claims_for_source("azura-src", store, apply=True, classify_fn=fake_classify)

    assert result.applied is True
    assert result.new_count == 2
    claims = store.read_all_claims()
    by_source = {}
    for c in claims:
        by_source.setdefault(c.source_id, []).append(c)
    assert len(by_source["src_001"]) == 2          # stale replaced
    assert {c.text for c in by_source["src_001"]} == {
        "Azura is available in gold.", "Azura is available in matte black."}
    assert all(c.subject_id == "entity:e_001" for c in by_source["src_001"])  # mapped to existing
    assert [c.id for c in by_source["src_002"]] == ["cl_900"]  # other source preserved
    # entity not overwritten
    assert store.read_entity("azura", "Product").description == "A product line."


def test_reextract_all_returns_one_result_per_source(tmp_path, fake_classify):
    store = WikiStore(root=tmp_path)
    _existing_entity(store)
    _seed_source_with_raw(store, slug="azura-a", source_id="src_001")
    _seed_source_with_raw(store, slug="azura-b", source_id="src_002")

    results = reextract_claims_all(store, apply=False, classify_fn=fake_classify)

    assert {r.slug for r in results} == {"azura-a", "azura-b"}
    assert all(r.new_count == 2 and r.applied is False for r in results)
    assert store.read_all_claims() == []  # dry-run wrote nothing


def test_apply_creates_missing_concept_and_links_claim(tmp_path):
    """Regression guard: concept-claims must link to a real concept node, not a dangling slug."""
    store = WikiStore(root=tmp_path)
    _seed_source_with_raw(store)  # src_001 / azura-src, no concepts in graph yet

    def classify(_text):
        return SourceClassification(
            title="t", description="d", tags=["t"], questions=["q?"], key_takeaways=["k"],
            entity_mentions=[],
            concept_mentions=[ConceptMention(
                name="Boho style", definition="A free-spirited interior style.",
                span=Span(start=0, end=4, text="Boho"))],
            claims=[ClaimExtraction(
                text="Boho style uses natural materials.", subject_name="Boho style",
                subject_type="concept", span=Span(start=0, end=10, text="Boho style"),
                confidence=0.9, polarity="asserts")],
        )

    result = reextract_claims_for_source("azura-src", store, apply=True, classify_fn=classify)

    assert result.applied is True
    assert store.concept_exists("boho-style")  # missing concept was created
    concept = store.read_concept("boho-style")
    claims = [c for c in store.read_all_claims() if c.source_id == "src_001"]
    assert len(claims) == 1
    assert claims[0].subject_id == f"concept:{concept.id}"  # linked to real node, not slug


def test_missing_raw_text_is_skipped(tmp_path, fake_classify):
    store = WikiStore(root=tmp_path)
    src = Source(id="src_001", title="No raw", type="txt", raw_path="raw/missing/parsed.md",
                 ingested_at=datetime(2026, 5, 1), source_url=None,
                 summary="S", key_takeaways=[], questions=[], tags=[])
    store.write_source(src, slug="no-raw")

    result = reextract_claims_for_source("no-raw", store, apply=True, classify_fn=fake_classify)

    assert result.skipped_reason is not None
    assert result.applied is False
    assert store.read_all_claims() == []
