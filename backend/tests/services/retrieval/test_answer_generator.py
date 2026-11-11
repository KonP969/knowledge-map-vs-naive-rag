import pytest
from unittest.mock import MagicMock, patch
from models.retrieval_models import Answer, AnswerSource
from services.retrieval.answer_generator import AnswerWithUsage
import services.retrieval.answer_generator as _module


@pytest.fixture(autouse=True)
def reset_client():
    _module._client = None
    yield
    _module._client = None


FIXED_ANSWER = Answer(
    final_answer="Scandinavian bedrooms use neutral colors: white, beige, and gray.",
    sources=[AnswerSource(source_id="src_001", claim_ids=["cl_001"], relevance="primary")],
    confidence=0.9,
    reasoning_steps=["Found source src_001", "Claim cl_001 directly answers question"],
    related_questions=["What materials are used?"],
)


def _make_mock_response(answer: Answer, prompt_tokens: int = 120, completion_tokens: int = 40):
    mock_msg = MagicMock()
    mock_msg.parsed = answer
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = prompt_tokens
    mock_response.usage.completion_tokens = completion_tokens
    return mock_response


def test_generate_answer_returns_answer():
    from services.retrieval.answer_generator import generate_answer
    mock_response = _make_mock_response(FIXED_ANSWER)
    with patch("services.retrieval.answer_generator._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        result = generate_answer("What colors?", "# Context\n\nSome context.")
    assert isinstance(result, AnswerWithUsage)
    assert isinstance(result.answer, Answer)
    assert result.answer.confidence == 0.9
    assert result.prompt_tokens == 120
    assert result.completion_tokens == 40
    assert result.llm_ms >= 0


def test_generate_answer_passes_question_and_context():
    from services.retrieval.answer_generator import generate_answer
    mock_response = _make_mock_response(FIXED_ANSWER)
    with patch("services.retrieval.answer_generator._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        generate_answer("SENTINEL_Q", "SENTINEL_CONTEXT")
        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        messages = call_kwargs.kwargs.get("messages", [])
        all_content = " ".join(m["content"] for m in messages if isinstance(m.get("content"), str))
        assert "SENTINEL_Q" in all_content
        assert "SENTINEL_CONTEXT" in all_content


def test_generate_answer_uses_answer_response_format():
    from services.retrieval.answer_generator import generate_answer
    mock_response = _make_mock_response(FIXED_ANSWER)
    with patch("services.retrieval.answer_generator._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        generate_answer("Q", "context")
        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        assert call_kwargs.kwargs.get("response_format") is Answer


def test_generate_answer_raises_on_none_response():
    from services.retrieval.answer_generator import generate_answer
    mock_msg = MagicMock()
    mock_msg.parsed = None
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    with patch("services.retrieval.answer_generator._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        with pytest.raises(ValueError, match="no structured output"):
            generate_answer("Q", "context")


def test_generate_answer_sources_present():
    from services.retrieval.answer_generator import generate_answer
    mock_response = _make_mock_response(FIXED_ANSWER)
    with patch("services.retrieval.answer_generator._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        result = generate_answer("Q", "context")
    assert len(result.answer.sources) == 1
    assert result.answer.sources[0].source_id == "src_001"


def test_generate_answer_uses_temperature_zero():
    from services.retrieval.answer_generator import generate_answer
    mock_response = _make_mock_response(FIXED_ANSWER)
    with patch("services.retrieval.answer_generator._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        generate_answer("Q", "context")
        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        assert call_kwargs.kwargs.get("temperature") == 0


def test_system_prompt_requires_surfacing_contradictions():
    from services.retrieval.answer_generator import _SYSTEM_PROMPT
    prompt = _SYSTEM_PROMPT.lower()
    assert "contradict" in prompt and "both" in prompt
