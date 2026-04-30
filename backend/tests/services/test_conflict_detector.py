import pytest
from unittest.mock import MagicMock, patch
from models.wiki_models import Claim, Span
from models.ingest_models import ConflictReport

import services.conflict_detector as _cd_module

@pytest.fixture(autouse=True)
def reset_openai_client():
    _cd_module._client = None
    yield
    _cd_module._client = None


def _make_claim(id, text, subject_id, polarity, source_id="src_001"):
    return Claim(
        id=id, text=text, subject_id=subject_id,
        source_id=source_id,
        span=Span(start=0, end=len(text), text=text[:20]),
        confidence=0.9, polarity=polarity,
    )


def test_no_conflicts_when_no_denying_claims():
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "Bedroom uses wood.", "entity:e_001", "asserts")]
    existing_claims = [_make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000")]
    result = detect_conflicts(new_claims, existing_claims)
    assert result == []


def test_no_conflicts_when_no_matching_subject():
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "Bathroom avoids wood.", "entity:e_002", "denies")]
    existing_claims = [_make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000")]
    result = detect_conflicts(new_claims, existing_claims)
    assert result == []


def test_skips_llm_when_no_potential_conflicts():
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "Bedroom uses white.", "entity:e_001", "asserts")]
    existing_claims = [_make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000")]
    with patch("services.conflict_detector._get_client") as mock_get_client:
        result = detect_conflicts(new_claims, existing_claims)
        mock_get_client.assert_not_called()
    assert result == []


def test_calls_llm_when_denies_claim_matches_subject():
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "Bedroom does not use wood.", "entity:e_001", "denies")]
    existing_claims = [_make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000")]

    mock_conflict = ConflictReport(
        new_claim_id="cl_002",
        existing_claim_id="cl_001",
        description="Direct contradiction on wood usage.",
    )

    class _FakeConflictList:
        conflicts: list = [mock_conflict]

    mock_msg = MagicMock()
    mock_msg.parsed = _FakeConflictList()
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("services.conflict_detector._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        result = detect_conflicts(new_claims, existing_claims)

    assert len(result) == 1
    assert result[0].new_claim_id == "cl_002"
    assert result[0].existing_claim_id == "cl_001"


def test_returns_empty_list_when_llm_finds_no_conflict():
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "Bedroom does not use plastic.", "entity:e_001", "denies")]
    existing_claims = [_make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000")]

    class _FakeConflictList:
        conflicts: list = []

    mock_msg = MagicMock()
    mock_msg.parsed = _FakeConflictList()
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("services.conflict_detector._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        result = detect_conflicts(new_claims, existing_claims)

    assert result == []
