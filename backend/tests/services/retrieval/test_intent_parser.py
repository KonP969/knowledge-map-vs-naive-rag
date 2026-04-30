import pytest
from unittest.mock import MagicMock, patch
from models.retrieval_models import ParsedIntent
import services.retrieval.intent_parser as _module


@pytest.fixture(autouse=True)
def reset_client():
    _module._client = None
    yield
    _module._client = None


FIXED_INTENT = ParsedIntent(
    original_question="What colors are used in Scandinavian bedrooms?",
    entity_mentions=["Sypialnia"],
    concept_mentions=["neutral palette"],
    intent_type="fact_lookup",
    expected_answer_form="short",
)


def _make_mock_response(intent: ParsedIntent):
    mock_msg = MagicMock()
    mock_msg.parsed = intent
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def test_parse_intent_returns_parsed_intent():
    from services.retrieval.intent_parser import parse_intent
    mock_response = _make_mock_response(FIXED_INTENT)
    with patch("services.retrieval.intent_parser._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        result = parse_intent("What colors are used in Scandinavian bedrooms?")
    assert isinstance(result, ParsedIntent)
    assert result.intent_type == "fact_lookup"


def test_parse_intent_passes_question_to_llm():
    from services.retrieval.intent_parser import parse_intent
    mock_response = _make_mock_response(FIXED_INTENT)
    with patch("services.retrieval.intent_parser._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        parse_intent("SENTINEL_QUESTION_42")
        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        messages = call_kwargs.kwargs.get("messages", [])
        all_content = " ".join(m["content"] for m in messages if isinstance(m.get("content"), str))
        assert "SENTINEL_QUESTION_42" in all_content


def test_parse_intent_uses_parsed_intent_response_format():
    from services.retrieval.intent_parser import parse_intent
    mock_response = _make_mock_response(FIXED_INTENT)
    with patch("services.retrieval.intent_parser._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        parse_intent("some question")
        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        response_format = call_kwargs.kwargs.get("response_format")
        assert response_format is ParsedIntent


def test_parse_intent_raises_on_none_response():
    from services.retrieval.intent_parser import parse_intent
    mock_msg = MagicMock()
    mock_msg.parsed = None
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    with patch("services.retrieval.intent_parser._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        with pytest.raises(ValueError, match="no structured output"):
            parse_intent("question")


def test_parse_intent_entity_mentions_extracted():
    from services.retrieval.intent_parser import parse_intent
    mock_response = _make_mock_response(FIXED_INTENT)
    with patch("services.retrieval.intent_parser._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        result = parse_intent("any question")
    assert "Sypialnia" in result.entity_mentions
