import pytest
from pydantic import ValidationError
from models.retrieval_models import (
    TimePeriod, ParsedIntent, Candidate, SelectedArtifact,
    Selection, AnswerSource, Answer, StageTrace, QueryTrace,
    AgentToolCall, AgentTrace,
)


def test_parsed_intent_valid():
    pi = ParsedIntent(
        original_question="What colors are used in Scandinavian bedrooms?",
        entity_mentions=["Sypialnia"],
        concept_mentions=["neutral palette"],
        intent_type="fact_lookup",
        expected_answer_form="short",
    )
    assert pi.intent_type == "fact_lookup"
    assert pi.time_period is None


def test_parsed_intent_invalid_intent_type():
    with pytest.raises(ValidationError):
        ParsedIntent(
            original_question="Q",
            entity_mentions=[],
            concept_mentions=[],
            intent_type="unknown_type",
            expected_answer_form="short",
        )


def test_parsed_intent_invalid_answer_form():
    with pytest.raises(ValidationError):
        ParsedIntent(
            original_question="Q",
            entity_mentions=[],
            concept_mentions=[],
            intent_type="fact_lookup",
            expected_answer_form="essay",
        )


def test_candidate_valid():
    c = Candidate(
        artifact_id="source:src_001",
        artifact_type="source",
        slug="scandinavian-bedroom",
        title="Scandinavian Bedroom",
        score=7,
        score_breakdown={"entity_match": 3, "concept_match": 2, "question_overlap": 2},
        questions=["What colors?"],
        tags=["bedroom"],
        description_preview="Article about Scandinavian design.",
    )
    assert c.score == 7
    assert c.artifact_type == "source"


def test_candidate_invalid_type():
    with pytest.raises(ValidationError):
        Candidate(
            artifact_id="x:001",
            artifact_type="claim",  # invalid
            slug="x",
            title="X",
            score=1,
            score_breakdown={},
            questions=[],
            tags=[],
            description_preview="",
        )


def test_selected_artifact_relevance_range():
    with pytest.raises(ValidationError):
        SelectedArtifact(
            artifact_id="source:src_001",
            relevance_score=1.5,
            reasoning="very relevant",
        )


def test_selection_valid():
    s = Selection(
        selected=[
            SelectedArtifact(
                artifact_id="source:src_001",
                relevance_score=0.9,
                reasoning="directly answers the question",
            )
        ],
        confidence=0.85,
        reasoning="Strong match.",
    )
    assert len(s.selected) == 1
    assert s.confidence == 0.85


def test_answer_confidence_range():
    with pytest.raises(ValidationError):
        Answer(
            final_answer="X",
            sources=[],
            confidence=1.5,
            reasoning_steps=[],
            related_questions=[],
        )


def test_answer_valid():
    a = Answer(
        final_answer="Scandinavian bedrooms use neutral colors.",
        sources=[
            AnswerSource(
                source_id="src_001",
                claim_ids=["cl_001"],
                relevance="primary source",
            )
        ],
        confidence=0.9,
        reasoning_steps=["Found source", "Extracted claim"],
        related_questions=["What materials are used?"],
    )
    assert a.confidence == 0.9
    assert len(a.sources) == 1


def test_stage_trace_valid():
    st = StageTrace(
        stage=1, name="Intent Parser",
        duration_ms=123.4, llm_called=True,
        input_summary="question: ...", output_summary="intent_type=fact_lookup",
    )
    assert st.stage == 1


def test_query_trace_valid():
    intent = ParsedIntent(
        original_question="Q", entity_mentions=[], concept_mentions=[],
        intent_type="fact_lookup", expected_answer_form="short",
    )
    answer = Answer(
        final_answer="A", sources=[], confidence=0.8,
        reasoning_steps=[], related_questions=[],
    )
    qt = QueryTrace(
        query_id="q_001", question="Q", intent=intent,
        candidates_count=5, selected_count=2, context_chars=1000,
        answer=answer, stages=[], total_duration_ms=1500.0, total_llm_calls=3,
    )
    assert qt.total_llm_calls == 3


def test_agent_tool_call_fields():
    tc = AgentToolCall(
        tool_name="search_entities",
        args={"q": "bedroom"},
        result_summary='[{"slug": "sypialnia"}]',
        duration_ms=12.5,
    )
    assert tc.tool_name == "search_entities"
    assert tc.args == {"q": "bedroom"}
    assert tc.duration_ms == 12.5


def test_agent_trace_not_triggered():
    at = AgentTrace(
        triggered=False,
        trigger_reason="",
        tool_calls=[],
        final_answer=None,
        duration_ms=0.0,
    )
    assert at.triggered is False
    assert at.tool_calls == []
    assert at.final_answer is None


def test_agent_trace_with_tool_calls():
    tc = AgentToolCall(
        tool_name="read_index",
        args={},
        result_summary="{}",
        duration_ms=5.0,
    )
    at = AgentTrace(
        triggered=True,
        trigger_reason="Stage 2 returned 0 candidates",
        tool_calls=[tc],
        final_answer=None,
        duration_ms=120.0,
    )
    assert len(at.tool_calls) == 1
    assert at.trigger_reason == "Stage 2 returned 0 candidates"


def test_query_trace_agent_trace_defaults_none():
    intent = ParsedIntent(
        original_question="q",
        entity_mentions=[],
        concept_mentions=[],
        intent_type="fact_lookup",
        expected_answer_form="short",
    )
    answer = Answer(
        final_answer="ans",
        sources=[],
        confidence=0.9,
        reasoning_steps=[],
        related_questions=[],
    )
    qt = QueryTrace(
        query_id="q_abc",
        question="q",
        intent=intent,
        candidates_count=1,
        selected_count=1,
        context_chars=100,
        answer=answer,
        stages=[],
        total_duration_ms=50.0,
        total_llm_calls=3,
    )
    assert qt.agent_trace is None


def test_agent_tool_call_negative_duration_rejected():
    with pytest.raises(ValidationError):
        AgentToolCall(
            tool_name="read_index",
            args={},
            result_summary="{}",
            duration_ms=-1.0,
        )


def test_agent_trace_negative_duration_rejected():
    with pytest.raises(ValidationError):
        AgentTrace(
            triggered=False,
            trigger_reason="",
            tool_calls=[],
            final_answer=None,
            duration_ms=-5.0,
        )
