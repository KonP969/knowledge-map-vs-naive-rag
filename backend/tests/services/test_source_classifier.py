import pytest
from unittest.mock import MagicMock, patch
from models.ingest_models import (
    SourceClassification, EntityMention, ConceptMention, ClaimExtraction
)
from models.wiki_models import Span
import services.source_classifier as _sc_module


@pytest.fixture(autouse=True)
def reset_openai_client():
    """Reset the module-level _client singleton before and after each test."""
    _sc_module._client = None
    yield
    _sc_module._client = None


# ── shared fixture ────────────────────────────────────────────────────────────

FIXED_CLASSIFICATION = SourceClassification(
    title="Scandinavian Bedroom",
    description="Article about Scandinavian bedroom design principles.",
    tags=["bedroom", "scandinavian", "design"],
    questions=["What colors are typical?", "What materials are used?"],
    key_takeaways=["Neutral palette is central.", "Wood dominates."],
    entity_mentions=[
        EntityMention(
            name="Sypialnia",
            type="Place",
            aliases=["bedroom"],
            description="A bedroom in Scandinavian style.",
            span=Span(start=0, end=8, text="Sypialnia"),
        )
    ],
    concept_mentions=[
        ConceptMention(
            name="neutral palette",
            definition="Color scheme using whites, beiges, and grays.",
            span=Span(start=20, end=35, text="neutral palette"),
        )
    ],
    claims=[
        ClaimExtraction(
            text="Scandinavian bedrooms use neutral colors.",
            subject_name="Sypialnia",
            subject_type="entity",
            span=Span(start=0, end=40, text="Scandinavian bedrooms use neutral colors."),
            confidence=0.95,
            polarity="asserts",
        )
    ],
)


def _make_mock_response(classification: SourceClassification):
    """Build a mock object that mimics openai structured output response."""
    mock_msg = MagicMock()
    mock_msg.parsed = classification
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


# ── tests ─────────────────────────────────────────────────────────────────────

def test_classify_source_returns_source_classification():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = classify_source("Some article text about Scandinavian bedroom design.")

    assert isinstance(result, SourceClassification)
    assert result.title == "Scandinavian Bedroom"


def test_classify_source_passes_text_to_llm():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        classify_source("TEXT_SENTINEL_VALUE")

        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        # The text must appear somewhere in the messages
        messages = call_kwargs.kwargs.get("messages", [])
        all_content = " ".join(
            m["content"] for m in messages if isinstance(m.get("content"), str)
        )
        assert "TEXT_SENTINEL_VALUE" in all_content


def test_classify_source_uses_source_classification_response_format():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        classify_source("some text")

        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        response_format = call_kwargs.kwargs.get("response_format")
        assert response_format is SourceClassification


def test_classify_source_entity_mentions_present():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = classify_source("some text")

    assert len(result.entity_mentions) == 1
    assert result.entity_mentions[0].name == "Sypialnia"


def test_classify_source_concept_mentions_present():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = classify_source("some text")

    assert len(result.concept_mentions) == 1
    assert result.concept_mentions[0].name == "neutral palette"


def test_classify_source_claims_present():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = classify_source("some text")

    assert len(result.claims) == 1
    assert result.claims[0].polarity == "asserts"
