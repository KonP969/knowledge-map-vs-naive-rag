# Phase 4 — Agent Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 10-tool OpenAI agent fallback to the retrieval pipeline that activates when the pipeline confidence is too low (0 candidates, Stage 3 confidence < 0.5, or Stage 5 confidence < 0.6) and records every tool call in `QueryTrace.agent_trace`.

**Architecture:** A pure-Python `agent_tools.py` module exposes 10 read-only functions over `WikiStore`; `agent_fallback.py` wraps them in an OpenAI tool-calling loop (max 8 turns); `retrieval_pipeline.py` checks three trigger conditions after each critical stage and calls the fallback when any is met. The result is attached as `QueryTrace.agent_trace` (Optional field, None when fallback not triggered).

**Tech Stack:** Python 3.9, Pydantic v2, `openai` SDK (tool calling via `chat.completions.create`), pytest + `unittest.mock`.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/models/retrieval_models.py` | Add `AgentToolCall`, `AgentTrace`; add `agent_trace` field to `QueryTrace` |
| Create | `backend/services/retrieval/agent_tools.py` | 10 pure-Python wiki search functions |
| Create | `backend/services/retrieval/agent_fallback.py` | OpenAI tool-calling loop, returns `AgentTrace` |
| Modify | `backend/services/retrieval/retrieval_pipeline.py` | Check 3 trigger conditions, call fallback, attach `agent_trace` |
| Modify | `backend/tests/models/test_retrieval_models.py` | Tests for new model fields |
| Create | `backend/tests/services/retrieval/test_agent_tools.py` | Unit tests for each tool function |
| Create | `backend/tests/services/retrieval/test_agent_fallback.py` | Unit tests for fallback orchestrator |
| Modify | `backend/tests/services/retrieval/test_retrieval_pipeline.py` | Tests for fallback trigger logic |

---

## Task 1: Extend retrieval models

**Files:**
- Modify: `backend/models/retrieval_models.py`
- Modify: `backend/tests/models/test_retrieval_models.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/models/test_retrieval_models.py`:

```python
from models.retrieval_models import (
    AgentToolCall, AgentTrace, QueryTrace,
    ParsedIntent, Answer, AnswerSource,
)


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
    from models.retrieval_models import (
        StageTrace, Selection, SelectedArtifact, ParsedIntent,
    )
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
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend && python -m pytest tests/models/test_retrieval_models.py -v -k "agent"
```
Expected: `ImportError` or `AttributeError` — `AgentToolCall` not defined yet.

- [ ] **Step 3: Add models to `retrieval_models.py`**

Add to `backend/models/retrieval_models.py` (after the `Answer` class, before `StageTrace`):

```python
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
```

Add `agent_trace` field to `QueryTrace`:

```python
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
    agent_trace: Optional["AgentTrace"] = None
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend && python -m pytest tests/models/test_retrieval_models.py -v -k "agent"
```
Expected: 4 tests PASS.

- [ ] **Step 5: Run full suite to check no regressions**

```
cd backend && python -m pytest --ignore=tests/test_web_crawler.py -q
```
Expected: all previously green tests still pass.

- [ ] **Step 6: Commit**

```bash
git add backend/models/retrieval_models.py backend/tests/models/test_retrieval_models.py
git commit -m "feat(models): add AgentToolCall, AgentTrace; add agent_trace to QueryTrace"
```

---

## Task 2: Implement 10 agent tools

**Files:**
- Create: `backend/services/retrieval/agent_tools.py`
- Create: `backend/tests/services/retrieval/test_agent_tools.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/retrieval/test_agent_tools.py`:

```python
import json
import pytest
from datetime import datetime
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from models.wiki_models import Source, Entity, Concept, Claim, Edge, Span


@pytest.fixture
def store(tmp_path):
    s = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="Scandinavian Bedroom", type="txt",
        raw_path="raw/x/parsed.md", ingested_at=datetime(2026, 4, 1),
        summary="Article about Scandinavian bedroom design with neutral tones.",
        key_takeaways=["Neutral palette."],
        questions=["What colors are typical in Scandinavian bedrooms?"],
        tags=["bedroom", "scandinavian"],
    )
    s.write_source(src, slug="scandinavian-bedroom")
    entity = Entity(
        id="e_001", type="Place", aliases=["bedroom", "sypialnia"],
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
    edge = Edge(
        id="edge_001", **{"from": "entity:e_001"},
        to="concept:c_001", relation="associated_with",
        source_id="src_001",
        span=Span(start=0, end=10, text="bedroom"),
        confidence=0.8,
    )
    s.append_edge(edge)
    # Write a raw parsed file so search_text can find content
    raw_dir = tmp_path / "raw" / "scandinavian-bedroom"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "parsed.md").write_text("Bedroom uses neutral tones including white and beige.", encoding="utf-8")
    regenerate_index(s)
    return s


# ── read_index ────────────────────────────────────────────────────────────────

def test_read_index_returns_json_string(store):
    from services.retrieval.agent_tools import read_index
    result = read_index(store)
    data = json.loads(result)
    assert "sources" in data
    assert "entities" in data
    assert "concepts" in data


def test_read_index_empty_store(tmp_path):
    from services.retrieval.agent_tools import read_index
    empty = WikiStore(root=tmp_path)
    result = read_index(empty)
    data = json.loads(result)
    assert data["sources"] == []


# ── search_entities ───────────────────────────────────────────────────────────

def test_search_entities_finds_by_alias(store):
    from services.retrieval.agent_tools import search_entities
    result = json.loads(search_entities(store, q="sypialnia"))
    assert len(result) >= 1
    assert result[0]["id"] == "e_001"


def test_search_entities_filters_by_type(store):
    from services.retrieval.agent_tools import search_entities
    result = json.loads(search_entities(store, q="sypialnia", type="Person"))
    assert result == []


def test_search_entities_no_match_returns_empty(store):
    from services.retrieval.agent_tools import search_entities
    result = json.loads(search_entities(store, q="xyznonexistent"))
    assert result == []


# ── search_concepts ───────────────────────────────────────────────────────────

def test_search_concepts_finds_by_slug(store):
    from services.retrieval.agent_tools import search_concepts
    result = json.loads(search_concepts(store, q="neutral"))
    assert len(result) >= 1


def test_search_concepts_no_match(store):
    from services.retrieval.agent_tools import search_concepts
    result = json.loads(search_concepts(store, q="xyz_never"))
    assert result == []


# ── search_wiki_content ───────────────────────────────────────────────────────

def test_search_wiki_content_finds_text(store):
    from services.retrieval.agent_tools import search_wiki_content
    result = json.loads(search_wiki_content(store, q="neutral"))
    assert len(result) >= 1
    assert "file" in result[0]
    assert "excerpt" in result[0]


def test_search_wiki_content_no_match(store):
    from services.retrieval.agent_tools import search_wiki_content
    result = json.loads(search_wiki_content(store, q="zzznomatch"))
    assert result == []


# ── search_text ───────────────────────────────────────────────────────────────

def test_search_text_finds_in_raw(store):
    from services.retrieval.agent_tools import search_text
    result = json.loads(search_text(store, q="beige"))
    assert len(result) >= 1
    assert "file" in result[0]


def test_search_text_no_match(store):
    from services.retrieval.agent_tools import search_text
    result = json.loads(search_text(store, q="nevermatches_xyz"))
    assert result == []


# ── get_node ──────────────────────────────────────────────────────────────────

def test_get_node_source(store):
    from services.retrieval.agent_tools import get_node
    result = json.loads(get_node(store, id="source:src_001"))
    assert result["id"] == "src_001"
    assert "summary" in result


def test_get_node_entity(store):
    from services.retrieval.agent_tools import get_node
    result = json.loads(get_node(store, id="entity:e_001"))
    assert result["id"] == "e_001"
    assert "description" in result


def test_get_node_concept(store):
    from services.retrieval.agent_tools import get_node
    result = json.loads(get_node(store, id="concept:c_001"))
    assert result["id"] == "c_001"
    assert "definition" in result


def test_get_node_unknown_returns_error(store):
    from services.retrieval.agent_tools import get_node
    result = json.loads(get_node(store, id="entity:nonexistent"))
    assert "error" in result


# ── get_claims ────────────────────────────────────────────────────────────────

def test_get_claims_all(store):
    from services.retrieval.agent_tools import get_claims
    result = json.loads(get_claims(store))
    assert len(result) == 1
    assert result[0]["id"] == "cl_001"


def test_get_claims_by_node_id(store):
    from services.retrieval.agent_tools import get_claims
    result = json.loads(get_claims(store, node_id="entity:e_001"))
    assert len(result) == 1


def test_get_claims_by_query(store):
    from services.retrieval.agent_tools import get_claims
    result = json.loads(get_claims(store, query="neutral"))
    assert len(result) == 1


def test_get_claims_by_polarity(store):
    from services.retrieval.agent_tools import get_claims
    result = json.loads(get_claims(store, polarity="denies"))
    assert result == []


# ── get_relations ─────────────────────────────────────────────────────────────

def test_get_relations_returns_edge(store):
    from services.retrieval.agent_tools import get_relations
    result = json.loads(get_relations(store, node_id="entity:e_001"))
    assert len(result) == 1
    assert result[0]["relation"] == "associated_with"


def test_get_relations_direction_out(store):
    from services.retrieval.agent_tools import get_relations
    result = json.loads(get_relations(store, node_id="entity:e_001", direction="out"))
    assert len(result) == 1


def test_get_relations_direction_in(store):
    from services.retrieval.agent_tools import get_relations
    result = json.loads(get_relations(store, node_id="entity:e_001", direction="in"))
    assert result == []


def test_get_relations_type_filter(store):
    from services.retrieval.agent_tools import get_relations
    result = json.loads(get_relations(store, node_id="entity:e_001", type="contradicts"))
    assert result == []


# ── read_source ───────────────────────────────────────────────────────────────

def test_read_source_returns_content(store):
    from services.retrieval.agent_tools import read_source
    result = json.loads(read_source(store, source_id="src_001"))
    assert result["id"] == "src_001"
    assert "content" in result


def test_read_source_unknown_id(store):
    from services.retrieval.agent_tools import read_source
    result = json.loads(read_source(store, source_id="src_999"))
    assert "error" in result


# ── query_log ─────────────────────────────────────────────────────────────────

def test_query_log_empty_log(store):
    from services.retrieval.agent_tools import query_log
    result = json.loads(query_log(store, filter="ingest"))
    assert isinstance(result, list)


def test_query_log_finds_entry(store, tmp_path):
    from services.retrieval.agent_tools import query_log
    from services.wiki_log import append_log_entry
    append_log_entry(store, op="ingest", source_id="src_001", details="test entry")
    result = json.loads(query_log(store, filter="ingest"))
    assert len(result) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend && python -m pytest tests/services/retrieval/test_agent_tools.py -v
```
Expected: `ModuleNotFoundError: No module named 'services.retrieval.agent_tools'`

- [ ] **Step 3: Implement `agent_tools.py`**

Create `backend/services/retrieval/agent_tools.py`:

```python
import json
from pathlib import Path
from typing import Optional

from services.wiki_store import WikiStore


def read_index(store: WikiStore) -> str:
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return json.dumps({"sources": [], "entities": [], "concepts": []})
    return index_path.read_text(encoding="utf-8")


def search_entities(store: WikiStore, q: str, type: Optional[str] = None) -> str:
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return "[]"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    q_lower = q.lower()
    results = []
    for e in data.get("entities", []):
        if type and e.get("type", "").lower() != type.lower():
            continue
        if (
            q_lower in e.get("slug", "").lower()
            or q_lower in e.get("id", "").lower()
            or any(q_lower in a.lower() for a in e.get("aliases", []))
        ):
            results.append(e)
    return json.dumps(results[:10], ensure_ascii=False)


def search_concepts(store: WikiStore, q: str) -> str:
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return "[]"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    q_lower = q.lower()
    results = [
        c for c in data.get("concepts", [])
        if q_lower in c.get("slug", "").lower()
        or q_lower in c.get("definition_preview", "").lower()
    ]
    return json.dumps(results[:10], ensure_ascii=False)


def search_wiki_content(store: WikiStore, q: str) -> str:
    wiki_dir = store.root / "wiki"
    q_lower = q.lower()
    results = []
    for md_file in sorted(wiki_dir.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        if q_lower in text.lower():
            idx = text.lower().find(q_lower)
            excerpt = text[max(0, idx - 50): idx + 150].replace("\n", " ")
            results.append({
                "file": str(md_file.relative_to(store.root)),
                "excerpt": excerpt,
            })
            if len(results) >= 5:
                break
    return json.dumps(results, ensure_ascii=False)


def search_text(store: WikiStore, q: str, scope: str = "raw") -> str:
    search_dir = store.root / scope
    if not search_dir.exists():
        return "[]"
    q_lower = q.lower()
    results = []
    for text_file in sorted(search_dir.rglob("*.md")):
        try:
            text = text_file.read_text(encoding="utf-8")
        except Exception:
            continue
        if q_lower in text.lower():
            idx = text.lower().find(q_lower)
            excerpt = text[max(0, idx - 50): idx + 150].replace("\n", " ")
            results.append({
                "file": str(text_file.relative_to(store.root)),
                "excerpt": excerpt,
            })
            if len(results) >= 5:
                break
    return json.dumps(results, ensure_ascii=False)


def get_node(store: WikiStore, id: str) -> str:
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return json.dumps({"error": "index not found"})
    data = json.loads(index_path.read_text(encoding="utf-8"))

    if ":" not in id:
        return json.dumps({"error": f"invalid id format: {id}"})
    prefix, node_id = id.split(":", 1)

    if prefix == "source":
        for s in data.get("sources", []):
            if s.get("id") == node_id:
                source = store.read_source(s["slug"])
                if source:
                    return json.dumps({
                        "id": source.id, "title": source.title,
                        "summary": source.summary, "questions": source.questions,
                        "key_takeaways": source.key_takeaways,
                    }, ensure_ascii=False)
    elif prefix == "entity":
        for e in data.get("entities", []):
            if e.get("id") == node_id:
                entity = store.read_entity(e["slug"], e["type"])
                if entity:
                    return json.dumps({
                        "id": entity.id, "type": entity.type,
                        "description": entity.description,
                        "questions": entity.questions, "aliases": entity.aliases,
                    }, ensure_ascii=False)
    elif prefix == "concept":
        for c in data.get("concepts", []):
            if c.get("id") == node_id:
                concept = store.read_concept(c["slug"])
                if concept:
                    return json.dumps({
                        "id": concept.id, "definition": concept.definition,
                        "examples": concept.examples, "questions": concept.questions,
                    }, ensure_ascii=False)

    return json.dumps({"error": f"node {id} not found"})


def get_claims(
    store: WikiStore,
    node_id: Optional[str] = None,
    query: Optional[str] = None,
    polarity: Optional[str] = None,
) -> str:
    claims = store.read_all_claims()
    if node_id:
        claims = [c for c in claims if c.subject_id == node_id or c.source_id == node_id]
    if polarity:
        claims = [c for c in claims if c.polarity == polarity]
    if query:
        q_lower = query.lower()
        claims = [c for c in claims if q_lower in c.text.lower()]
    result = [
        {
            "id": c.id, "text": c.text, "subject_id": c.subject_id,
            "source_id": c.source_id, "confidence": c.confidence, "polarity": c.polarity,
        }
        for c in claims[:20]
    ]
    return json.dumps(result, ensure_ascii=False)


def get_relations(
    store: WikiStore,
    node_id: str,
    direction: Optional[str] = None,
    type: Optional[str] = None,
) -> str:
    edges = store.read_all_edges()
    result = []
    for e in edges:
        from_match = e.from_ == node_id
        to_match = e.to == node_id
        if direction == "out" and not from_match:
            continue
        if direction == "in" and not to_match:
            continue
        if direction is None and not (from_match or to_match):
            continue
        if type and e.relation != type:
            continue
        result.append({
            "id": e.id, "from": e.from_, "to": e.to,
            "relation": e.relation, "source_id": e.source_id,
        })
    return json.dumps(result[:20], ensure_ascii=False)


def read_source(store: WikiStore, source_id: str, section: Optional[str] = None) -> str:
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return json.dumps({"error": "index not found"})
    data = json.loads(index_path.read_text(encoding="utf-8"))
    slug = next((s["slug"] for s in data.get("sources", []) if s.get("id") == source_id), None)
    if not slug:
        return json.dumps({"error": f"source {source_id} not found"})
    source = store.read_source(slug)
    if not source:
        return json.dumps({"error": f"slug {slug} not readable"})
    content = source.summary
    if section:
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if section.lower() in line.lower():
                excerpt = "\n".join(lines[i: i + 20])
                return json.dumps({"section": section, "content": excerpt}, ensure_ascii=False)
    return json.dumps({"id": source.id, "title": source.title, "content": content[:1000]}, ensure_ascii=False)


def query_log(store: WikiStore, filter: str) -> str:
    log_path = store.root / "wiki" / "log.md"
    if not log_path.exists():
        return "[]"
    f_lower = filter.lower()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    matches = [line for line in lines if line.startswith("##") and f_lower in line.lower()]
    return json.dumps(matches[:20], ensure_ascii=False)
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend && python -m pytest tests/services/retrieval/test_agent_tools.py -v
```
Expected: all tests PASS.

- [ ] **Step 5: Run full suite**

```
cd backend && python -m pytest --ignore=tests/test_web_crawler.py -q
```
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/services/retrieval/agent_tools.py backend/tests/services/retrieval/test_agent_tools.py
git commit -m "feat(retrieval): add agent_tools module with 10 wiki search functions"
```

---

## Task 3: Implement agent_fallback orchestrator

**Files:**
- Create: `backend/services/retrieval/agent_fallback.py`
- Create: `backend/tests/services/retrieval/test_agent_fallback.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/retrieval/test_agent_fallback.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch, call
from models.retrieval_models import AgentTrace, Answer
import services.retrieval.agent_fallback as _module


@pytest.fixture(autouse=True)
def reset_client():
    _module._client = None
    yield
    _module._client = None


def _make_stop_response(text: str):
    """Build a mock OpenAI response with finish_reason='stop'."""
    msg = MagicMock()
    msg.content = text
    msg.tool_calls = None
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = "stop"
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_tool_call_response(tool_name: str, args: dict, call_id: str = "call_1"):
    """Build a mock OpenAI response with a tool_call."""
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(args)

    msg = MagicMock()
    msg.content = None
    msg.tool_calls = [tc]
    choice = MagicMock()
    choice.message = msg
    choice.finish_reason = "tool_calls"
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_run_agent_fallback_returns_agent_trace(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    stop_resp = _make_stop_response("The answer is X.")
    with patch("services.retrieval.agent_fallback._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = stop_resp
        mock_get.return_value = mock_client
        result = run_agent_fallback("What is X?", store, "Stage 2 returned 0 candidates")
    assert isinstance(result, AgentTrace)
    assert result.triggered is True


def test_run_agent_fallback_trigger_reason_preserved(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    with patch("services.retrieval.agent_fallback._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_stop_response("ans")
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "Stage 3 confidence too low (0.3 < 0.5)")
    assert result.trigger_reason == "Stage 3 confidence too low (0.3 < 0.5)"


def test_run_agent_fallback_no_tool_calls_has_empty_tool_list(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    with patch("services.retrieval.agent_fallback._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_stop_response("ans")
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert result.tool_calls == []


def test_run_agent_fallback_stop_produces_final_answer(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    with patch("services.retrieval.agent_fallback._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_stop_response("The final answer is 42.")
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert result.final_answer is not None
    assert isinstance(result.final_answer, Answer)
    assert "42" in result.final_answer.final_answer


def test_run_agent_fallback_tool_call_then_stop(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    tool_resp = _make_tool_call_response("read_index", {})
    stop_resp = _make_stop_response("Found nothing.")
    with patch("services.retrieval.agent_fallback._get_client") as mock_get, \
         patch("services.retrieval.agent_fallback._dispatch_tool", return_value='{"sources":[]}') as mock_dispatch:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [tool_resp, stop_resp]
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "read_index"
    mock_dispatch.assert_called_once_with("read_index", {}, store)


def test_run_agent_fallback_tool_call_logged(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    tool_resp = _make_tool_call_response("search_entities", {"q": "bedroom"}, "call_abc")
    stop_resp = _make_stop_response("Done.")
    with patch("services.retrieval.agent_fallback._get_client") as mock_get, \
         patch("services.retrieval.agent_fallback._dispatch_tool", return_value="[]"):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [tool_resp, stop_resp]
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert result.tool_calls[0].args == {"q": "bedroom"}
    assert result.tool_calls[0].result_summary == "[]"


def test_run_agent_fallback_respects_max_iterations(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback, MAX_ITERATIONS
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    # Always return a tool call — the loop must terminate at MAX_ITERATIONS
    always_tool = _make_tool_call_response("read_index", {})
    with patch("services.retrieval.agent_fallback._get_client") as mock_get, \
         patch("services.retrieval.agent_fallback._dispatch_tool", return_value="{}"):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = always_tool
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert mock_client.chat.completions.create.call_count == MAX_ITERATIONS
    assert result.triggered is True


def test_run_agent_fallback_duration_ms_positive(tmp_path):
    from services.retrieval.agent_fallback import run_agent_fallback
    from services.wiki_store import WikiStore
    store = WikiStore(root=tmp_path)
    with patch("services.retrieval.agent_fallback._get_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_stop_response("ans")
        mock_get.return_value = mock_client
        result = run_agent_fallback("Q", store, "reason")
    assert result.duration_ms >= 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend && python -m pytest tests/services/retrieval/test_agent_fallback.py -v
```
Expected: `ModuleNotFoundError: No module named 'services.retrieval.agent_fallback'`

- [ ] **Step 3: Implement `agent_fallback.py`**

Create `backend/services/retrieval/agent_fallback.py`:

```python
import json
import os
import time
from typing import List, Optional

from openai import OpenAI

from models.retrieval_models import AgentToolCall, AgentTrace, Answer
from services.wiki_store import WikiStore
import services.retrieval.agent_tools as _tools

_client: OpenAI = None
MAX_ITERATIONS = 8

_SYSTEM_PROMPT = (
    "You are a wiki search agent with access to tools to search a structured knowledge wiki. "
    "Use tools to gather information, then answer the user's question with evidence from the wiki. "
    "When you have gathered enough information, provide your final answer. "
    "Always cite which sources, claims, or nodes you used."
)

_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_index",
            "description": "Get wiki overview — list of all sources, entities, and concepts.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_entities",
            "description": "Search entities by name or aliases.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Search query"},
                    "type": {"type": "string", "description": "Optional entity type filter"},
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_concepts",
            "description": "Search concepts by name.",
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string"}},
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_wiki_content",
            "description": "Full-text search over all wiki markdown files.",
            "parameters": {
                "type": "object",
                "properties": {"q": {"type": "string"}},
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "Full-text search over raw source content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "q": {"type": "string"},
                    "scope": {"type": "string", "description": "Search scope directory (default: raw)"},
                },
                "required": ["q"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_node",
            "description": (
                "Get full content of a node by prefixed ID "
                "(e.g. 'entity:e_001', 'concept:c_001', 'source:src_001')."
            ),
            "parameters": {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_claims",
            "description": "Get claims filtered by node_id, query text, or polarity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "query": {"type": "string"},
                    "polarity": {"type": "string", "enum": ["asserts", "denies"]},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_relations",
            "description": "Get edges for a node, with optional direction and relation type filters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string"},
                    "direction": {"type": "string", "enum": ["in", "out"]},
                    "type": {"type": "string"},
                },
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_source",
            "description": "Read source document content by source_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "section": {"type": "string"},
                },
                "required": ["source_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_log",
            "description": "Query the wiki activity log with a text filter string.",
            "parameters": {
                "type": "object",
                "properties": {"filter": {"type": "string"}},
                "required": ["filter"],
            },
        },
    },
]


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _dispatch_tool(name: str, args: dict, store: WikiStore) -> str:
    dispatch = {
        "read_index": lambda: _tools.read_index(store),
        "search_entities": lambda: _tools.search_entities(store, **args),
        "search_concepts": lambda: _tools.search_concepts(store, **args),
        "search_wiki_content": lambda: _tools.search_wiki_content(store, **args),
        "search_text": lambda: _tools.search_text(store, **args),
        "get_node": lambda: _tools.get_node(store, **args),
        "get_claims": lambda: _tools.get_claims(store, **args),
        "get_relations": lambda: _tools.get_relations(store, **args),
        "read_source": lambda: _tools.read_source(store, **args),
        "query_log": lambda: _tools.query_log(store, **args),
    }
    fn = dispatch.get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool: {name}"})
    return fn()


def run_agent_fallback(
    question: str,
    store: WikiStore,
    trigger_reason: str,
    model: str = None,
) -> AgentTrace:
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    t_start = time.time()
    client = _get_client()
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tool_calls: List[AgentToolCall] = []
    final_answer: Optional[Answer] = None

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=_TOOL_DEFINITIONS,
            tool_choice="auto",
        )
        choice = response.choices[0]
        msg = choice.message

        # Build assistant message dict for history
        assistant_msg: dict = {"role": "assistant"}
        if msg.content:
            assistant_msg["content"] = msg.content
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        if choice.finish_reason == "stop" or not msg.tool_calls:
            text = msg.content or ""
            final_answer = Answer(
                final_answer=text,
                sources=[],
                confidence=0.7,
                reasoning_steps=["Agent fallback completed"],
                related_questions=[],
            )
            break

        for tc in msg.tool_calls:
            t_tool = time.time()
            args = json.loads(tc.function.arguments or "{}")
            result = _dispatch_tool(tc.function.name, args, store)
            tool_calls.append(AgentToolCall(
                tool_name=tc.function.name,
                args=args,
                result_summary=result[:200],
                duration_ms=(time.time() - t_tool) * 1000,
            ))
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    return AgentTrace(
        triggered=True,
        trigger_reason=trigger_reason,
        tool_calls=tool_calls,
        final_answer=final_answer,
        duration_ms=(time.time() - t_start) * 1000,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend && python -m pytest tests/services/retrieval/test_agent_fallback.py -v
```
Expected: all 9 tests PASS.

- [ ] **Step 5: Run full suite**

```
cd backend && python -m pytest --ignore=tests/test_web_crawler.py -q
```
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/services/retrieval/agent_fallback.py backend/tests/services/retrieval/test_agent_fallback.py
git commit -m "feat(retrieval): agent_fallback orchestrator with 10-tool OpenAI loop"
```

---

## Task 4: Wire fallback into retrieval_pipeline

**Files:**
- Modify: `backend/services/retrieval/retrieval_pipeline.py`
- Modify: `backend/tests/services/retrieval/test_retrieval_pipeline.py`

- [ ] **Step 1: Write failing tests**

Add to the bottom of `backend/tests/services/retrieval/test_retrieval_pipeline.py`:

```python
from models.retrieval_models import AgentTrace, AgentToolCall


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
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=FIXED_ANSWER), \
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
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=FIXED_ANSWER), \
         patch("services.retrieval.retrieval_pipeline.run_agent_fallback", return_value=FIXED_AGENT_TRACE) as mock_fb:
        result = run_retrieval("Q", store)
    mock_fb.assert_called_once()
    call_trigger = mock_fb.call_args[0][2]  # trigger_reason positional arg
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
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=low_conf_answer), \
         patch("services.retrieval.retrieval_pipeline.run_agent_fallback", return_value=FIXED_AGENT_TRACE) as mock_fb:
        result = run_retrieval("Q", store)
    mock_fb.assert_called_once()
    call_trigger = mock_fb.call_args[0][2]
    assert "0.4" in call_trigger or "Stage 5" in call_trigger
    assert result.agent_trace is not None


def test_pipeline_fallback_trigger_reason_no_candidates(tmp_path):
    from services.retrieval.retrieval_pipeline import run_retrieval
    from services.wiki_store import WikiStore
    empty_store = WikiStore(root=tmp_path)
    with patch("services.retrieval.retrieval_pipeline.parse_intent", return_value=FIXED_INTENT), \
         patch("services.retrieval.retrieval_pipeline.generate_answer", return_value=FIXED_ANSWER), \
         patch("services.retrieval.retrieval_pipeline.run_agent_fallback", return_value=FIXED_AGENT_TRACE) as mock_fb:
        run_retrieval("Q", empty_store)
    trigger_reason = mock_fb.call_args[0][2]
    assert "Stage 2" in trigger_reason or "0 candidates" in trigger_reason
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend && python -m pytest tests/services/retrieval/test_retrieval_pipeline.py -v -k "fallback or agent_trace"
```
Expected: `ImportError` (run_agent_fallback not imported in pipeline) or `AttributeError` (agent_trace not on QueryTrace).

- [ ] **Step 3: Update `retrieval_pipeline.py`**

Replace the entire `backend/services/retrieval/retrieval_pipeline.py` with:

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
from services.retrieval.agent_fallback import run_agent_fallback


def run_retrieval(question: str, store: WikiStore) -> QueryTrace:
    """
    Orchestrates the 5-stage retrieval pipeline with agent fallback.
    Fallback triggers when:
      - Stage 2 returns 0 candidates, OR
      - Stage 3 selection confidence < 0.5, OR
      - Stage 5 answer confidence < 0.6.
    """
    t_total = time.time()
    query_id = f"q_{uuid.uuid4().hex[:8]}"
    stages = []
    total_llm_calls = 0
    agent_trace = None

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

    if not candidates:
        agent_trace = run_agent_fallback(
            question, store,
            trigger_reason="Stage 2 returned 0 candidates",
        )

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

    if agent_trace is None and candidates and selection.confidence < 0.5:
        agent_trace = run_agent_fallback(
            question, store,
            trigger_reason=f"Stage 3 confidence too low ({selection.confidence:.2f} < 0.5)",
        )

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

    if agent_trace is None and answer.confidence < 0.6:
        agent_trace = run_agent_fallback(
            question, store,
            trigger_reason=f"Stage 5 answer confidence too low ({answer.confidence:.2f} < 0.6)",
        )

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
        agent_trace=agent_trace,
    )
```

- [ ] **Step 4: Run new pipeline tests**

```
cd backend && python -m pytest tests/services/retrieval/test_retrieval_pipeline.py -v
```
Expected: all tests PASS (including new fallback tests).

- [ ] **Step 5: Run full suite**

```
cd backend && python -m pytest --ignore=tests/test_web_crawler.py -q
```
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add backend/services/retrieval/retrieval_pipeline.py backend/tests/services/retrieval/test_retrieval_pipeline.py
git commit -m "feat(retrieval): wire agent fallback into pipeline — 3 trigger conditions"
```

---

## Task 5: Tag and verify Phase 4 complete

- [ ] **Step 1: Final test run**

```
cd backend && python -m pytest --ignore=tests/test_web_crawler.py -v 2>&1 | tail -20
```
Expected: output ends with `X passed, 0 failed`.

- [ ] **Step 2: Count new tests**

```
cd backend && python -m pytest --ignore=tests/test_web_crawler.py --collect-only -q 2>&1 | tail -5
```
Record the total test count — should be at least 184 (prior count) + new tests from Tasks 1–4.

- [ ] **Step 3: Tag the phase**

```bash
git tag phase-4-complete
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|------------------|------|
| Agent fallback triggered when len(candidates)==0 | Task 4 (Stage 2 check) |
| Agent fallback triggered when selection.confidence < 0.5 | Task 4 (Stage 3 check) |
| Agent fallback triggered when answer.confidence < 0.6 | Task 4 (Stage 5 check) |
| 10 tools: read_index, search_entities, search_concepts, search_wiki_content, search_text, get_node, get_claims, get_relations, read_source, query_log | Task 2 |
| Result integrates as `agent_trace` field on QueryTrace | Task 1 + Task 4 |
| Trace shows each tool call | Task 1 (`AgentToolCall`) + Task 3 (logging) |

**Placeholder scan:** No TBD, TODO, or "implement later" found.

**Type consistency:**
- `AgentToolCall`, `AgentTrace` defined in Task 1, used in Task 3 and Task 4 — consistent.
- `run_agent_fallback` signature: `(question: str, store: WikiStore, trigger_reason: str)` — used identically in Task 4 pipeline code and test mocks.
- `_dispatch_tool` in `agent_fallback.py` is patched by name in Task 3 tests — matches the function name in the implementation.
- `FIXED_AGENT_TRACE` in pipeline tests uses `FIXED_ANSWER` imported from earlier fixture — consistent.
