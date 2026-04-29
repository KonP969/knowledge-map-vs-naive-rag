import pytest
from pydantic import ValidationError
from models.ingest_models import (
    EntityMention, ConceptMention, ClaimExtraction,
    SourceClassification, ConflictReport, IngestResult,
)
from models.wiki_models import Span


def test_entity_mention_valid():
    em = EntityMention(
        name="IKEA",
        type="Org",
        aliases=["IKEA Group"],
        description="Swedish furniture retailer.",
        span=Span(start=0, end=4, text="IKEA"),
    )
    assert em.name == "IKEA"
    assert em.type == "Org"


def test_entity_mention_invalid_type():
    with pytest.raises(ValidationError):
        EntityMention(
            name="IKEA",
            type="Company",  # not in EntityType
            aliases=[],
            description="x",
            span=Span(start=0, end=4, text="IKEA"),
        )


def test_concept_mention_valid():
    cm = ConceptMention(
        name="neutral palette",
        definition="A color scheme using whites, beiges, and grays.",
        span=Span(start=10, end=24, text="neutral palette"),
    )
    assert cm.name == "neutral palette"


def test_claim_extraction_valid_polarity():
    ce = ClaimExtraction(
        text="IKEA uses sustainable materials.",
        subject_name="IKEA",
        subject_type="entity",
        span=Span(start=0, end=31, text="IKEA uses sustainable materials."),
        confidence=0.9,
        polarity="asserts",
    )
    assert ce.subject_type == "entity"


def test_claim_extraction_invalid_subject_type():
    with pytest.raises(ValidationError):
        ClaimExtraction(
            text="X",
            subject_name="X",
            subject_type="relation",  # invalid
            span=Span(start=0, end=1, text="X"),
            confidence=0.5,
            polarity="asserts",
        )


def test_claim_extraction_confidence_out_of_range():
    with pytest.raises(ValidationError):
        ClaimExtraction(
            text="X",
            subject_name="X",
            subject_type="entity",
            span=Span(start=0, end=1, text="X"),
            confidence=1.5,  # out of range
            polarity="asserts",
        )


def test_source_classification_valid():
    sc = SourceClassification(
        title="Scandinavian Bedroom",
        description="Article about Scandinavian bedroom design.",
        tags=["bedroom", "scandinavian"],
        questions=["What colors are typical?"],
        key_takeaways=["Minimalism is key."],
        entity_mentions=[],
        concept_mentions=[],
        claims=[],
    )
    assert sc.title == "Scandinavian Bedroom"


def test_conflict_report_valid():
    cr = ConflictReport(
        new_claim_id="cl_002",
        existing_claim_id="cl_001",
        description="Claim contradicts an existing assertion.",
    )
    assert cr.new_claim_id == "cl_002"


def test_ingest_result_status_enum():
    with pytest.raises(ValidationError):
        IngestResult(
            source_id="src_001",
            slug="test-source",
            status="unknown",  # invalid
            entities_created=0, entities_merged=0,
            concepts_created=0, concepts_merged=0,
            claims_added=0, edges_added=0,
            conflicts=[], duration_ms=100.0, llm_calls=1,
        )


def test_ingest_result_ok():
    result = IngestResult(
        source_id="src_001",
        slug="test-source",
        status="ok",
        entities_created=2, entities_merged=0,
        concepts_created=1, concepts_merged=0,
        claims_added=3, edges_added=3,
        conflicts=[], duration_ms=1234.5, llm_calls=1,
    )
    assert result.status == "ok"
    assert result.error is None
