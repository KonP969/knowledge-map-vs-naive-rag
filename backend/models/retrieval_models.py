from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class TimePeriod(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None


class ParsedIntent(BaseModel):
    original_question: str
    entity_mentions: List[str]
    concept_mentions: List[str]
    time_period: Optional[TimePeriod] = None
    intent_type: Literal[
        "fact_lookup", "comparison", "synthesis",
        "definition", "how_to", "temporal_trend",
    ]
    expected_answer_form: Literal["short", "list", "table", "analysis", "citation"]


class Candidate(BaseModel):
    artifact_id: str
    artifact_type: Literal["source", "entity", "concept"]
    slug: str
    title: str
    score: int
    score_breakdown: Dict[str, int]
    questions: List[str]
    tags: List[str]
    description_preview: str


class SelectedArtifact(BaseModel):
    artifact_id: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str


class Selection(BaseModel):
    selected: List[SelectedArtifact]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str


class AnswerSource(BaseModel):
    source_id: str
    claim_ids: List[str] = Field(default_factory=list)
    relevance: str


class Answer(BaseModel):
    final_answer: str
    sources: List[AnswerSource]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning_steps: List[str]
    related_questions: List[str]


class AgentToolCall(BaseModel):
    tool_name: str
    args: dict
    result_summary: str
    duration_ms: float


class AgentTrace(BaseModel):
    triggered: bool
    trigger_reason: str
    tool_calls: List[AgentToolCall]
    final_answer: Optional[Answer] = None
    duration_ms: float


class StageTrace(BaseModel):
    stage: int
    name: str
    duration_ms: float
    llm_called: bool
    input_summary: str
    output_summary: str


class QueryTrace(BaseModel):
    query_id: str
    question: str
    intent: ParsedIntent
    candidates_count: int
    selected_count: int
    context_chars: int
    answer: Answer
    stages: List[StageTrace]
    total_duration_ms: float
    total_llm_calls: int
    agent_trace: Optional[AgentTrace] = None
