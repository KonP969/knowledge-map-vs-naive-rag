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


def _verdict(pair, same_thing=True, same_property=True, incompatible=True, why="differs"):
    from services.conflict_detector import PairVerdict
    return PairVerdict(pair=pair, same_thing=same_thing, same_property=same_property,
                       incompatible=incompatible, description=why)


def _fake_llm(verdicts):
    class _FakeVerdicts:
        pass
    parsed = _FakeVerdicts()
    parsed.verdicts = verdicts
    msg = MagicMock(); msg.parsed = parsed
    choice = MagicMock(); choice.message = msg
    resp = MagicMock(); resp.choices = [choice]
    client = MagicMock()
    client.beta.chat.completions.parse.return_value = resp
    return client


def test_no_llm_when_claims_share_no_subject_and_no_neighbors():
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "Bathroom avoids wood.", "entity:e_002", "denies")]
    existing_claims = [_make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000")]
    with patch("services.conflict_detector._get_client") as mock_get_client:
        assert detect_conflicts(new_claims, existing_claims) == []
        mock_get_client.assert_not_called()


def test_no_llm_for_claims_from_the_same_source():
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "Door is 70 cm.", "entity:e_001", "asserts", "src_001")]
    existing_claims = [_make_claim("cl_001", "Door is 80 cm.", "entity:e_001", "asserts", "src_001")]
    with patch("services.conflict_detector._get_client") as mock_get_client:
        assert detect_conflicts(new_claims, existing_claims) == []
        mock_get_client.assert_not_called()


def test_two_asserting_claims_on_one_subject_are_checked():
    # "80 cm" vs "70 cm" are both 'asserts' - the old rule (denies vs asserts only) missed it.
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "Bathroom door min width is 70 cm.", "entity:e_001", "asserts", "src_002")]
    existing_claims = [_make_claim("cl_001", "Bathroom door min width is 80 cm.", "entity:e_001", "asserts", "src_001")]
    with patch("services.conflict_detector._get_client", return_value=_fake_llm([_verdict(1, why="70 vs 80 cm")])) as g:
        result = detect_conflicts(new_claims, existing_claims)
        prompt = g.return_value.beta.chat.completions.parse.call_args.kwargs["messages"][0]["content"]
    assert [(r.new_claim_id, r.existing_claim_id) for r in result] == [("cl_002", "cl_001")]
    assert "cl_001" in prompt and "cl_002" in prompt


def test_semantic_neighbors_are_checked_even_with_different_subjects():
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "Colour of 2026 is Mocha Mousse.", "concept:c_009", "asserts", "src_002")]
    existing_claims = [_make_claim("cl_001", "Colour of 2026 is Cloud Dancer.", "entity:e_004", "asserts", "src_001")]
    with patch("services.conflict_detector._get_client", return_value=_fake_llm([])) as g:
        detect_conflicts(new_claims, existing_claims, neighbors={"cl_002": ["cl_001"]})
        g.assert_called_once()


def test_verdicts_for_unknown_pair_numbers_are_dropped():
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "A is 70.", "entity:e_001", "asserts", "src_002")]
    existing_claims = [_make_claim("cl_001", "A is 80.", "entity:e_001", "asserts", "src_001")]
    with patch("services.conflict_detector._get_client",
               return_value=_fake_llm([_verdict(7), _verdict(1)])):
        result = detect_conflicts(new_claims, existing_claims)
    assert [(r.new_claim_id, r.existing_claim_id) for r in result] == [("cl_002", "cl_001")]


def test_only_pairs_meeting_all_three_conditions_are_conflicts():
    # "different advice about the same style" is not a contradiction: same thing,
    # but not the same property / not incompatible.
    from services.conflict_detector import detect_conflicts
    new_claims = [
        _make_claim("cl_002", "Boho comes from 19th-century Paris.", "concept:c_001", "asserts", "src_002"),
        _make_claim("cl_003", "Door min width is 70 cm.", "entity:e_001", "asserts", "src_002"),
    ]
    existing_claims = [
        _make_claim("cl_001", "Boho is a mix of cultures.", "concept:c_001", "asserts", "src_001"),
        _make_claim("cl_004", "Door min width is 80 cm.", "entity:e_001", "asserts", "src_001"),
    ]
    verdicts = [_verdict(1, same_property=False, incompatible=False), _verdict(2)]
    with patch("services.conflict_detector._get_client", return_value=_fake_llm(verdicts)):
        result = detect_conflicts(new_claims, existing_claims)
    assert [(r.new_claim_id, r.existing_claim_id) for r in result] == [("cl_003", "cl_004")]


def test_returns_empty_list_when_llm_finds_no_conflict():
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "Bedroom does not use plastic.", "entity:e_001", "denies")]
    existing_claims = [_make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000")]
    with patch("services.conflict_detector._get_client",
               return_value=_fake_llm([_verdict(1, incompatible=False)])):
        assert detect_conflicts(new_claims, existing_claims) == []


def test_conflict_verdicts_are_deterministic():
    from services.conflict_detector import detect_conflicts
    new_claims = [_make_claim("cl_002", "A is 70.", "entity:e_001", "asserts", "src_002")]
    existing_claims = [_make_claim("cl_001", "A is 80.", "entity:e_001", "asserts", "src_001")]
    with patch("services.conflict_detector._get_client", return_value=_fake_llm([])) as g:
        detect_conflicts(new_claims, existing_claims)
        assert g.return_value.beta.chat.completions.parse.call_args.kwargs.get("temperature") == 0
