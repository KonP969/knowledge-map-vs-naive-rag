import pytest
from unittest.mock import MagicMock, patch
from models.retrieval_models import Candidate, Selection, SelectedArtifact
import services.retrieval.selection as _module


@pytest.fixture(autouse=True)
def reset_client():
    _module._client = None
    yield
    _module._client = None


FIXED_SELECTION = Selection(
    selected=[
        SelectedArtifact(
            artifact_id="source:src_001",
            relevance_score=0.9,
            reasoning="directly answers the question",
        )
    ],
    confidence=0.85,
    reasoning="Best match found.",
)

SAMPLE_CANDIDATES = [
    Candidate(
        artifact_id="source:src_001",
        artifact_type="source",
        slug="scandinavian-bedroom",
        title="Scandinavian Bedroom",
        score=7,
        score_breakdown={"entity_match": 3, "question_overlap": 2, "tag_match": 2},
        questions=["What colors are typical?"],
        tags=["bedroom"],
        description_preview="Article about Scandinavian design.",
    )
]


def _make_mock_response(selection: Selection):
    mock_msg = MagicMock()
    mock_msg.parsed = selection
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def test_select_candidates_returns_selection():
    from services.retrieval.selection import select_candidates
    mock_response = _make_mock_response(FIXED_SELECTION)
    with patch("services.retrieval.selection._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        result = select_candidates("What colors?", SAMPLE_CANDIDATES)
    assert isinstance(result, Selection)
    assert result.confidence == 0.85


def test_select_candidates_passes_question_to_llm():
    from services.retrieval.selection import select_candidates
    mock_response = _make_mock_response(FIXED_SELECTION)
    with patch("services.retrieval.selection._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        select_candidates("SENTINEL_QUESTION_99", SAMPLE_CANDIDATES)
        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        messages = call_kwargs.kwargs.get("messages", [])
        all_content = " ".join(m["content"] for m in messages if isinstance(m.get("content"), str))
        assert "SENTINEL_QUESTION_99" in all_content


def test_select_candidates_uses_selection_response_format():
    from services.retrieval.selection import select_candidates
    mock_response = _make_mock_response(FIXED_SELECTION)
    with patch("services.retrieval.selection._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        select_candidates("Q", SAMPLE_CANDIDATES)
        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        assert call_kwargs.kwargs.get("response_format") is Selection


def test_select_candidates_raises_on_none_response():
    from services.retrieval.selection import select_candidates
    mock_msg = MagicMock()
    mock_msg.parsed = None
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    with patch("services.retrieval.selection._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        with pytest.raises(ValueError, match="no structured output"):
            select_candidates("Q", SAMPLE_CANDIDATES)


def test_select_candidates_includes_artifact_ids_in_prompt():
    from services.retrieval.selection import select_candidates
    mock_response = _make_mock_response(FIXED_SELECTION)
    with patch("services.retrieval.selection._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        select_candidates("Q", SAMPLE_CANDIDATES)
        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        messages = call_kwargs.kwargs.get("messages", [])
        all_content = " ".join(m["content"] for m in messages if isinstance(m.get("content"), str))
        assert "source:src_001" in all_content


def test_select_candidates_uses_temperature_zero():
    from services.retrieval.selection import select_candidates
    mock_response = _make_mock_response(FIXED_SELECTION)
    with patch("services.retrieval.selection._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        select_candidates("Q", SAMPLE_CANDIDATES)
        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        assert call_kwargs.kwargs.get("temperature") == 0
