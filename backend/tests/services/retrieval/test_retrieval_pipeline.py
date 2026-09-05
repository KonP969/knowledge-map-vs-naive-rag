import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from models.wiki_models import Source, Entity, Concept, Claim, Edge, Span
from models.retrieval_models import (
    ParsedIntent, Selection, SelectedArtifact, Answer, AnswerSource, QueryTrace,
    AgentTrace, AgentToolCall,
)
from services.retrieval.answer_generator import AnswerWithUsage


@pytest.fixture
def store(tmp_path):
    s = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="Scandinavian Bedroom", type="txt",
        raw_path="raw/x/parsed.md", ingested_at=datetime(2026, 4, 1),
        summary="Article about Scandinavian bedroom design.",
        key_takeaways=["Neutral palette."],
        questions=["What colors are typical in Scandinavian bedrooms?"],
        tags=["bedroom", "scandinavian"],
    )
    s.write_source(src, slug="scandinavian-bedroom")
    entity = Entity(
        id="e_001", type="Place", aliases=["bedroom"],
        description="A Scandinavian bedroom.", mentions_count=1,
        questions=["What materials are used?"], tags=["bedroom"],
    )
    s.write_entity(entity, slug="sypialnia")
    concept = Concept(
        id="c_001", definition="Whites, beiges, grays.",
        examples=["white walls"], related=[],
        questions=["What is a neutral palette?"], tags=["color"],
    )
    s.write_concept(concept, slug="neutral-palette")
    claim = Claim(
        id="cl_001", text="Bedroom uses neutral colors.",
        subject_id="entity:e_001", source_id="src_001",
        span=Span(start=0, end=30, text="Bedroom uses neutral colors."),
        confidence=0.9, polarity="asserts",
    )
    s.append_claim(claim)
    regenerate_index(s)
    return s


FIXED_INTENT = ParsedIntent(
    original_question="What colors are used in Scandinavian bedrooms?",
    entity_mentions=["sypialnia"],
    concept_mentions=["neutral palette"],
    intent_type="fact_lookup",
    expected_answer_form="short",
)

FIXED_SELECTION = Selection(
    selected=[
        SelectedArtifact(
            artifact_id="source:src_001",
            relevance_score=0.9,
            reasoning="primary source",
        )
    ],
    confidence=0.85,
    reasoning="Best match.",
)

FIXED_ANSWER = Answer(
    final_answer="Scandinavian bedrooms use neutral colors.",
    sources=[AnswerSource(source_id="src_001", claim_ids=["cl_001"], relevance="primary")],
    confidence=0.9,
    reasoning_steps=["Found source", "Extracted claim"],
    related_questions=["What materials are used?"],
)


def _with_usage(answer, prompt_tokens=120, completion_tokens=40, llm_ms=12.5):
    """generate_answer returns AnswerWithUsage, not a bare Answer."""
    return AnswerWithUsage(
        answer=answer,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        llm_ms=llm_ms,
    )


FIXED_ANSWER_RESULT = _with_usage(FIXED_ANSWER)


def run_pipeline(store):
    from services.retrieval.retrieval_pipeline import run_retrieval
    with patch("services.retrieval.retrieval_pipeline.parse_intent", return_value=FIXED_INTENT), \
         patch("services.retrieval.retrieval_pipeline.select_candidates", return_value=FIXED_SELECTION), \
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=FIXED_ANSWER_RESULT):
        return run_retrieval("What colors are used in Scandinavian bedrooms?", store)


def test_pipeline_returns_query_trace(store):
    result = run_pipeline(store)
    assert isinstance(result, QueryTrace)


def test_pipeline_has_five_stages(store):
    result = run_pipeline(store)
    assert len(result.stages) == 5


def test_pipeline_stage_names(store):
    result = run_pipeline(store)
    names = [s.name for s in result.stages]
    assert names == ["Intent Parser", "Candidate Filter", "Selection", "Context Assembly", "Answer Generator"]


def test_pipeline_llm_calls_count(store):
    result = run_pipeline(store)
    # Stages 1, 3, 5 use LLM (all mocked here)
    assert result.total_llm_calls == 3


def test_pipeline_candidates_count_positive(store):
    result = run_pipeline(store)
    # Store has 3 artifacts; at least entity + concept + source match the intent
    assert result.candidates_count >= 1


def test_pipeline_selected_count(store):
    result = run_pipeline(store)
    assert result.selected_count == 1


def test_pipeline_context_chars_positive(store):
    result = run_pipeline(store)
    assert result.context_chars > 0


def test_pipeline_answer_matches_mock(store):
    result = run_pipeline(store)
    assert result.answer.final_answer == FIXED_ANSWER.final_answer


def test_pipeline_duration_ms_positive(store):
    result = run_pipeline(store)
    assert result.total_duration_ms > 0


def test_pipeline_query_id_unique(store):
    r1 = run_pipeline(store)
    r2 = run_pipeline(store)
    assert r1.query_id != r2.query_id


def test_pipeline_stage_2_not_llm(store):
    result = run_pipeline(store)
    stage2 = next(s for s in result.stages if s.stage == 2)
    assert stage2.llm_called is False


def test_pipeline_empty_vault_returns_trace(tmp_path):
    from services.retrieval.retrieval_pipeline import run_retrieval
    empty_store = WikiStore(root=tmp_path)
    with patch("services.retrieval.retrieval_pipeline.parse_intent", return_value=FIXED_INTENT), \
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=FIXED_ANSWER_RESULT), \
         patch("services.retrieval.retrieval_pipeline.run_agent_fallback", return_value=FIXED_AGENT_TRACE):
        result = run_retrieval("Q", empty_store)
    assert isinstance(result, QueryTrace)
    assert result.candidates_count == 0
    assert result.selected_count == 0


FIXED_AGENT_TRACE = AgentTrace(
    triggered=True,
    trigger_reason="Stage 2 returned 0 candidates",
    tool_calls=[
        AgentToolCall(tool_name="read_index", args={}, result_summary="{}", duration_ms=5.0)
    ],
    final_answer=FIXED_ANSWER,
    duration_ms=200.0,
)


def test_pipeline_no_agent_trace_when_confident(store):
    result = run_pipeline(store)
    # FIXED_SELECTION has confidence=0.85, FIXED_ANSWER has confidence=0.9 → no fallback
    assert result.agent_trace is None


def test_pipeline_triggers_fallback_when_no_candidates(tmp_path):
    from services.retrieval.retrieval_pipeline import run_retrieval
    from services.wiki_store import WikiStore
    empty_store = WikiStore(root=tmp_path)
    with patch("services.retrieval.retrieval_pipeline.parse_intent", return_value=FIXED_INTENT), \
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=FIXED_ANSWER_RESULT), \
         patch("services.retrieval.retrieval_pipeline.run_agent_fallback", return_value=FIXED_AGENT_TRACE) as mock_fb:
        result = run_retrieval("Q", empty_store)
    mock_fb.assert_called_once()
    assert result.agent_trace is not None
    assert result.agent_trace.triggered is True


def test_pipeline_triggers_fallback_when_low_selection_confidence(store):
    from services.retrieval.retrieval_pipeline import run_retrieval
    from models.retrieval_models import Selection, SelectedArtifact
    low_conf_selection = Selection(
        selected=[SelectedArtifact(artifact_id="source:src_001", relevance_score=0.4, reasoning="weak")],
        confidence=0.3,
        reasoning="uncertain",
    )
    with patch("services.retrieval.retrieval_pipeline.parse_intent", return_value=FIXED_INTENT), \
         patch("services.retrieval.retrieval_pipeline.select_candidates", return_value=low_conf_selection), \
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=FIXED_ANSWER_RESULT), \
         patch("services.retrieval.retrieval_pipeline.run_agent_fallback", return_value=FIXED_AGENT_TRACE) as mock_fb:
        result = run_retrieval("Q", store)
    mock_fb.assert_called_once()
    call_trigger = mock_fb.call_args.kwargs["trigger_reason"]
    assert "0.3" in call_trigger or "Stage 3" in call_trigger
    assert result.agent_trace is not None


def test_pipeline_triggers_fallback_when_low_answer_confidence(store):
    from services.retrieval.retrieval_pipeline import run_retrieval
    from models.retrieval_models import Answer, AnswerSource
    low_conf_answer = Answer(
        final_answer="I am not sure.",
        sources=[AnswerSource(source_id="src_001", relevance="low")],
        confidence=0.4,
        reasoning_steps=[],
        related_questions=[],
    )
    with patch("services.retrieval.retrieval_pipeline.parse_intent", return_value=FIXED_INTENT), \
         patch("services.retrieval.retrieval_pipeline.select_candidates", return_value=FIXED_SELECTION), \
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=_with_usage(low_conf_answer)), \
         patch("services.retrieval.retrieval_pipeline.run_agent_fallback", return_value=FIXED_AGENT_TRACE) as mock_fb:
        result = run_retrieval("Q", store)
    mock_fb.assert_called_once()
    call_trigger = mock_fb.call_args.kwargs["trigger_reason"]
    assert "0.4" in call_trigger or "Stage 5" in call_trigger
    assert result.agent_trace is not None


def test_pipeline_fallback_trigger_reason_no_candidates(tmp_path):
    from services.retrieval.retrieval_pipeline import run_retrieval
    from services.wiki_store import WikiStore
    empty_store = WikiStore(root=tmp_path)
    with patch("services.retrieval.retrieval_pipeline.parse_intent", return_value=FIXED_INTENT), \
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=FIXED_ANSWER_RESULT), \
         patch("services.retrieval.retrieval_pipeline.run_agent_fallback", return_value=FIXED_AGENT_TRACE) as mock_fb:
        run_retrieval("Q", empty_store)
    trigger_reason = mock_fb.call_args.kwargs["trigger_reason"]
    assert "Stage 2" in trigger_reason or "0 candidates" in trigger_reason


def test_pipeline_fallback_answer_supersedes_weak_answer(store):
    """When the agent fallback produces an answer, QueryTrace.answer must be that one,
    not the weak pipeline answer that triggered the fallback."""
    from services.retrieval.retrieval_pipeline import run_retrieval
    from models.retrieval_models import Answer, AnswerSource
    weak_answer = Answer(
        final_answer="I am not sure.",
        sources=[AnswerSource(source_id="src_001", relevance="low")],
        confidence=0.3,
        reasoning_steps=[],
        related_questions=[],
    )
    strong_fallback = AgentTrace(
        triggered=True,
        trigger_reason="Stage 5 answer confidence too low (0.30 < 0.6)",
        tool_calls=[],
        final_answer=Answer(
            final_answer="The fallback found the real answer.",
            sources=[AnswerSource(source_id="src_001", claim_ids=["cl_001"], relevance="primary")],
            confidence=0.88,
            reasoning_steps=["searched"],
            related_questions=[],
        ),
        duration_ms=150.0,
    )
    with patch("services.retrieval.retrieval_pipeline.parse_intent", return_value=FIXED_INTENT), \
         patch("services.retrieval.retrieval_pipeline.select_candidates", return_value=FIXED_SELECTION), \
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=_with_usage(weak_answer)), \
         patch("services.retrieval.retrieval_pipeline.run_agent_fallback", return_value=strong_fallback):
        result = run_retrieval("Q", store)
    assert result.answer.final_answer == "The fallback found the real answer."
    assert result.answer.confidence == 0.88
