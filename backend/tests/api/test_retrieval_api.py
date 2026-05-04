import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from models.retrieval_models import (
    ParsedIntent, Selection, Answer, QueryTrace, StageTrace,
)

FIXED_INTENT = ParsedIntent(
    original_question="What colors?",
    entity_mentions=[], concept_mentions=[],
    intent_type="fact_lookup", expected_answer_form="short",
)

FIXED_ANSWER = Answer(
    final_answer="Neutral colors.",
    sources=[], confidence=0.8,
    reasoning_steps=["Found context."],
    related_questions=["What materials?"],
)

FIXED_TRACE = QueryTrace(
    query_id="q_test01",
    question="What colors?",
    intent=FIXED_INTENT,
    candidates_count=3,
    selected_count=1,
    context_chars=500,
    answer=FIXED_ANSWER,
    stages=[
        StageTrace(
            stage=i, name=name,
            duration_ms=50.0, llm_called=(i in {1, 3, 5}),
            input_summary="...", output_summary="...",
        )
        for i, name in enumerate(
            ["Intent Parser", "Candidate Filter", "Selection", "Context Assembly", "Answer Generator"],
            start=1,
        )
    ],
    total_duration_ms=300.0,
    total_llm_calls=3,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_query_returns_200(client):
    with patch("api.retrieval.run_retrieval", return_value=FIXED_TRACE):
        response = client.post("/api/retrieval/query", json={"question": "What colors?"})
    assert response.status_code == 200


def test_query_response_shape(client):
    with patch("api.retrieval.run_retrieval", return_value=FIXED_TRACE):
        response = client.post("/api/retrieval/query", json={"question": "What colors?"})
    data = response.json()
    assert "query_id" in data
    assert "question" in data
    assert "answer" in data
    assert "stages" in data
    assert "total_llm_calls" in data


def test_query_response_has_five_stages(client):
    with patch("api.retrieval.run_retrieval", return_value=FIXED_TRACE):
        response = client.post("/api/retrieval/query", json={"question": "What colors?"})
    assert len(response.json()["stages"]) == 5


def test_query_empty_question_returns_400(client):
    response = client.post("/api/retrieval/query", json={"question": "   "})
    assert response.status_code == 400


def test_query_missing_question_returns_422(client):
    response = client.post("/api/retrieval/query", json={})
    assert response.status_code == 422


def test_query_calls_run_retrieval_once(client):
    with patch("api.retrieval.run_retrieval", return_value=FIXED_TRACE) as mock_run:
        client.post("/api/retrieval/query", json={"question": "What colors?"})
    mock_run.assert_called_once()
