# Phase 3: Retrieval Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the 5-stage retrieval pipeline (Intent Parse → Candidate Filter → Selection → Context Assembly → Answer Generation) with a FastAPI endpoint and two frontend panels (ChatWithTracePanel, KnowledgeMapPanel) that let users query the wiki and observe retrieval results.

**Architecture:** Retrieval is a sequential pipeline orchestrated by `retrieval_pipeline.py`. Stages 2 and 4 are deterministic (no LLM). Stages 1, 3, and 5 call OpenAI via `client.beta.chat.completions.parse()`. The pipeline reads from the existing `WikiStore` (index.json, claims.jsonl, edges.jsonl). The backend exposes `POST /api/retrieval/query`. The frontend adds `ChatWithTracePanel` (split: answer + 5-stage trace) and `KnowledgeMapPanel` (browser table — no graph, that's Phase 5).

**Tech Stack:** Python 3.9+, FastAPI, Pydantic v2, OpenAI SDK 1.51.0 (structured output), pytest + unittest.mock; React 19 + TypeScript + Vite + Tailwind CSS, lucide-react.

**Phase 2 baseline:** 124 tests green on commit `2c1ccb4`, tag `phase-2-complete`.

---

## File Structure (Phase 3)

**Create (backend):**
- `backend/models/retrieval_models.py` — ParsedIntent, Candidate, Selection, Answer, QueryTrace, StageTrace
- `backend/services/retrieval/__init__.py` — empty
- `backend/services/retrieval/intent_parser.py` — Stage 1: LLM structured output → ParsedIntent
- `backend/services/retrieval/candidate_filter.py` — Stage 2: deterministic scoring over index.json
- `backend/services/retrieval/selection.py` — Stage 3: LLM structured output → Selection
- `backend/services/retrieval/context_assembly.py` — Stage 4: deterministic markdown context builder
- `backend/services/retrieval/answer_generator.py` — Stage 5: LLM structured output → Answer
- `backend/services/retrieval/retrieval_pipeline.py` — orchestrates all 5 stages
- `backend/api/retrieval.py` — FastAPI router: POST /api/retrieval/query
- `backend/tests/models/test_retrieval_models.py`
- `backend/tests/services/retrieval/__init__.py` — new
- `backend/tests/services/retrieval/test_intent_parser.py`
- `backend/tests/services/retrieval/test_candidate_filter.py`
- `backend/tests/services/retrieval/test_selection.py`
- `backend/tests/services/retrieval/test_context_assembly.py`
- `backend/tests/services/retrieval/test_answer_generator.py`
- `backend/tests/services/retrieval/test_retrieval_pipeline.py`
- `backend/tests/api/test_retrieval_api.py`

**Create (frontend):**
- `frontend/src/components/chat_with_trace/ChatWithTracePanel.tsx`
- `frontend/src/components/wiki/KnowledgeMapPanel.tsx`

**Modify:**
- `backend/main.py` — include retrieval router
- `frontend/src/types/index.ts` — add retrieval types, extend Panel
- `frontend/src/api/client.ts` — add queryWiki method
- `frontend/src/App.tsx` — add "chat_trace" and "knowledge_map" panels
- `frontend/src/components/layout/Sidebar.tsx` — add nav entries

---

## Task 1: Retrieval models

**Files:**
- Create: `backend/models/retrieval_models.py`
- Create: `backend/tests/models/test_retrieval_models.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/models/test_retrieval_models.py`:

```python
import pytest
from pydantic import ValidationError
from models.retrieval_models import (
    TimePeriod, ParsedIntent, Candidate, SelectedArtifact,
    Selection, AnswerSource, Answer, StageTrace, QueryTrace,
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/models/test_retrieval_models.py -v
```

Expected: ImportError — `models.retrieval_models` not found.

- [ ] **Step 3: Implement retrieval models**

Create `backend/models/retrieval_models.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/models/test_retrieval_models.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/models/retrieval_models.py backend/tests/models/test_retrieval_models.py
git commit -m "feat(models): retrieval pipeline Pydantic models (ParsedIntent, Candidate, Selection, Answer, QueryTrace)"
```

---

## Task 2: Stage 1 — Intent Parser (LLM, mocked in tests)

**Files:**
- Create: `backend/services/retrieval/__init__.py`
- Create: `backend/services/retrieval/intent_parser.py`
- Create: `backend/tests/services/retrieval/__init__.py`
- Create: `backend/tests/services/retrieval/test_intent_parser.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/retrieval/__init__.py` (empty).

Create `backend/tests/services/retrieval/test_intent_parser.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/retrieval/test_intent_parser.py -v
```

Expected: ImportError — `services.retrieval.intent_parser` not found.

- [ ] **Step 3: Implement intent_parser**

Create `backend/services/retrieval/__init__.py` (empty).

Create `backend/services/retrieval/intent_parser.py`:

```python
import os
from openai import OpenAI
from models.retrieval_models import ParsedIntent

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a query understanding engine for a structured knowledge wiki.

Analyze the user's question and extract:
1. entity_mentions: Named entities (persons, orgs, products, places, events) explicitly mentioned or strongly implied.
   If none explicitly mentioned, return all relevant by category — never exclude candidates.
2. concept_mentions: Abstract concepts, design principles, techniques, or topics.
3. time_period: start/end ISO dates if temporal filters apply; null otherwise.
   Convert relative dates ("last year") to absolute ISO dates using today's date.
4. intent_type: One of: fact_lookup, comparison, synthesis, definition, how_to, temporal_trend.
   Use "comparison" when the question compares multiple entities (list all in entity_mentions).
5. expected_answer_form: One of: short, list, table, analysis, citation.
"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def parse_intent(question: str, model: str = None) -> ParsedIntent:
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    client = _get_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        response_format=ParsedIntent,
    )
    result = response.choices[0].message.parsed
    if result is None:
        raise ValueError("LLM returned no structured output for intent parsing")
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/retrieval/test_intent_parser.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/retrieval/__init__.py backend/services/retrieval/intent_parser.py backend/tests/services/retrieval/__init__.py backend/tests/services/retrieval/test_intent_parser.py
git commit -m "feat(retrieval/intent_parser): Stage 1 LLM intent parsing → ParsedIntent"
```

---

## Task 3: Stage 2 — Candidate Filter (deterministic)

**Files:**
- Create: `backend/services/retrieval/candidate_filter.py`
- Create: `backend/tests/services/retrieval/test_candidate_filter.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/retrieval/test_candidate_filter.py`:

```python
import json
import pytest
from pathlib import Path
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from models.wiki_models import Source, Entity, Concept
from models.retrieval_models import ParsedIntent
from datetime import datetime


@pytest.fixture
def store(tmp_path):
    s = WikiStore(root=tmp_path)
    # Seed: one source, one entity, one concept
    src = Source(
        id="src_001", title="Scandinavian Bedroom Design",
        type="txt", raw_path="raw/scandinavian-bedroom/parsed.md",
        ingested_at=datetime(2026, 4, 1),
        summary="Article about Scandinavian bedroom design.",
        key_takeaways=["Neutral palette."],
        questions=["What colors are typical in Scandinavian bedrooms?"],
        tags=["bedroom", "scandinavian", "design"],
    )
    s.write_source(src, slug="scandinavian-bedroom")

    entity = Entity(
        id="e_001", type="Place", aliases=["bedroom"],
        description="A Scandinavian bedroom.",
        mentions_count=1,
        questions=["What materials are used in Scandinavian bedrooms?"],
        tags=["bedroom", "place"],
    )
    s.write_entity(entity, slug="sypialnia")

    concept = Concept(
        id="c_001", definition="A color scheme using whites, beiges, and grays.",
        examples=["white walls"], related=[],
        questions=["What is a neutral palette?"],
        tags=["color", "design"],
    )
    s.write_concept(concept, slug="neutral-palette")

    regenerate_index(s)
    return s


@pytest.fixture
def fact_lookup_intent():
    return ParsedIntent(
        original_question="What colors are used in Scandinavian bedrooms?",
        entity_mentions=["sypialnia"],
        concept_mentions=["neutral palette"],
        intent_type="fact_lookup",
        expected_answer_form="short",
    )


@pytest.fixture
def empty_intent():
    return ParsedIntent(
        original_question="Unrelated question about aviation history.",
        entity_mentions=[],
        concept_mentions=[],
        intent_type="fact_lookup",
        expected_answer_form="short",
    )


def test_filter_candidates_returns_list(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    assert isinstance(result, list)


def test_filter_candidates_entity_match_scores_highest(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    entity_cands = [c for c in result if c.artifact_type == "entity"]
    assert len(entity_cands) >= 1
    assert entity_cands[0].score_breakdown.get("entity_match", 0) == 3


def test_filter_candidates_concept_match_scores(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    concept_cands = [c for c in result if c.artifact_type == "concept"]
    assert len(concept_cands) >= 1
    assert concept_cands[0].score_breakdown.get("concept_match", 0) == 2


def test_filter_candidates_question_overlap_scores(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    # "bedrooms" and "colors" appear in source questions → question_overlap > 0
    source_cands = [c for c in result if c.artifact_type == "source"]
    assert len(source_cands) >= 1
    assert source_cands[0].score_breakdown.get("question_overlap", 0) > 0


def test_filter_candidates_sorted_by_score(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    scores = [c.score for c in result]
    assert scores == sorted(scores, reverse=True)


def test_filter_candidates_empty_intent_returns_few_results(store, empty_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(empty_intent, store)
    # No entity/concept matches; only incidental tag matches possible
    entity_cands = [c for c in result if c.artifact_type == "entity" and c.score_breakdown.get("entity_match", 0) > 0]
    assert len(entity_cands) == 0


def test_filter_candidates_no_index_returns_empty(tmp_path):
    from services.retrieval.candidate_filter import filter_candidates
    empty_store = WikiStore(root=tmp_path)
    intent = ParsedIntent(
        original_question="Q", entity_mentions=[], concept_mentions=[],
        intent_type="fact_lookup", expected_answer_form="short",
    )
    result = filter_candidates(intent, empty_store)
    assert result == []


def test_filter_candidates_respects_top_n(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store, top_n=1)
    assert len(result) <= 1


def test_filter_candidates_artifact_id_format(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    for c in result:
        assert c.artifact_id.startswith(c.artifact_type + ":")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/retrieval/test_candidate_filter.py -v
```

Expected: ImportError — `services.retrieval.candidate_filter` not found.

- [ ] **Step 3: Implement candidate_filter**

Create `backend/services/retrieval/candidate_filter.py`:

```python
import json
from typing import Dict, List, Tuple
from models.retrieval_models import Candidate, ParsedIntent
from services.wiki_store import WikiStore


def filter_candidates(
    intent: ParsedIntent,
    store: WikiStore,
    top_n: int = 20,
) -> List[Candidate]:
    """
    Stage 2 (deterministic). Reads index.json and scores all artifacts.
    Scoring rules:
      +3 entity exact slug/alias match
      +2 concept exact slug match
      +2 question overlap (artifact question contains query word ≥4 chars)
      +1 per matching tag word
    Returns top_n by score (score > 0 only).
    """
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return []

    index = json.loads(index_path.read_text(encoding="utf-8"))
    query_lower = intent.original_question.lower()
    query_words = {w for w in query_lower.split() if len(w) >= 4}

    entity_slugs = {e.lower().replace(" ", "-") for e in intent.entity_mentions}
    entity_names = {e.lower() for e in intent.entity_mentions}
    concept_slugs = {c.lower().replace(" ", "-") for c in intent.concept_mentions}
    concept_names = {c.lower() for c in intent.concept_mentions}

    candidates: List[Candidate] = []

    for s in index.get("sources", []):
        score, breakdown = _score(
            slug=s["slug"], questions=s.get("questions", []), tags=s.get("tags", []),
            entity_slugs=entity_slugs, entity_names=entity_names,
            concept_slugs=concept_slugs, concept_names=concept_names,
            query_words=query_words, is_entity=False, is_concept=False,
        )
        if score > 0:
            candidates.append(Candidate(
                artifact_id=f"source:{s['id']}",
                artifact_type="source",
                slug=s["slug"],
                title=s["title"],
                score=score,
                score_breakdown=breakdown,
                questions=s.get("questions", []),
                tags=s.get("tags", []),
                description_preview=s.get("summary", "")[:200],
            ))

    for e in index.get("entities", []):
        aliases = [a.lower() for a in e.get("aliases", [])]
        score, breakdown = _score(
            slug=e["slug"], questions=e.get("questions", []), tags=e.get("tags", []),
            entity_slugs=entity_slugs, entity_names=entity_names,
            concept_slugs=concept_slugs, concept_names=concept_names,
            query_words=query_words, is_entity=True, is_concept=False,
            aliases=aliases,
        )
        if score > 0:
            candidates.append(Candidate(
                artifact_id=f"entity:{e['id']}",
                artifact_type="entity",
                slug=e["slug"],
                title=f"{e['type']}: {e['slug']}",
                score=score,
                score_breakdown=breakdown,
                questions=e.get("questions", []),
                tags=e.get("tags", []),
                description_preview=e.get("description_preview", "")[:200],
            ))

    for c in index.get("concepts", []):
        score, breakdown = _score(
            slug=c["slug"], questions=c.get("questions", []), tags=c.get("tags", []),
            entity_slugs=entity_slugs, entity_names=entity_names,
            concept_slugs=concept_slugs, concept_names=concept_names,
            query_words=query_words, is_entity=False, is_concept=True,
        )
        if score > 0:
            candidates.append(Candidate(
                artifact_id=f"concept:{c['id']}",
                artifact_type="concept",
                slug=c["slug"],
                title=c["slug"],
                score=score,
                score_breakdown=breakdown,
                questions=c.get("questions", []),
                tags=c.get("tags", []),
                description_preview=c.get("definition_preview", "")[:200],
            ))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_n]


def _score(
    slug: str,
    questions: list,
    tags: list,
    entity_slugs: set,
    entity_names: set,
    concept_slugs: set,
    concept_names: set,
    query_words: set,
    is_entity: bool,
    is_concept: bool,
    aliases: list = None,
) -> Tuple[int, Dict[str, int]]:
    score = 0
    breakdown: Dict[str, int] = {}

    if is_entity:
        slug_match = slug in entity_slugs
        name_match = slug.replace("-", " ") in entity_names
        alias_match = bool(aliases and any(
            a in entity_names or a.replace(" ", "-") in entity_slugs
            for a in (aliases or [])
        ))
        if slug_match or name_match or alias_match:
            score += 3
            breakdown["entity_match"] = 3

    if is_concept:
        if slug in concept_slugs or slug.replace("-", " ") in concept_names:
            score += 2
            breakdown["concept_match"] = 2

    q_hits = sum(
        1 for q in questions
        if any(word in q.lower() for word in query_words)
    )
    if q_hits:
        pts = min(q_hits * 2, 2)
        score += pts
        breakdown["question_overlap"] = pts

    tag_words = {t.lower() for t in tags}
    tag_overlap = len(tag_words & query_words)
    if tag_overlap:
        score += tag_overlap
        breakdown["tag_match"] = tag_overlap

    return score, breakdown
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/retrieval/test_candidate_filter.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/retrieval/candidate_filter.py backend/tests/services/retrieval/test_candidate_filter.py
git commit -m "feat(retrieval/candidate_filter): Stage 2 deterministic scoring over index.json"
```

---

## Task 4: Stage 3 — Selection (LLM, mocked in tests)

**Files:**
- Create: `backend/services/retrieval/selection.py`
- Create: `backend/tests/services/retrieval/test_selection.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/retrieval/test_selection.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/retrieval/test_selection.py -v
```

Expected: ImportError — `services.retrieval.selection` not found.

- [ ] **Step 3: Implement selection**

Create `backend/services/retrieval/selection.py`:

```python
import os
from typing import List
from openai import OpenAI
from models.retrieval_models import Candidate, Selection

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a retrieval selection assistant for a structured knowledge wiki.

Given a user question and a list of candidate artifacts (sources, entities, concepts) with metadata,
select the 1-5 most relevant artifacts that would help answer the question.

Rules:
- Use only the provided metadata (title, questions, tags, preview) — not your own knowledge.
- For each selected artifact, give a relevance_score (0.0–1.0) and short reasoning.
- Give an overall confidence score and reasoning for your selection.
- If no candidates are clearly relevant, return an empty selected list with low confidence.
"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def select_candidates(
    question: str,
    candidates: List[Candidate],
    model: str = None,
) -> Selection:
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    candidates_text = "\n\n".join(
        f"[{i + 1}] artifact_id={c.artifact_id}\n"
        f"  type={c.artifact_type}, slug={c.slug}\n"
        f"  title={c.title}\n"
        f"  tags={c.tags}\n"
        f"  questions={c.questions[:3]}\n"
        f"  preview={c.description_preview[:120]}"
        for i, c in enumerate(candidates)
    )

    client = _get_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"QUESTION: {question}\n\nCANDIDATES:\n{candidates_text}"},
        ],
        response_format=Selection,
    )
    result = response.choices[0].message.parsed
    if result is None:
        raise ValueError("LLM returned no structured output for selection")
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/retrieval/test_selection.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/retrieval/selection.py backend/tests/services/retrieval/test_selection.py
git commit -m "feat(retrieval/selection): Stage 3 LLM selection from candidate list"
```

---

## Task 5: Stage 4 — Context Assembly (deterministic)

**Files:**
- Create: `backend/services/retrieval/context_assembly.py`
- Create: `backend/tests/services/retrieval/test_context_assembly.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/retrieval/test_context_assembly.py`:

```python
import pytest
from datetime import datetime
from services.wiki_store import WikiStore
from models.wiki_models import Source, Entity, Claim, Edge, Span
from models.retrieval_models import Candidate, Selection, SelectedArtifact


@pytest.fixture
def store(tmp_path):
    s = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="Scandinavian Bedroom", type="txt",
        raw_path="raw/x/parsed.md", ingested_at=datetime(2026, 4, 1),
        summary="Article about Scandinavian bedroom design.",
        key_takeaways=["Neutral palette."], questions=["What colors?"], tags=["bedroom"],
    )
    s.write_source(src, slug="scandinavian-bedroom")

    entity = Entity(
        id="e_001", type="Place", aliases=["bedroom"],
        description="A Scandinavian bedroom.", mentions_count=1,
        questions=["What materials?"], tags=["bedroom"],
    )
    s.write_entity(entity, slug="sypialnia")

    claim = Claim(
        id="cl_001", text="Bedroom uses neutral colors.",
        subject_id="entity:e_001", source_id="src_001",
        span=Span(start=0, end=30, text="Bedroom uses neutral colors."),
        confidence=0.9, polarity="asserts",
    )
    s.append_claim(claim)

    edge = Edge(
        id="ed_001", **{"from": "source:src_001"},
        to="entity:e_001", relation="mentions",
        source_id="src_001",
        span=Span(start=0, end=5, text="Scand"),
        confidence=1.0,
    )
    s.append_edge(edge)
    return s


@pytest.fixture
def selection_with_source():
    return Selection(
        selected=[
            SelectedArtifact(
                artifact_id="source:src_001",
                relevance_score=0.9,
                reasoning="Primary source.",
            )
        ],
        confidence=0.85,
        reasoning="Best match.",
    )


@pytest.fixture
def candidates():
    return [
        Candidate(
            artifact_id="source:src_001",
            artifact_type="source",
            slug="scandinavian-bedroom",
            title="Scandinavian Bedroom",
            score=7,
            score_breakdown={"question_overlap": 2},
            questions=["What colors?"],
            tags=["bedroom"],
            description_preview="Article about Scandinavian bedroom design.",
        )
    ]


def test_assemble_context_returns_string_and_int(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, char_count = assemble_context("What colors?", selection_with_source, candidates, store)
    assert isinstance(context, str)
    assert isinstance(char_count, int)
    assert char_count == len(context)


def test_assemble_context_contains_artifact_id(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, _ = assemble_context("What colors?", selection_with_source, candidates, store)
    assert "source:src_001" in context


def test_assemble_context_contains_claim(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, _ = assemble_context("What colors?", selection_with_source, candidates, store)
    assert "cl_001" in context
    assert "neutral colors" in context


def test_assemble_context_contains_edge(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, _ = assemble_context("What colors?", selection_with_source, candidates, store)
    assert "mentions" in context


def test_assemble_context_contains_question(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, _ = assemble_context("What colors?", selection_with_source, candidates, store)
    assert "What colors?" in context


def test_assemble_context_empty_selection_returns_header_only(store, candidates):
    from services.retrieval.context_assembly import assemble_context
    empty_selection = Selection(selected=[], confidence=0.0, reasoning="No match.")
    context, char_count = assemble_context("Q", empty_selection, candidates, store)
    assert "Q" in context
    assert char_count > 0


def test_assemble_context_char_count_matches_len(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, char_count = assemble_context("Q", selection_with_source, candidates, store)
    assert char_count == len(context)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/retrieval/test_context_assembly.py -v
```

Expected: ImportError — `services.retrieval.context_assembly` not found.

- [ ] **Step 3: Implement context_assembly**

Create `backend/services/retrieval/context_assembly.py`:

```python
from typing import List, Tuple
from models.retrieval_models import Candidate, Selection
from services.wiki_store import WikiStore


def assemble_context(
    question: str,
    selection: Selection,
    candidates: List[Candidate],
    store: WikiStore,
) -> Tuple[str, int]:
    """
    Stage 4 (deterministic). Builds markdown context with citation anchors.
    Returns (context_markdown, char_count).
    """
    selected_ids = {sa.artifact_id for sa in selection.selected}
    selected_candidates = [c for c in candidates if c.artifact_id in selected_ids]

    all_claims = store.read_all_claims()
    all_edges = store.read_all_edges()

    sections = [f"# Context for: {question}\n"]

    for cand in selected_candidates:
        parts = [
            f"## {cand.artifact_type.capitalize()}: {cand.title} [{cand.artifact_id}]",
            cand.description_preview,
        ]

        relevant_claims = [
            cl for cl in all_claims
            if cl.subject_id == cand.artifact_id
            or cl.source_id == cand.artifact_id.split(":", 1)[-1]
        ]
        if relevant_claims:
            parts.append("\n### Claims:")
            for cl in relevant_claims[:5]:
                parts.append(
                    f"- [claim:{cl.id}] ({cl.polarity}) {cl.text} "
                    f"(confidence: {cl.confidence:.2f})"
                )

        related_edges = [
            e for e in all_edges
            if e.from_ == cand.artifact_id or e.to == cand.artifact_id
        ]
        if related_edges:
            parts.append("\n### Relations:")
            for e in related_edges[:5]:
                other = e.to if e.from_ == cand.artifact_id else e.from_
                parts.append(f"- [{e.relation}] → {other} [source:{e.source_id}]")

        if cand.questions:
            parts.append(f"\n### Answers questions: {', '.join(cand.questions[:3])}")

        sections.append("\n".join(parts))

    context = "\n\n---\n\n".join(sections)
    return context, len(context)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/retrieval/test_context_assembly.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/retrieval/context_assembly.py backend/tests/services/retrieval/test_context_assembly.py
git commit -m "feat(retrieval/context_assembly): Stage 4 deterministic markdown context with citation anchors"
```

---

## Task 6: Stage 5 — Answer Generator (LLM, mocked in tests)

**Files:**
- Create: `backend/services/retrieval/answer_generator.py`
- Create: `backend/tests/services/retrieval/test_answer_generator.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/retrieval/test_answer_generator.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from models.retrieval_models import Answer, AnswerSource
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


def _make_mock_response(answer: Answer):
    mock_msg = MagicMock()
    mock_msg.parsed = answer
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


def test_generate_answer_returns_answer():
    from services.retrieval.answer_generator import generate_answer
    mock_response = _make_mock_response(FIXED_ANSWER)
    with patch("services.retrieval.answer_generator._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client
        result = generate_answer("What colors?", "# Context\n\nSome context.")
    assert isinstance(result, Answer)
    assert result.confidence == 0.9


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
    assert len(result.sources) == 1
    assert result.sources[0].source_id == "src_001"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/retrieval/test_answer_generator.py -v
```

Expected: ImportError — `services.retrieval.answer_generator` not found.

- [ ] **Step 3: Implement answer_generator**

Create `backend/services/retrieval/answer_generator.py`:

```python
import os
from openai import OpenAI
from models.retrieval_models import Answer

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a precise knowledge retrieval assistant.

Answer the user's question using ONLY the provided context.
Do not use your own general knowledge.
Cite specific sources using their IDs from the context (e.g. [source:src_001] or [claim:cl_001]).
Provide reasoning steps showing how you arrived at the answer.
Be honest about confidence — lower it if context is incomplete or ambiguous.
Generate 2–3 related questions the user might want to ask next.
If the context contains no relevant information, say so clearly and set confidence below 0.4.
"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def generate_answer(question: str, context: str, model: str = None) -> Answer:
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    client = _get_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"QUESTION: {question}\n\nCONTEXT:\n{context}"},
        ],
        response_format=Answer,
    )
    result = response.choices[0].message.parsed
    if result is None:
        raise ValueError("LLM returned no structured output for answer generation")
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/retrieval/test_answer_generator.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/retrieval/answer_generator.py backend/tests/services/retrieval/test_answer_generator.py
git commit -m "feat(retrieval/answer_generator): Stage 5 LLM answer generation with citation anchors"
```

---

## Task 7: Retrieval Pipeline orchestration

**Files:**
- Create: `backend/services/retrieval/retrieval_pipeline.py`
- Create: `backend/tests/services/retrieval/test_retrieval_pipeline.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/retrieval/test_retrieval_pipeline.py`:

```python
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from models.wiki_models import Source, Entity, Concept, Claim, Edge, Span
from models.retrieval_models import (
    ParsedIntent, Selection, SelectedArtifact, Answer, AnswerSource, QueryTrace,
)


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


def run_pipeline(store):
    from services.retrieval.retrieval_pipeline import run_retrieval
    with patch("services.retrieval.retrieval_pipeline.parse_intent", return_value=FIXED_INTENT), \
         patch("services.retrieval.retrieval_pipeline.select_candidates", return_value=FIXED_SELECTION), \
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=FIXED_ANSWER):
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
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=FIXED_ANSWER):
        result = run_retrieval("Q", empty_store)
    assert isinstance(result, QueryTrace)
    assert result.candidates_count == 0
    assert result.selected_count == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/retrieval/test_retrieval_pipeline.py -v
```

Expected: ImportError — `services.retrieval.retrieval_pipeline` not found.

- [ ] **Step 3: Implement retrieval_pipeline**

Create `backend/services/retrieval/retrieval_pipeline.py`:

```python
import time
import uuid
from models.retrieval_models import QueryTrace, StageTrace, Selection
from services.wiki_store import WikiStore
from services.retrieval.intent_parser import parse_intent
from services.retrieval.candidate_filter import filter_candidates
from services.retrieval.selection import select_candidates
from services.retrieval.context_assembly import assemble_context
from services.retrieval.answer_generator import generate_answer


def run_retrieval(question: str, store: WikiStore) -> QueryTrace:
    """
    Orchestrates the 5-stage retrieval pipeline:
    Stage 1: Intent Parsing (LLM)
    Stage 2: Candidate Filtering (deterministic)
    Stage 3: Selection (LLM, skipped if no candidates)
    Stage 4: Context Assembly (deterministic)
    Stage 5: Answer Generation (LLM)
    """
    t_total = time.time()
    query_id = f"q_{uuid.uuid4().hex[:8]}"
    stages = []
    total_llm_calls = 0

    # Stage 1
    t = time.time()
    intent = parse_intent(question)
    total_llm_calls += 1
    stages.append(StageTrace(
        stage=1, name="Intent Parser",
        duration_ms=(time.time() - t) * 1000, llm_called=True,
        input_summary=f"question: {question[:80]}",
        output_summary=(
            f"intent_type={intent.intent_type}, "
            f"entities={intent.entity_mentions}, "
            f"concepts={intent.concept_mentions}"
        ),
    ))

    # Stage 2
    t = time.time()
    candidates = filter_candidates(intent, store)
    stages.append(StageTrace(
        stage=2, name="Candidate Filter",
        duration_ms=(time.time() - t) * 1000, llm_called=False,
        input_summary=f"intent_type={intent.intent_type}",
        output_summary=f"{len(candidates)} candidates scored",
    ))

    # Stage 3
    t = time.time()
    if candidates:
        selection = select_candidates(question, candidates)
        total_llm_calls += 1
        llm_called_s3 = True
    else:
        selection = Selection(selected=[], confidence=0.0, reasoning="No candidates found.")
        llm_called_s3 = False
    stages.append(StageTrace(
        stage=3, name="Selection",
        duration_ms=(time.time() - t) * 1000, llm_called=llm_called_s3,
        input_summary=f"{len(candidates)} candidates",
        output_summary=f"{len(selection.selected)} selected, confidence={selection.confidence:.2f}",
    ))

    # Stage 4
    t = time.time()
    context, context_chars = assemble_context(question, selection, candidates, store)
    stages.append(StageTrace(
        stage=4, name="Context Assembly",
        duration_ms=(time.time() - t) * 1000, llm_called=False,
        input_summary=f"{len(selection.selected)} selected artifacts",
        output_summary=f"{context_chars} chars assembled",
    ))

    # Stage 5
    t = time.time()
    answer = generate_answer(question, context)
    total_llm_calls += 1
    stages.append(StageTrace(
        stage=5, name="Answer Generator",
        duration_ms=(time.time() - t) * 1000, llm_called=True,
        input_summary=f"{context_chars} chars context",
        output_summary=f"confidence={answer.confidence:.2f}, sources={len(answer.sources)}",
    ))

    return QueryTrace(
        query_id=query_id,
        question=question,
        intent=intent,
        candidates_count=len(candidates),
        selected_count=len(selection.selected),
        context_chars=context_chars,
        answer=answer,
        stages=stages,
        total_duration_ms=(time.time() - t_total) * 1000,
        total_llm_calls=total_llm_calls,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/retrieval/test_retrieval_pipeline.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
cd backend && pytest tests/ -q --tb=no --ignore=tests/test_web_crawler.py
```

Expected: all ≥ 136 tests green.

- [ ] **Step 6: Commit**

```bash
git add backend/services/retrieval/retrieval_pipeline.py backend/tests/services/retrieval/test_retrieval_pipeline.py
git commit -m "feat(retrieval_pipeline): 5-stage orchestration (Intent→Filter→Select→Assemble→Answer)"
```

---

## Task 8: FastAPI retrieval router

**Files:**
- Create: `backend/api/retrieval.py`
- Create: `backend/tests/api/test_retrieval_api.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/api/test_retrieval_api.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/api/test_retrieval_api.py -v
```

Expected: 404 — route not found.

- [ ] **Step 3: Implement retrieval API router**

Create `backend/api/retrieval.py`:

```python
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.wiki_store import WikiStore
from services.retrieval.retrieval_pipeline import run_retrieval
from models.retrieval_models import QueryTrace

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])

_WIKI_DATA_DIR = Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default"))


def _get_store() -> WikiStore:
    return WikiStore(root=_WIKI_DATA_DIR)


class QueryRequest(BaseModel):
    question: str


@router.post("/query", response_model=QueryTrace)
def query_wiki(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        store = _get_store()
        return run_retrieval(request.question.strip(), store)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

- [ ] **Step 4: Add router to main.py**

In `backend/main.py`, add after the existing router imports:

```python
from api.retrieval import router as retrieval_router
```

And after the existing `app.include_router(wiki_router)` line:

```python
app.include_router(retrieval_router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && pytest tests/api/test_retrieval_api.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Run full test suite**

```bash
cd backend && pytest tests/ -q --tb=no --ignore=tests/test_web_crawler.py
```

Expected: all ≥ 142 tests green.

- [ ] **Step 7: Commit**

```bash
git add backend/api/retrieval.py backend/tests/api/test_retrieval_api.py backend/main.py
git commit -m "feat(api/retrieval): POST /api/retrieval/query endpoint returning QueryTrace"
```

---

## Task 9: Frontend — retrieval types + API client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Extend Panel type and add retrieval types in types/index.ts**

In `frontend/src/types/index.ts`, replace the existing `Panel` type with:

```typescript
export type Panel =
  | "documents"
  | "chunks"
  | "embeddings"
  | "chat"
  | "metrics"
  | "tutorial"
  | "sources"
  | "ingest"
  | "chat_trace"
  | "knowledge_map";
```

Then append at the end of the file:

```typescript
// ── Retrieval types ────────────────────────────────────────────────────────

export interface TimePeriod {
  start?: string | null;
  end?: string | null;
}

export interface ParsedIntent {
  original_question: string;
  entity_mentions: string[];
  concept_mentions: string[];
  time_period?: TimePeriod | null;
  intent_type: "fact_lookup" | "comparison" | "synthesis" | "definition" | "how_to" | "temporal_trend";
  expected_answer_form: "short" | "list" | "table" | "analysis" | "citation";
}

export interface RetrievalCandidate {
  artifact_id: string;
  artifact_type: "source" | "entity" | "concept";
  slug: string;
  title: string;
  score: number;
  score_breakdown: Record<string, number>;
  questions: string[];
  tags: string[];
  description_preview: string;
}

export interface SelectedArtifact {
  artifact_id: string;
  relevance_score: number;
  reasoning: string;
}

export interface RetrievalSelection {
  selected: SelectedArtifact[];
  confidence: number;
  reasoning: string;
}

export interface AnswerSource {
  source_id: string;
  claim_ids: string[];
  relevance: string;
}

export interface RetrievalAnswer {
  final_answer: string;
  sources: AnswerSource[];
  confidence: number;
  reasoning_steps: string[];
  related_questions: string[];
}

export interface RetrievalStageTrace {
  stage: number;
  name: string;
  duration_ms: number;
  llm_called: boolean;
  input_summary: string;
  output_summary: string;
}

export interface QueryTrace {
  query_id: string;
  question: string;
  intent: ParsedIntent;
  candidates_count: number;
  selected_count: number;
  context_chars: number;
  answer: RetrievalAnswer;
  stages: RetrievalStageTrace[];
  total_duration_ms: number;
  total_llm_calls: number;
}
```

- [ ] **Step 2: Add queryWiki to api/client.ts**

In `frontend/src/api/client.ts`, inside the `api` object, after the `ingestSource` method and before the `// Folders` section, add:

```typescript
  // Retrieval
  queryWiki: (question: string) =>
    request<import("../types").QueryTrace>("/retrieval/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && ./node_modules/.bin/tsc --noEmit
```

Expected: no output (zero errors).

- [ ] **Step 4: Commit**

```bash
cd .. && git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat(frontend/types): add retrieval types (QueryTrace, ParsedIntent, RetrievalAnswer, etc.) and queryWiki API method"
```

---

## Task 10: Frontend — ChatWithTracePanel

**Files:**
- Create: `frontend/src/components/chat_with_trace/ChatWithTracePanel.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Create ChatWithTracePanel**

Create `frontend/src/components/chat_with_trace/ChatWithTracePanel.tsx`:

```tsx
import { useState, useRef, useEffect } from "react";
import { Send, Brain, Filter, CheckSquare, Layers, Sparkles, Clock, AlertCircle } from "lucide-react";
import { api } from "../../api/client";
import type { QueryTrace, RetrievalStageTrace } from "../../types";

const STAGE_ICONS = [Brain, Filter, CheckSquare, Layers, Sparkles];
const STAGE_COLORS: Record<string, string> = {
  idle: "text-muted-foreground border-border",
  running: "text-blue-500 border-blue-500/40 bg-blue-500/5 animate-pulse",
  done: "text-green-500 border-green-500/40 bg-green-500/5",
  error: "text-red-500 border-red-500/40 bg-red-500/5",
};

function StageCard({ stage, status }: { stage: RetrievalStageTrace; status: "idle" | "running" | "done" | "error" }) {
  const Icon = STAGE_ICONS[stage.stage - 1] ?? Brain;
  return (
    <div className={`border rounded-md p-2.5 text-xs transition-colors ${STAGE_COLORS[status]}`}>
      <div className="flex items-center gap-1.5 font-medium mb-1">
        <Icon className="w-3 h-3" />
        Stage {stage.stage}: {stage.name}
        {stage.llm_called && <span className="ml-auto text-[10px] bg-muted px-1 rounded">LLM</span>}
      </div>
      {status === "done" && (
        <>
          <p className="text-muted-foreground truncate">{stage.output_summary}</p>
          <p className="text-muted-foreground/60 mt-0.5">
            <Clock className="w-2.5 h-2.5 inline mr-0.5" />
            {stage.duration_ms.toFixed(0)} ms
          </p>
        </>
      )}
    </div>
  );
}

export function ChatWithTracePanel() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [trace, setTrace] = useState<QueryTrace | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || loading) return;
    setLoading(true);
    setError(null);
    setTrace(null);
    try {
      const result = await api.queryWiki(question.trim());
      setTrace(result);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Query failed.");
    } finally {
      setLoading(false);
    }
  }

  const stageStatus = (idx: number): "idle" | "running" | "done" | "error" => {
    if (!trace) return loading ? (idx === 0 ? "running" : "idle") : "idle";
    return "done";
  };

  return (
    <div className="h-full flex flex-col p-6 gap-4">
      {/* Query bar */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your wiki…"
          className="flex-1 px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/40"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!question.trim() || loading}
          className="px-3 py-2 rounded-md bg-primary text-primary-foreground disabled:opacity-50 hover:bg-primary/90 transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-500 border border-red-500/30 rounded-md p-3">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      <div className="flex-1 flex gap-4 overflow-hidden min-h-0">
        {/* Left: Answer */}
        <div className="flex-1 border border-border rounded-lg bg-card p-4 overflow-auto">
          {!trace && !loading && (
            <p className="text-sm text-muted-foreground">Ask a question to see the answer here.</p>
          )}
          {loading && (
            <p className="text-sm text-muted-foreground animate-pulse">Running retrieval pipeline…</p>
          )}
          {trace && (
            <div className="space-y-4">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Question</p>
                <p className="text-sm font-medium">{trace.question}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Answer</p>
                <p className="text-sm whitespace-pre-wrap">{trace.answer.final_answer}</p>
              </div>
              {trace.answer.sources.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Sources</p>
                  <div className="space-y-1">
                    {trace.answer.sources.map((s) => (
                      <div key={s.source_id} className="text-xs border border-border rounded px-2 py-1">
                        <span className="font-mono">[source:{s.source_id}]</span>
                        {s.claim_ids.length > 0 && (
                          <span className="text-muted-foreground ml-2">
                            via {s.claim_ids.map((c) => `[claim:${c}]`).join(", ")}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {trace.answer.reasoning_steps.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Reasoning</p>
                  <ol className="text-xs space-y-0.5 list-decimal list-inside text-muted-foreground">
                    {trace.answer.reasoning_steps.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ol>
                </div>
              )}
              {trace.answer.related_questions.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Related questions</p>
                  <ul className="space-y-1">
                    {trace.answer.related_questions.map((q, i) => (
                      <li key={i}>
                        <button
                          onClick={() => setQuestion(q)}
                          className="text-xs text-primary hover:underline text-left"
                        >
                          {q}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="flex gap-3 text-xs text-muted-foreground pt-2 border-t border-border">
                <span>Confidence: {(trace.answer.confidence * 100).toFixed(0)}%</span>
                <span>{trace.total_duration_ms.toFixed(0)} ms</span>
                <span>{trace.total_llm_calls} LLM calls</span>
                <span>{trace.candidates_count} candidates → {trace.selected_count} selected</span>
              </div>
            </div>
          )}
        </div>

        {/* Right: Stage trace */}
        <div className="w-72 shrink-0 space-y-2 overflow-auto">
          <h3 className="text-sm font-semibold">Pipeline Trace</h3>
          {trace ? (
            trace.stages.map((s, i) => (
              <StageCard key={s.stage} stage={s} status={stageStatus(i)} />
            ))
          ) : (
            Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="border border-border rounded-md p-2.5 text-xs text-muted-foreground">
                Stage {i + 1}: waiting…
              </div>
            ))
          )}
          {trace && (
            <div className="text-xs text-muted-foreground pt-1 border-t border-border">
              <p>Intent: <span className="font-medium">{trace.intent.intent_type}</span></p>
              {trace.intent.entity_mentions.length > 0 && (
                <p>Entities: {trace.intent.entity_mentions.join(", ")}</p>
              )}
              {trace.intent.concept_mentions.length > 0 && (
                <p>Concepts: {trace.intent.concept_mentions.join(", ")}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire into App.tsx**

In `frontend/src/App.tsx`, add import after the existing wiki imports:

```tsx
import { ChatWithTracePanel } from "./components/chat_with_trace/ChatWithTracePanel";
```

And add panel rendering inside `<main>`:

```tsx
{activePanel === "chat_trace" && <ChatWithTracePanel />}
```

- [ ] **Step 3: Add nav entry in Sidebar.tsx**

In `frontend/src/components/layout/Sidebar.tsx`, add `MessageSquareText` to the lucide-react import:

```tsx
import { FileText, Layers, ScatterChart, MessageSquare, BarChart2, BookOpen, Database, Zap, MessageSquareText, Map } from "lucide-react";
```

Add to the NAV array after the `ingest` entry:

```tsx
{ id: "chat_trace" as Panel, label: "Wiki Chat", icon: MessageSquareText },
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && ./node_modules/.bin/tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/components/chat_with_trace/ChatWithTracePanel.tsx frontend/src/App.tsx frontend/src/components/layout/Sidebar.tsx
git commit -m "feat(frontend): ChatWithTracePanel — wiki query with 5-stage pipeline trace"
```

---

## Task 11: Frontend — KnowledgeMapPanel (browser tab)

**Files:**
- Create: `frontend/src/components/wiki/KnowledgeMapPanel.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Create KnowledgeMapPanel**

Create `frontend/src/components/wiki/KnowledgeMapPanel.tsx`:

```tsx
import { useState, useEffect } from "react";
import { RefreshCw, Search, User, Building, Package, MapPin, Calendar, Lightbulb } from "lucide-react";
import { api } from "../../api/client";
import type { WikiEntity, WikiConcept, WikiSource } from "../../types";

type Tab = "entities" | "concepts" | "sources";

const ENTITY_TYPE_ICONS: Record<string, React.ElementType> = {
  Person: User,
  Org: Building,
  Product: Package,
  Place: MapPin,
  Event: Calendar,
};

export function KnowledgeMapPanel() {
  const [tab, setTab] = useState<Tab>("entities");
  const [entities, setEntities] = useState<WikiEntity[]>([]);
  const [concepts, setConcepts] = useState<WikiConcept[]>([]);
  const [sources, setSources] = useState<WikiSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  async function fetchAll() {
    setLoading(true);
    try {
      const [e, c, s] = await Promise.all([
        api.listWikiEntities(),
        api.listWikiConcepts(),
        api.listWikiSources(),
      ]);
      setEntities(e);
      setConcepts(c);
      setSources(s);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { fetchAll(); }, []);

  const q = search.toLowerCase();

  const filteredEntities = entities.filter(
    (e) =>
      !q ||
      e.slug.includes(q) ||
      e.type.toLowerCase().includes(q) ||
      e.description.toLowerCase().includes(q) ||
      e.aliases.some((a) => a.toLowerCase().includes(q))
  );

  const filteredConcepts = concepts.filter(
    (c) =>
      !q ||
      c.slug.includes(q) ||
      c.definition.toLowerCase().includes(q)
  );

  const filteredSources = sources.filter(
    (s) =>
      !q ||
      s.title.toLowerCase().includes(q) ||
      s.summary.toLowerCase().includes(q) ||
      s.tags.some((t) => t.includes(q))
  );

  const tabs: { id: Tab; label: string; count: number }[] = [
    { id: "entities", label: "Entities", count: entities.length },
    { id: "concepts", label: "Concepts", count: concepts.length },
    { id: "sources", label: "Sources", count: sources.length },
  ];

  return (
    <div className="h-full flex flex-col p-6 gap-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex gap-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-3 py-1.5 text-xs rounded-md transition-colors ${
                tab === t.id
                  ? "bg-primary text-primary-foreground font-medium"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              {t.label} ({t.count})
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter…"
            className="w-full pl-7 pr-3 py-1.5 text-xs border border-border rounded-md bg-background focus:outline-none focus:ring-1 focus:ring-primary/40"
          />
        </div>
        <button
          onClick={fetchAll}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 border border-border rounded-lg bg-card overflow-auto">
        {tab === "entities" && (
          <table className="w-full text-xs">
            <thead className="border-b border-border sticky top-0 bg-card">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">Type</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">Slug</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">Description</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">Aliases</th>
                <th className="text-right px-3 py-2 font-medium text-muted-foreground">ID</th>
              </tr>
            </thead>
            <tbody>
              {filteredEntities.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-muted-foreground">
                    {entities.length === 0 ? "No entities ingested yet." : "No matches."}
                  </td>
                </tr>
              )}
              {filteredEntities.map((e) => {
                const Icon = ENTITY_TYPE_ICONS[e.type] ?? User;
                return (
                  <tr key={e.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                    <td className="px-3 py-2">
                      <span className="flex items-center gap-1">
                        <Icon className="w-3 h-3" />
                        {e.type}
                      </span>
                    </td>
                    <td className="px-3 py-2 font-mono">{e.slug}</td>
                    <td className="px-3 py-2 max-w-xs truncate text-muted-foreground">{e.description}</td>
                    <td className="px-3 py-2 text-muted-foreground">{e.aliases.slice(0, 3).join(", ")}</td>
                    <td className="px-3 py-2 text-right font-mono text-muted-foreground">{e.id}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {tab === "concepts" && (
          <table className="w-full text-xs">
            <thead className="border-b border-border sticky top-0 bg-card">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">Slug</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">Definition</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">Tags</th>
                <th className="text-right px-3 py-2 font-medium text-muted-foreground">ID</th>
              </tr>
            </thead>
            <tbody>
              {filteredConcepts.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-muted-foreground">
                    {concepts.length === 0 ? "No concepts ingested yet." : "No matches."}
                  </td>
                </tr>
              )}
              {filteredConcepts.map((c) => (
                <tr key={c.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="px-3 py-2 font-mono flex items-center gap-1">
                    <Lightbulb className="w-3 h-3 text-yellow-500" />
                    {c.slug}
                  </td>
                  <td className="px-3 py-2 max-w-xs truncate text-muted-foreground">{c.definition}</td>
                  <td className="px-3 py-2 text-muted-foreground">{c.tags.slice(0, 4).join(", ")}</td>
                  <td className="px-3 py-2 text-right font-mono text-muted-foreground">{c.id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {tab === "sources" && (
          <table className="w-full text-xs">
            <thead className="border-b border-border sticky top-0 bg-card">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">Title</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">Summary</th>
                <th className="text-left px-3 py-2 font-medium text-muted-foreground">Tags</th>
                <th className="text-right px-3 py-2 font-medium text-muted-foreground">ID</th>
              </tr>
            </thead>
            <tbody>
              {filteredSources.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-6 text-center text-muted-foreground">
                    {sources.length === 0 ? "No sources ingested yet." : "No matches."}
                  </td>
                </tr>
              )}
              {filteredSources.map((s) => (
                <tr key={s.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="px-3 py-2 font-medium truncate max-w-[180px]">{s.title}</td>
                  <td className="px-3 py-2 max-w-xs truncate text-muted-foreground">{s.summary}</td>
                  <td className="px-3 py-2 text-muted-foreground">{s.tags.slice(0, 4).join(", ")}</td>
                  <td className="px-3 py-2 text-right font-mono text-muted-foreground">{s.id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Wire into App.tsx**

In `frontend/src/App.tsx`, add import:

```tsx
import { KnowledgeMapPanel } from "./components/wiki/KnowledgeMapPanel";
```

And add panel rendering:

```tsx
{activePanel === "knowledge_map" && <KnowledgeMapPanel />}
```

- [ ] **Step 3: Add nav entry in Sidebar.tsx**

Add `Map` to the lucide-react import (already added `MessageSquareText` and `Map` in Task 10 if done sequentially — include if missing).

Add to the NAV array after the `chat_trace` entry:

```tsx
{ id: "knowledge_map" as Panel, label: "Knowledge Map", icon: Map },
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd frontend && ./node_modules/.bin/tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
cd .. && git add frontend/src/components/wiki/KnowledgeMapPanel.tsx frontend/src/App.tsx frontend/src/components/layout/Sidebar.tsx
git commit -m "feat(frontend): KnowledgeMapPanel browser tab — filterable entity/concept/source tables"
```

---

## Task 12: Final integration check

- [ ] **Step 1: Run complete backend test suite**

```bash
cd backend && pytest tests/ -v --tb=short --ignore=tests/test_web_crawler.py
```

Expected: all tests green. New total should be ≥ 142 tests.

- [ ] **Step 2: Verify no raw LLM calls in Phase 3 tests**

```bash
cd backend && grep -r "OpenAI\|openai" tests/services/retrieval/ tests/api/test_retrieval_api.py --include="*.py" | grep -v "mock\|Mock\|patch\|import\|reset_client"
```

Expected: no output.

- [ ] **Step 3: Verify TypeScript compiles clean**

```bash
cd frontend && ./node_modules/.bin/tsc --noEmit
```

Expected: no output.

- [ ] **Step 4: Commit integration tag**

```bash
cd .. && git tag phase-3-complete
```

---

## Self-Review Checklist

- [ ] All backend tests pass (`pytest tests/ -v`) with ≥ 142 tests green
- [ ] No real OpenAI calls in retrieval tests (all `_get_client` mocked via `patch`)
- [ ] `candidate_filter.py` returns `[]` (not an error) when `index.json` does not exist
- [ ] `retrieval_pipeline.py` skips Stage 3 LLM call when `candidates == []`
- [ ] `POST /api/retrieval/query` returns 400 for empty/whitespace-only question
- [ ] `POST /api/retrieval/query` returns 422 for missing `question` field
- [ ] `QueryTrace.stages` always has exactly 5 entries
- [ ] `total_llm_calls` is 3 when no conflicts in Stage 3 (pipeline called with candidates), 2 when candidates empty (Stage 3 skipped)
- [ ] `ChatWithTracePanel` shows answer + 5 stage cards after query
- [ ] `KnowledgeMapPanel` shows empty state when store is empty (no 500)
- [ ] `Panel` type includes `"chat_trace"` and `"knowledge_map"`
- [ ] Frontend compiles with no TypeScript errors

---

## What Phase 3 explicitly does NOT do

- No agent fallback (10-tool loop) — that is Phase 4.
- No graph visualization (force-directed) — that is Phase 5.
- No Lint workflow — that is Phase 6.
- No streaming answer output — synchronous `POST /query` only.
- The retrieval pipeline does not store query history (no `GET /chat/history`).

---

## Done criterion for Phase 3

A developer can:

1. `cd backend && pytest tests/ -v` → all green (≥ 142 tests)
2. Start the server: `uvicorn main:app --reload`
3. Send `POST /api/retrieval/query {"question": "What colors are typical?"}` and receive a `QueryTrace` with `status 200`
4. Open the React app, navigate to "Wiki Chat", type a question, and see the answer + 5-stage trace
5. Navigate to "Knowledge Map" and browse entities, concepts, sources in filterable tables
