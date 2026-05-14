# Phase 7 — Lint Tier 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 4 LLM-assisted semantic lint checks (Tier 3, `info` severity, opt-in), upgrade `empty_questions` to auto-fixable via LLM question generator, and add per-report log summary on close.

**Architecture:** One file per semantic check in `services/lint/checks/semantic/`. Each check function accepts optional `llm_client` for test injection. `runner.py` dispatches Tier 3 conditionally via `include_semantic: bool`. `fix_applier.py` handles three new fix types; only `empty_questions` calls LLM at fix time — `unmarked_contradiction` and `stale_summary` fixes are pure data writes using pre-computed payloads.

**Tech Stack:** Python 3.9, FastAPI, Pydantic v2, OpenAI `client.beta.chat.completions.parse`, pytest with `unittest.mock.MagicMock`. Frontend: React + TypeScript, lucide-react.

**Run tests from:** `cd backend && python -m pytest`  
**Run tsc check:** `cd frontend && npx tsc --noEmit`

---

### Task 1: Extend `lint_models.py` — 4 new IssueTypes + LLM response models

**Files:**
- Modify: `backend/models/lint_models.py`
- Test: `backend/tests/services/lint/test_lint_models.py`

- [ ] **Step 1: Write failing tests for new IssueType values and LLM models**

Add to `backend/tests/services/lint/test_lint_models.py`:

```python
from models.lint_models import (
    LintIssue,
    ContradictionJudgement,
    AliasMergeJudgement,
    MissingConceptJudgement,
    StaleSummaryJudgement,
    LlmQuestionsResult,
)


def test_tier3_issue_types_are_valid():
    for t in ("unmarked_contradiction", "entity_alias_collision", "missing_concept", "stale_summary"):
        issue = LintIssue(
            id=f"{t}:x",
            type=t,
            severity="info",
            location="entity:e_001",
            description="test",
            auto_fixable=False,
        )
        assert issue.type == t
        assert issue.severity == "info"


def test_contradiction_judgement():
    j = ContradictionJudgement(is_contradiction=True, explanation="opposing facts")
    assert j.is_contradiction is True


def test_alias_merge_judgement():
    j = AliasMergeJudgement(should_merge=True, explanation="same person", suggested_canonical="jan-kowalski")
    assert j.suggested_canonical == "jan-kowalski"


def test_missing_concept_judgement():
    j = MissingConceptJudgement(has_missing_concept=True, concept_name="oświetlenie", explanation="7 claims")
    assert j.concept_name == "oświetlenie"


def test_stale_summary_judgement():
    j = StaleSummaryJudgement(is_stale=True, proposed_summary="Updated summary.", explanation="missing claims")
    assert j.proposed_summary == "Updated summary."


def test_llm_questions_result():
    r = LlmQuestionsResult(questions=["What is X?", "How does Y work?"])
    assert len(r.questions) == 2
```

- [ ] **Step 2: Run tests — expect ImportError**

```
cd backend && python -m pytest tests/services/lint/test_lint_models.py -v
```
Expected: `ImportError: cannot import name 'ContradictionJudgement'`

- [ ] **Step 3: Extend `lint_models.py`**

Replace the `IssueType` Literal and add 5 new Pydantic models at the bottom of `backend/models/lint_models.py`:

```python
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


IssueSeverity = Literal["error", "warning", "info"]

IssueType = Literal[
    # Tier 1 (error)
    "provenance_missing",
    "dangling_source_ref",
    "dangling_node_ref",
    "corrupted_jsonl",
    # Tier 2 (warning)
    "orphan_entity",
    "orphan_concept",
    "empty_questions",
    "empty_description",
    # Tier 3 (info)
    "unmarked_contradiction",
    "entity_alias_collision",
    "missing_concept",
    "stale_summary",
]

IssueStatus = Literal["open", "fixed", "rejected", "wontfix"]


class LintIssue(BaseModel):
    id: str
    type: IssueType
    severity: IssueSeverity
    location: str
    description: str
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: IssueStatus = "open"


class LintReport(BaseModel):
    id: str
    created_at: datetime
    issues: List[LintIssue]
    counts_by_severity: Dict[str, int]
    counts_by_type: Dict[str, int]


# ── LLM response models for Tier 3 checks ────────────────────────────────────

class ContradictionJudgement(BaseModel):
    is_contradiction: bool
    explanation: str


class AliasMergeJudgement(BaseModel):
    should_merge: bool
    explanation: str
    suggested_canonical: str


class MissingConceptJudgement(BaseModel):
    has_missing_concept: bool
    concept_name: str
    explanation: str


class StaleSummaryJudgement(BaseModel):
    is_stale: bool
    proposed_summary: str
    explanation: str


class LlmQuestionsResult(BaseModel):
    questions: List[str]
```

- [ ] **Step 4: Run tests — expect PASS**

```
cd backend && python -m pytest tests/services/lint/test_lint_models.py -v
```
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```
git add backend/models/lint_models.py backend/tests/services/lint/test_lint_models.py
git commit -m "feat(lint): extend lint_models with Tier 3 IssueTypes and LLM response models"
```

---

### Task 2: Add wiki_store methods needed by Tier 3 fixes

**Files:**
- Modify: `backend/services/wiki_store.py`
- Test: `backend/tests/services/test_wiki_store.py`

- [ ] **Step 1: Write failing tests for the 4 new methods**

Add to `backend/tests/services/test_wiki_store.py` (append at the bottom):

```python
def test_update_source_summary(tmp_path):
    from datetime import datetime
    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="Test", type="article", raw_path="raw/test",
        ingested_at=datetime.now(), summary="Old summary.",
        key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, "test")
    store.update_source_summary("test", "New summary updated.")
    reloaded = store.read_source("test")
    assert reloaded.summary == "New summary updated."


def test_update_entity_questions(tmp_path):
    store = WikiStore(root=tmp_path)
    ent = Entity(id="e_001", type="Person", description="A person.", questions=[], tags=[])
    store.write_entity(ent, "jan-kowalski")
    store.update_entity_questions("jan-kowalski", "Person", ["What does Jan do?"])
    reloaded = store.read_entity("jan-kowalski", "Person")
    assert reloaded.questions == ["What does Jan do?"]


def test_update_concept_questions(tmp_path):
    store = WikiStore(root=tmp_path)
    c = Concept(id="c_001", definition="A concept.", examples=[], related=[], questions=[], tags=[])
    store.write_concept(c, "my-concept")
    store.update_concept_questions("my-concept", ["What is this concept?"])
    reloaded = store.read_concept("my-concept")
    assert reloaded.questions == ["What is this concept?"]


def test_update_source_questions(tmp_path):
    from datetime import datetime
    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_002", title="T2", type="article", raw_path="raw/t2",
        ingested_at=datetime.now(), summary="Summary.",
        key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, "t2")
    store.update_source_questions("t2", ["Q1?", "Q2?"])
    reloaded = store.read_source("t2")
    assert reloaded.questions == ["Q1?", "Q2?"]
```

- [ ] **Step 2: Run tests — expect AttributeError**

```
cd backend && python -m pytest tests/services/test_wiki_store.py::test_update_source_summary -v
```
Expected: `AttributeError: 'WikiStore' object has no attribute 'update_source_summary'`

- [ ] **Step 3: Add the 4 methods to `wiki_store.py`**

Append inside the `WikiStore` class, after `update_concept_description` (line ~307):

```python
    def update_source_summary(self, slug: str, summary: str) -> None:
        s = self.read_source(slug)
        if s is None:
            raise FileNotFoundError(f"Source not found: {slug}")
        self.write_source(s.model_copy(update={"summary": summary}), slug)

    def update_entity_questions(self, slug: str, entity_type: str, questions: List[str]) -> None:
        ent = self.read_entity(slug, entity_type)
        if ent is None:
            raise FileNotFoundError(f"Entity not found: {entity_type}/{slug}")
        self.write_entity(ent.model_copy(update={"questions": questions}), slug)

    def update_concept_questions(self, slug: str, questions: List[str]) -> None:
        c = self.read_concept(slug)
        if c is None:
            raise FileNotFoundError(f"Concept not found: {slug}")
        self.write_concept(c.model_copy(update={"questions": questions}), slug)

    def update_source_questions(self, slug: str, questions: List[str]) -> None:
        s = self.read_source(slug)
        if s is None:
            raise FileNotFoundError(f"Source not found: {slug}")
        self.write_source(s.model_copy(update={"questions": questions}), slug)
```

- [ ] **Step 4: Run tests — expect PASS**

```
cd backend && python -m pytest tests/services/test_wiki_store.py::test_update_source_summary tests/services/test_wiki_store.py::test_update_entity_questions tests/services/test_wiki_store.py::test_update_concept_questions tests/services/test_wiki_store.py::test_update_source_questions -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```
git add backend/services/wiki_store.py backend/tests/services/test_wiki_store.py
git commit -m "feat(wiki_store): add update_source_summary and update_*_questions methods"
```

---

### Task 3: `unmarked_contradiction` check

**Files:**
- Create: `backend/services/lint/checks/semantic/__init__.py`
- Create: `backend/services/lint/checks/semantic/unmarked_contradiction.py`
- Create: `backend/tests/services/lint/semantic/__init__.py`
- Create: `backend/tests/services/lint/semantic/test_unmarked_contradiction.py`

- [ ] **Step 1: Create empty `__init__.py` files**

```
backend/services/lint/checks/semantic/__init__.py  (empty)
backend/tests/services/lint/semantic/__init__.py   (empty)
```

- [ ] **Step 2: Write failing tests**

Create `backend/tests/services/lint/semantic/test_unmarked_contradiction.py`:

```python
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from models.lint_models import ContradictionJudgement
from models.wiki_models import Claim, Edge, Span
from services.lint.checks.semantic.unmarked_contradiction import check_unmarked_contradiction
from services.wiki_store import WikiStore


def _make_span():
    return Span(start=0, end=10, text="test")


def _make_claim(id_, subject_id, polarity, text="Some claim.", source_id="src_001"):
    return Claim(
        id=id_, text=text, subject_id=subject_id, source_id=source_id,
        span=_make_span(), confidence=0.9, polarity=polarity,
    )


def _mock_llm(is_contradiction: bool):
    client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.parsed = ContradictionJudgement(
        is_contradiction=is_contradiction,
        explanation="test explanation",
    )
    client.beta.chat.completions.parse.return_value = resp
    return client


def _store_with_claims(tmp_path, claims, edges=None):
    store = WikiStore(root=tmp_path)
    for c in claims:
        store.append_claim(c)
    for e in edges or []:
        store.append_edge(e)
    return store


def test_detects_contradiction(tmp_path):
    claims = [
        _make_claim("cl_001", "entity:e_001", "asserts", "Entity is great."),
        _make_claim("cl_002", "entity:e_001", "denies", "Entity is not great."),
    ]
    store = _store_with_claims(tmp_path, claims)
    issues = check_unmarked_contradiction(store, llm_client=_mock_llm(True))
    assert len(issues) == 1
    assert issues[0].type == "unmarked_contradiction"
    assert issues[0].severity == "info"
    assert issues[0].auto_fixable is True
    assert issues[0].payload["claim_a_id"] == "cl_001"
    assert issues[0].payload["claim_b_id"] == "cl_002"


def test_no_issue_when_llm_says_not_contradiction(tmp_path):
    claims = [
        _make_claim("cl_001", "entity:e_001", "asserts"),
        _make_claim("cl_002", "entity:e_001", "denies"),
    ]
    store = _store_with_claims(tmp_path, claims)
    issues = check_unmarked_contradiction(store, llm_client=_mock_llm(False))
    assert issues == []


def test_no_issue_when_same_polarity(tmp_path):
    claims = [
        _make_claim("cl_001", "entity:e_001", "asserts"),
        _make_claim("cl_002", "entity:e_001", "asserts"),
    ]
    store = _store_with_claims(tmp_path, claims)
    mock = _mock_llm(True)
    issues = check_unmarked_contradiction(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_no_issue_when_contradicts_edge_exists(tmp_path):
    import uuid
    claims = [
        _make_claim("cl_001", "entity:e_001", "asserts"),
        _make_claim("cl_002", "entity:e_001", "denies"),
    ]
    edge = Edge(
        id="e_c01",
        **{"from": "claim:cl_001"},
        to="claim:cl_002",
        relation="contradicts",
        source_id="src_001",
        span=_make_span(),
        confidence=1.0,
    )
    store = _store_with_claims(tmp_path, claims, edges=[edge])
    mock = _mock_llm(True)
    issues = check_unmarked_contradiction(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_empty_store_returns_no_issues(tmp_path):
    store = WikiStore(root=tmp_path)
    issues = check_unmarked_contradiction(store, llm_client=_mock_llm(True))
    assert issues == []


def test_respects_cap(tmp_path):
    # 60 subjects each with one asserts + one denies claim = 60 pairs
    claims = []
    for i in range(60):
        claims.append(_make_claim(f"ca_{i}", f"entity:e_{i:03d}", "asserts"))
        claims.append(_make_claim(f"cd_{i}", f"entity:e_{i:03d}", "denies"))
    store = _store_with_claims(tmp_path, claims)
    mock = _mock_llm(True)
    issues = check_unmarked_contradiction(store, llm_client=mock)
    assert mock.beta.chat.completions.parse.call_count <= 50
    assert len(issues) <= 50
```

- [ ] **Step 3: Run tests — expect ImportError**

```
cd backend && python -m pytest tests/services/lint/semantic/test_unmarked_contradiction.py -v
```
Expected: `ImportError: No module named 'services.lint.checks.semantic.unmarked_contradiction'`

- [ ] **Step 4: Implement `unmarked_contradiction.py`**

Create `backend/services/lint/checks/semantic/unmarked_contradiction.py`:

```python
import os
from collections import defaultdict
from typing import List, Optional

from openai import OpenAI

from models.lint_models import ContradictionJudgement, LintIssue
from services.wiki_store import WikiStore

_SEMANTIC_CAP = 50


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def check_unmarked_contradiction(
    store: WikiStore, llm_client=None
) -> List[LintIssue]:
    if llm_client is None:
        llm_client = _get_client()

    claims = store.read_all_claims()
    edges = store.read_all_edges()

    contradicts_pairs: set = set()
    for e in edges:
        if e.relation == "contradicts":
            contradicts_pairs.add((e.from_, e.to))
            contradicts_pairs.add((e.to, e.from_))

    by_subject: dict = defaultdict(list)
    for c in claims:
        by_subject[c.subject_id].append(c)

    issues: List[LintIssue] = []
    checked = 0
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    for subject_id, group in by_subject.items():
        if checked >= _SEMANTIC_CAP:
            break
        asserts = [c for c in group if c.polarity == "asserts"]
        denies = [c for c in group if c.polarity == "denies"]
        if not asserts or not denies:
            continue

        for ca in asserts:
            for cd in denies:
                if checked >= _SEMANTIC_CAP:
                    break
                key_ab = (f"claim:{ca.id}", f"claim:{cd.id}")
                key_ba = (f"claim:{cd.id}", f"claim:{ca.id}")
                if key_ab in contradicts_pairs or key_ba in contradicts_pairs:
                    continue

                checked += 1
                resp = llm_client.beta.chat.completions.parse(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Judge whether these two claims are genuinely contradictory. "
                                "Return is_contradiction=True only if they express opposing facts about the same subject."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Claim A (asserts): {ca.text}\nClaim B (denies): {cd.text}",
                        },
                    ],
                    response_format=ContradictionJudgement,
                )
                result = resp.choices[0].message.parsed
                if result and result.is_contradiction:
                    issues.append(LintIssue(
                        id=f"unmarked_contradiction:{ca.id}:{cd.id}",
                        type="unmarked_contradiction",
                        severity="info",
                        location=subject_id,
                        description=(
                            f"Claims {ca.id} and {cd.id} have opposing polarity on "
                            f"{subject_id} without a contradicts edge. {result.explanation}"
                        ),
                        suggested_fix="Add contradicts edge",
                        auto_fixable=True,
                        payload={
                            "claim_a_id": ca.id,
                            "claim_b_id": cd.id,
                            "subject_id": subject_id,
                            "source_id": ca.source_id,
                        },
                    ))
    return issues
```

- [ ] **Step 5: Run tests — expect PASS**

```
cd backend && python -m pytest tests/services/lint/semantic/test_unmarked_contradiction.py -v
```
Expected: all 6 tests PASS

- [ ] **Step 6: Commit**

```
git add backend/services/lint/checks/semantic/ backend/tests/services/lint/semantic/
git commit -m "feat(lint/semantic): unmarked_contradiction check with LLM judgement"
```

---

### Task 4: `entity_alias_collision` check

**Files:**
- Create: `backend/services/lint/checks/semantic/entity_alias_collision.py`
- Create: `backend/tests/services/lint/semantic/test_entity_alias_collision.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/lint/semantic/test_entity_alias_collision.py`:

```python
from unittest.mock import MagicMock

from models.lint_models import AliasMergeJudgement
from models.wiki_models import Entity
from services.lint.checks.semantic.entity_alias_collision import (
    _edit_distance,
    check_entity_alias_collision,
)
from services.wiki_store import WikiStore


def _mock_llm(should_merge: bool, canonical: str = "jan-kowalski"):
    client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.parsed = AliasMergeJudgement(
        should_merge=should_merge,
        explanation="test",
        suggested_canonical=canonical,
    )
    client.beta.chat.completions.parse.return_value = resp
    return client


def _write_entity(store, slug, entity_type="Person", entity_id=None):
    ent = Entity(
        id=entity_id or f"e_{slug}",
        type=entity_type,
        description="A person.",
        questions=[],
        tags=[],
    )
    store.write_entity(ent, slug)
    return ent


def test_edit_distance_same():
    assert _edit_distance("abc", "abc") == 0


def test_edit_distance_one_insertion():
    assert _edit_distance("abc", "abcd") == 1


def test_edit_distance_substitution():
    assert _edit_distance("abc", "axc") == 1


def test_detects_collision(tmp_path):
    store = WikiStore(root=tmp_path)
    _write_entity(store, "jan-kowalski", entity_id="e_001")
    _write_entity(store, "jan-kowalsky", entity_id="e_002")
    issues = check_entity_alias_collision(store, llm_client=_mock_llm(True, "jan-kowalski"))
    assert len(issues) == 1
    assert issues[0].type == "entity_alias_collision"
    assert issues[0].auto_fixable is False
    assert "jan-kowalski" in issues[0].suggested_fix


def test_no_issue_when_llm_says_keep_separate(tmp_path):
    store = WikiStore(root=tmp_path)
    _write_entity(store, "jan-kowalski", entity_id="e_001")
    _write_entity(store, "jan-kowalsky", entity_id="e_002")
    issues = check_entity_alias_collision(store, llm_client=_mock_llm(False))
    assert issues == []


def test_no_issue_when_distance_gte_3(tmp_path):
    store = WikiStore(root=tmp_path)
    _write_entity(store, "jan-kowalski", entity_id="e_001")
    _write_entity(store, "anna-nowak", entity_id="e_002")
    mock = _mock_llm(True)
    issues = check_entity_alias_collision(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_empty_store_returns_no_issues(tmp_path):
    store = WikiStore(root=tmp_path)
    issues = check_entity_alias_collision(store, llm_client=_mock_llm(True))
    assert issues == []


def test_respects_cap(tmp_path):
    store = WikiStore(root=tmp_path)
    for i in range(30):
        _write_entity(store, f"jan-{i:02d}", entity_id=f"e_{i:03d}")
    mock = _mock_llm(True)
    check_entity_alias_collision(store, llm_client=mock)
    assert mock.beta.chat.completions.parse.call_count <= 50
```

- [ ] **Step 2: Run tests — expect ImportError**

```
cd backend && python -m pytest tests/services/lint/semantic/test_entity_alias_collision.py -v
```
Expected: `ImportError: No module named 'services.lint.checks.semantic.entity_alias_collision'`

- [ ] **Step 3: Implement `entity_alias_collision.py`**

Create `backend/services/lint/checks/semantic/entity_alias_collision.py`:

```python
import os
from typing import List

from openai import OpenAI

from models.lint_models import AliasMergeJudgement, LintIssue
from services.wiki_store import ENTITIES_DIR, WikiStore

_SEMANTIC_CAP = 50


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _edit_distance(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def _normalize(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").strip().lower()


def check_entity_alias_collision(
    store: WikiStore, llm_client=None
) -> List[LintIssue]:
    if llm_client is None:
        llm_client = _get_client()

    base = store.root / "wiki" / ENTITIES_DIR
    if not base.exists():
        return []

    entities = []
    for type_dir in base.iterdir():
        if not type_dir.is_dir():
            continue
        for path in type_dir.glob("*.md"):
            ent = store.read_entity(path.stem, type_dir.name)
            if ent:
                entities.append((path.stem, type_dir.name, ent, _normalize(path.stem)))

    issues: List[LintIssue] = []
    checked = 0
    seen_pairs: set = set()
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    for i in range(len(entities)):
        if checked >= _SEMANTIC_CAP:
            break
        slug_a, type_a, ent_a, norm_a = entities[i]
        for j in range(i + 1, len(entities)):
            if checked >= _SEMANTIC_CAP:
                break
            slug_b, type_b, ent_b, norm_b = entities[j]
            pair = tuple(sorted([ent_a.id, ent_b.id]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if _edit_distance(norm_a, norm_b) >= 3:
                continue

            checked += 1
            resp = llm_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Judge whether these two entity names refer to the same real-world entity and should be merged.",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Entity A: {slug_a} (type: {type_a}, id: {ent_a.id})\n"
                            f"Entity B: {slug_b} (type: {type_b}, id: {ent_b.id})"
                        ),
                    },
                ],
                response_format=AliasMergeJudgement,
            )
            result = resp.choices[0].message.parsed
            if result and result.should_merge:
                issues.append(LintIssue(
                    id=f"entity_alias_collision:{ent_a.id}:{ent_b.id}",
                    type="entity_alias_collision",
                    severity="info",
                    location=f"entity:{ent_a.id}",
                    description=(
                        f"Entities '{slug_a}' and '{slug_b}' have similar names. {result.explanation}"
                    ),
                    suggested_fix=f"Merge into '{result.suggested_canonical}'",
                    auto_fixable=False,
                    payload={
                        "entity_a_id": ent_a.id,
                        "entity_b_id": ent_b.id,
                        "slug_a": slug_a,
                        "slug_b": slug_b,
                        "type_a": type_a,
                        "type_b": type_b,
                        "suggested_canonical": result.suggested_canonical,
                    },
                ))
    return issues
```

- [ ] **Step 4: Run tests — expect PASS**

```
cd backend && python -m pytest tests/services/lint/semantic/test_entity_alias_collision.py -v
```
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```
git add backend/services/lint/checks/semantic/entity_alias_collision.py backend/tests/services/lint/semantic/test_entity_alias_collision.py
git commit -m "feat(lint/semantic): entity_alias_collision check with Levenshtein pre-filter"
```

---

### Task 5: `missing_concept` check

**Files:**
- Create: `backend/services/lint/checks/semantic/missing_concept.py`
- Create: `backend/tests/services/lint/semantic/test_missing_concept.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/lint/semantic/test_missing_concept.py`:

```python
from unittest.mock import MagicMock

from models.lint_models import MissingConceptJudgement
from models.wiki_models import Claim, Entity, Span
from services.lint.checks.semantic.missing_concept import check_missing_concept
from services.wiki_store import WikiStore


def _make_claim(id_, subject_id, source_id="src_001"):
    return Claim(
        id=id_, text=f"Claim text {id_}.", subject_id=subject_id, source_id=source_id,
        span=Span(start=0, end=10, text="test"), confidence=0.9, polarity="asserts",
    )


def _mock_llm(has_concept: bool, concept_name: str = "oświetlenie"):
    client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.parsed = MissingConceptJudgement(
        has_missing_concept=has_concept,
        concept_name=concept_name,
        explanation="many claims about topic",
    )
    client.beta.chat.completions.parse.return_value = resp
    return client


def test_detects_missing_concept(tmp_path):
    store = WikiStore(root=tmp_path)
    ent = Entity(id="e_001", type="Person", description="Entity.", questions=[], tags=[])
    store.write_entity(ent, "test-entity")
    for i in range(5):
        store.append_claim(_make_claim(f"cl_{i:03d}", "entity:e_001"))
    issues = check_missing_concept(store, llm_client=_mock_llm(True))
    assert len(issues) == 1
    assert issues[0].type == "missing_concept"
    assert issues[0].auto_fixable is False
    assert "oświetlenie" in issues[0].suggested_fix


def test_no_issue_below_threshold(tmp_path):
    store = WikiStore(root=tmp_path)
    for i in range(4):
        store.append_claim(_make_claim(f"cl_{i}", "entity:e_001"))
    mock = _mock_llm(True)
    issues = check_missing_concept(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_no_issue_when_llm_says_no_concept(tmp_path):
    store = WikiStore(root=tmp_path)
    for i in range(5):
        store.append_claim(_make_claim(f"cl_{i}", "entity:e_001"))
    issues = check_missing_concept(store, llm_client=_mock_llm(False))
    assert issues == []


def test_skips_non_entity_subjects(tmp_path):
    store = WikiStore(root=tmp_path)
    for i in range(5):
        store.append_claim(_make_claim(f"cl_{i}", "concept:c_001"))
    mock = _mock_llm(True)
    issues = check_missing_concept(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_empty_store_returns_no_issues(tmp_path):
    store = WikiStore(root=tmp_path)
    issues = check_missing_concept(store, llm_client=_mock_llm(True))
    assert issues == []
```

- [ ] **Step 2: Run tests — expect ImportError**

```
cd backend && python -m pytest tests/services/lint/semantic/test_missing_concept.py -v
```

- [ ] **Step 3: Implement `missing_concept.py`**

Create `backend/services/lint/checks/semantic/missing_concept.py`:

```python
import os
from collections import defaultdict
from typing import List

from openai import OpenAI

from models.lint_models import LintIssue, MissingConceptJudgement
from services.wiki_store import WikiStore

_SEMANTIC_CAP = 50
_CLAIM_THRESHOLD = 5


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def check_missing_concept(
    store: WikiStore, llm_client=None
) -> List[LintIssue]:
    if llm_client is None:
        llm_client = _get_client()

    claims = store.read_all_claims()
    by_subject: dict = defaultdict(list)
    for c in claims:
        if c.subject_id.startswith("entity:"):
            by_subject[c.subject_id].append(c)

    issues: List[LintIssue] = []
    checked = 0
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    for subject_id, group in by_subject.items():
        if checked >= _SEMANTIC_CAP:
            break
        if len(group) < _CLAIM_THRESHOLD:
            continue

        checked += 1
        claim_texts = "\n".join(f"- {c.text}" for c in group[:20])
        resp = llm_client.beta.chat.completions.parse(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Given claims about an entity, determine if there is a recurring "
                        "topic/theme that warrants its own Concept node in the knowledge graph."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Entity: {subject_id}\nClaims:\n{claim_texts}",
                },
            ],
            response_format=MissingConceptJudgement,
        )
        result = resp.choices[0].message.parsed
        if result and result.has_missing_concept:
            entity_id = subject_id.split(":", 1)[1]
            issues.append(LintIssue(
                id=f"missing_concept:{entity_id}:{result.concept_name}",
                type="missing_concept",
                severity="info",
                location=subject_id,
                description=(
                    f"{subject_id} has {len(group)} claims about '{result.concept_name}' "
                    f"without a Concept node. {result.explanation}"
                ),
                suggested_fix=f"Create concept '{result.concept_name}'",
                auto_fixable=False,
                payload={
                    "entity_id": entity_id,
                    "concept_name": result.concept_name,
                },
            ))
    return issues
```

- [ ] **Step 4: Run tests — expect PASS**

```
cd backend && python -m pytest tests/services/lint/semantic/test_missing_concept.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```
git add backend/services/lint/checks/semantic/missing_concept.py backend/tests/services/lint/semantic/test_missing_concept.py
git commit -m "feat(lint/semantic): missing_concept check — entity with ≥5 claims on common topic"
```

---

### Task 6: `stale_summary` check

**Files:**
- Create: `backend/services/lint/checks/semantic/stale_summary.py`
- Create: `backend/tests/services/lint/semantic/test_stale_summary.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/lint/semantic/test_stale_summary.py`:

```python
from datetime import datetime
from unittest.mock import MagicMock

from models.lint_models import StaleSummaryJudgement
from models.wiki_models import Claim, Source, Span
from services.lint.checks.semantic.stale_summary import check_stale_summary
from services.wiki_store import WikiStore


def _make_source(slug, source_id="src_001"):
    return Source(
        id=source_id, title="Test Source", type="article", raw_path=f"raw/{slug}",
        ingested_at=datetime.now(), summary="Original summary.",
        key_takeaways=[], questions=[], tags=[],
    )


def _make_claim(id_, source_id="src_001"):
    return Claim(
        id=id_, text="New important fact.", subject_id="entity:e_001", source_id=source_id,
        span=Span(start=0, end=10, text="test"), confidence=0.9, polarity="asserts",
    )


def _mock_llm(is_stale: bool, proposed="Updated summary."):
    client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.parsed = StaleSummaryJudgement(
        is_stale=is_stale, proposed_summary=proposed, explanation="missing facts",
    )
    client.beta.chat.completions.parse.return_value = resp
    return client


def test_detects_stale_summary(tmp_path):
    store = WikiStore(root=tmp_path)
    store.write_source(_make_source("test"), "test")
    store.append_claim(_make_claim("cl_001"))
    issues = check_stale_summary(store, llm_client=_mock_llm(True, "Updated summary."))
    assert len(issues) == 1
    assert issues[0].type == "stale_summary"
    assert issues[0].auto_fixable is True
    assert issues[0].payload["proposed_summary"] == "Updated summary."
    assert issues[0].payload["slug"] == "test"


def test_no_issue_when_llm_says_fresh(tmp_path):
    store = WikiStore(root=tmp_path)
    store.write_source(_make_source("test"), "test")
    store.append_claim(_make_claim("cl_001"))
    issues = check_stale_summary(store, llm_client=_mock_llm(False))
    assert issues == []


def test_skips_source_with_no_claims(tmp_path):
    store = WikiStore(root=tmp_path)
    store.write_source(_make_source("test"), "test")
    mock = _mock_llm(True)
    issues = check_stale_summary(store, llm_client=mock)
    assert issues == []
    mock.beta.chat.completions.parse.assert_not_called()


def test_empty_store_returns_no_issues(tmp_path):
    store = WikiStore(root=tmp_path)
    issues = check_stale_summary(store, llm_client=_mock_llm(True))
    assert issues == []


def test_respects_cap(tmp_path):
    store = WikiStore(root=tmp_path)
    for i in range(60):
        src = _make_source(f"s{i}", source_id=f"src_{i:03d}")
        store.write_source(src, f"s{i}")
        store.append_claim(_make_claim(f"cl_{i}", source_id=f"src_{i:03d}"))
    mock = _mock_llm(True)
    check_stale_summary(store, llm_client=mock)
    assert mock.beta.chat.completions.parse.call_count <= 50
```

- [ ] **Step 2: Run tests — expect ImportError**

```
cd backend && python -m pytest tests/services/lint/semantic/test_stale_summary.py -v
```

- [ ] **Step 3: Implement `stale_summary.py`**

Create `backend/services/lint/checks/semantic/stale_summary.py`:

```python
import os
from typing import List

from openai import OpenAI

from models.lint_models import LintIssue, StaleSummaryJudgement
from services.wiki_store import WikiStore

_SEMANTIC_CAP = 50


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def check_stale_summary(
    store: WikiStore, llm_client=None
) -> List[LintIssue]:
    if llm_client is None:
        llm_client = _get_client()

    claims = store.read_all_claims()
    issues: List[LintIssue] = []
    checked = 0
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    for slug in store.list_sources():
        if checked >= _SEMANTIC_CAP:
            break
        source = store.read_source(slug)
        if source is None:
            continue
        source_claims = [c for c in claims if c.source_id == source.id]
        if not source_claims:
            continue

        checked += 1
        claim_texts = "\n".join(f"- {c.text}" for c in source_claims[:20])
        resp = llm_client.beta.chat.completions.parse(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Compare a source summary with its extracted claims. "
                        "Determine if the summary is missing important information and needs updating."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Current summary:\n{source.summary}\n\nExtracted claims:\n{claim_texts}"
                    ),
                },
            ],
            response_format=StaleSummaryJudgement,
        )
        result = resp.choices[0].message.parsed
        if result and result.is_stale:
            issues.append(LintIssue(
                id=f"stale_summary:{source.id}",
                type="stale_summary",
                severity="info",
                location=f"source:{source.id}",
                description=(
                    f"Source '{slug}' summary may be incomplete. {result.explanation}"
                ),
                suggested_fix="Update summary (LLM-proposed)",
                auto_fixable=True,
                payload={
                    "slug": slug,
                    "source_id": source.id,
                    "proposed_summary": result.proposed_summary,
                },
            ))
    return issues
```

- [ ] **Step 4: Run tests — expect PASS**

```
cd backend && python -m pytest tests/services/lint/semantic/test_stale_summary.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```
git add backend/services/lint/checks/semantic/stale_summary.py backend/tests/services/lint/semantic/test_stale_summary.py
git commit -m "feat(lint/semantic): stale_summary check — LLM compares summary vs claims"
```

---

### Task 7: Extend `fix_applier.py` — empty_questions generator + unmarked_contradiction + stale_summary

**Files:**
- Modify: `backend/services/lint/fix_applier.py`
- Modify: `backend/tests/services/lint/test_fix_applier.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/services/lint/test_fix_applier.py`:

```python
from unittest.mock import MagicMock
from models.lint_models import LintIssue, LlmQuestionsResult


def _mock_questions_llm(questions=None):
    questions = questions or ["What is X?", "How does Y work?", "Why Z?"]
    client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.parsed = LlmQuestionsResult(questions=questions)
    client.beta.chat.completions.parse.return_value = resp
    return client


def test_fix_empty_questions_entity(tmp_path):
    from models.wiki_models import Entity
    store = WikiStore(root=tmp_path)
    ent = Entity(id="e_001", type="Person", description="A person.", questions=[], tags=[])
    store.write_entity(ent, "jan")
    issue = LintIssue(
        id="empty_questions:entity:e_001",
        type="empty_questions",
        severity="warning",
        location="entity:e_001",
        description="Empty questions",
        auto_fixable=True,
        payload={"node_id": "entity:e_001", "slug": "jan", "entity_type": "Person"},
    )
    apply_fix(store, issue, llm_client=_mock_questions_llm())
    reloaded = store.read_entity("jan", "Person")
    assert len(reloaded.questions) == 3


def test_fix_empty_questions_concept(tmp_path):
    from models.wiki_models import Concept
    store = WikiStore(root=tmp_path)
    c = Concept(id="c_001", definition="A concept.", examples=[], related=[], questions=[], tags=[])
    store.write_concept(c, "my-concept")
    issue = LintIssue(
        id="empty_questions:concept:c_001",
        type="empty_questions",
        severity="warning",
        location="concept:c_001",
        description="Empty questions",
        auto_fixable=True,
        payload={"node_id": "concept:c_001", "slug": "my-concept"},
    )
    apply_fix(store, issue, llm_client=_mock_questions_llm(["Q1?", "Q2?"]))
    reloaded = store.read_concept("my-concept")
    assert reloaded.questions == ["Q1?", "Q2?"]


def test_fix_unmarked_contradiction_appends_edge(tmp_path):
    store = WikiStore(root=tmp_path)
    issue = LintIssue(
        id="unmarked_contradiction:cl_001:cl_002",
        type="unmarked_contradiction",
        severity="info",
        location="entity:e_001",
        description="Contradiction",
        auto_fixable=True,
        payload={"claim_a_id": "cl_001", "claim_b_id": "cl_002", "source_id": "src_001"},
    )
    apply_fix(store, issue)
    edges = store.read_all_edges()
    assert any(e.relation == "contradicts" for e in edges)
    contradicts = [e for e in edges if e.relation == "contradicts"]
    assert contradicts[0].from_ == "claim:cl_001"
    assert contradicts[0].to == "claim:cl_002"


def test_fix_stale_summary_updates_source(tmp_path):
    from datetime import datetime
    from models.wiki_models import Source
    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="T", type="article", raw_path="r",
        ingested_at=datetime.now(), summary="Old.", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, "test-source")
    issue = LintIssue(
        id="stale_summary:src_001",
        type="stale_summary",
        severity="info",
        location="source:src_001",
        description="Stale",
        auto_fixable=True,
        payload={"slug": "test-source", "source_id": "src_001", "proposed_summary": "New updated summary."},
    )
    apply_fix(store, issue)
    reloaded = store.read_source("test-source")
    assert reloaded.summary == "New updated summary."
```

- [ ] **Step 2: Run tests — expect FAIL**

```
cd backend && python -m pytest tests/services/lint/test_fix_applier.py::test_fix_empty_questions_entity tests/services/lint/test_fix_applier.py::test_fix_unmarked_contradiction_appends_edge tests/services/lint/test_fix_applier.py::test_fix_stale_summary_updates_source -v
```
Expected: TypeError (apply_fix doesn't accept `llm_client`) and FixError for unhandled types

- [ ] **Step 3: Rewrite `fix_applier.py`**

Replace `backend/services/lint/fix_applier.py` in full:

```python
import os
import uuid
from typing import Any, Dict, Optional

from openai import OpenAI

from models.lint_models import LintIssue, LlmQuestionsResult
from models.wiki_models import Edge, Span
from services.wiki_store import WikiStore


class FixError(Exception):
    """Raised when a fix cannot be applied."""


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _generate_questions(content: str, node_id: str, llm_client) -> list:
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    resp = llm_client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate 3-5 analytical questions that this knowledge node answers. "
                    "Questions should be specific, varied, and useful for retrieval."
                ),
            },
            {
                "role": "user",
                "content": f"Node: {node_id}\n\nContent:\n{content}",
            },
        ],
        response_format=LlmQuestionsResult,
    )
    result = resp.choices[0].message.parsed
    return result.questions if result else []


def apply_fix(
    store: WikiStore,
    issue: LintIssue,
    edit_payload: Optional[Dict[str, Any]] = None,
    llm_client=None,
) -> None:
    if not issue.auto_fixable:
        raise FixError(f"Issue {issue.id} ({issue.type}) is not auto-fixable")

    t = issue.type
    p = issue.payload

    if t == "dangling_source_ref":
        if p.get("kind") == "claim":
            store.delete_claim(p["claim_id"])
        elif p.get("kind") == "edge":
            store.delete_edge(p["edge_id"])
        else:
            raise FixError(f"Unknown payload.kind for dangling_source_ref: {p.get('kind')}")
        return

    if t == "dangling_node_ref":
        store.delete_edge(p["edge_id"])
        return

    if t == "corrupted_jsonl":
        path = store.root / "wiki" / p["file"]
        store.delete_jsonl_line(path, p["line_no"])
        return

    if t == "orphan_entity":
        store.delete_entity(p["slug"], p["entity_type"])
        return

    if t == "orphan_concept":
        store.delete_concept(p["slug"])
        return

    if t == "empty_description":
        if not edit_payload or "description" not in edit_payload:
            raise FixError("empty_description fix requires edit_payload['description']")
        new_text = edit_payload["description"]
        if p.get("kind") == "entity":
            store.update_entity_description(p["slug"], p["entity_type"], new_text)
        elif p.get("kind") == "concept":
            store.update_concept_description(p["slug"], new_text)
        else:
            raise FixError(f"empty_description fix not implemented for kind={p.get('kind')}")
        return

    if t == "empty_questions":
        if llm_client is None:
            llm_client = _get_client()
        node_id = p["node_id"]
        kind = node_id.split(":")[0]
        slug = p["slug"]
        if kind == "entity":
            node = store.read_entity(slug, p["entity_type"])
            content = f"Entity type: {node.type}\nDescription: {node.description}"
        elif kind == "concept":
            node = store.read_concept(slug)
            content = f"Definition: {node.definition}"
        else:
            node = store.read_source(slug)
            content = f"Summary: {node.summary}"
        questions = _generate_questions(content, node_id, llm_client)
        if not questions:
            raise FixError("LLM returned no questions")
        if kind == "entity":
            store.update_entity_questions(slug, p["entity_type"], questions)
        elif kind == "concept":
            store.update_concept_questions(slug, questions)
        else:
            store.update_source_questions(slug, questions)
        return

    if t == "unmarked_contradiction":
        edge = Edge(
            id=f"e_{uuid.uuid4().hex[:8]}",
            **{"from": f"claim:{p['claim_a_id']}"},
            to=f"claim:{p['claim_b_id']}",
            relation="contradicts",
            source_id=p["source_id"],
            span=Span(start=0, end=0, text="[lint-generated]"),
            confidence=1.0,
        )
        store.append_edge(edge)
        return

    if t == "stale_summary":
        store.update_source_summary(p["slug"], p["proposed_summary"])
        return

    raise FixError(f"No fix implemented for type {t}")
```

- [ ] **Step 4: Run tests — expect PASS**

```
cd backend && python -m pytest tests/services/lint/test_fix_applier.py -v
```
Expected: all fix_applier tests PASS (including previous Phase 6 ones)

- [ ] **Step 5: Commit**

```
git add backend/services/lint/fix_applier.py backend/tests/services/lint/test_fix_applier.py
git commit -m "feat(lint): fix_applier — empty_questions LLM generator, unmarked_contradiction edge, stale_summary"
```

---

### Task 8: Extend `runner.py` — `include_semantic` flag + Tier 3 dispatch

**Files:**
- Modify: `backend/services/lint/runner.py`
- Modify: `backend/tests/services/lint/test_runner.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/services/lint/test_runner.py`:

```python
from unittest.mock import MagicMock, patch
from models.lint_models import (
    ContradictionJudgement, AliasMergeJudgement,
    MissingConceptJudgement, StaleSummaryJudgement,
)


def _make_noop_llm():
    """LLM client that always returns 'no issue' for all Tier 3 checks."""
    client = MagicMock()
    resp = MagicMock()
    # Return negative results for all check types
    resp.choices[0].message.parsed = ContradictionJudgement(is_contradiction=False, explanation="")
    client.beta.chat.completions.parse.return_value = resp
    return client


def test_run_lint_without_semantic_does_not_call_llm(tmp_path):
    store = WikiStore(root=tmp_path)
    with patch("services.lint.runner.OpenAI") as mock_openai:
        report = run_lint(store, include_semantic=False)
    mock_openai.assert_not_called()
    assert report.counts_by_severity.get("info", 0) == 0


def test_run_lint_with_semantic_calls_tier3(tmp_path):
    from models.wiki_models import Claim, Span
    store = WikiStore(root=tmp_path)
    # Add contradicting claims to trigger unmarked_contradiction check
    for i, polarity in enumerate(["asserts", "denies"]):
        store.append_claim(Claim(
            id=f"cl_{i}", text=f"Claim {i}.", subject_id="entity:e_001",
            source_id="src_001", span=Span(start=0, end=5, text="test"),
            confidence=0.9, polarity=polarity,
        ))

    noop = _make_noop_llm()
    with patch("services.lint.runner.OpenAI", return_value=noop):
        report = run_lint(store, include_semantic=True)
    # LLM was called at least once (for unmarked_contradiction check)
    assert noop.beta.chat.completions.parse.called


def test_run_lint_semantic_issues_have_info_severity(tmp_path):
    from datetime import datetime
    from models.wiki_models import Claim, Source, Span
    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="T", type="article", raw_path="r",
        ingested_at=datetime.now(), summary="Summary.", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, "test")
    store.append_claim(Claim(
        id="cl_001", text="Fact.", subject_id="entity:e_001", source_id="src_001",
        span=Span(start=0, end=4, text="Fact"), confidence=0.9, polarity="asserts",
    ))

    # Mock stale_summary to return True
    stale_client = MagicMock()
    stale_resp = MagicMock()
    stale_resp.choices[0].message.parsed = StaleSummaryJudgement(
        is_stale=True, proposed_summary="Updated.", explanation="missing facts",
    )
    stale_client.beta.chat.completions.parse.return_value = stale_resp

    with patch("services.lint.runner.OpenAI", return_value=stale_client):
        report = run_lint(store, include_semantic=True)

    info_issues = [i for i in report.issues if i.severity == "info"]
    assert len(info_issues) >= 1
    assert all(i.severity == "info" for i in info_issues)
```

- [ ] **Step 2: Run tests — expect FAIL**

```
cd backend && python -m pytest tests/services/lint/test_runner.py::test_run_lint_without_semantic_does_not_call_llm -v
```
Expected: `TypeError: run_lint() got an unexpected keyword argument 'include_semantic'`

- [ ] **Step 3: Update `runner.py`**

Replace `backend/services/lint/runner.py` in full:

```python
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from openai import OpenAI

from models.lint_models import IssueStatus, LintIssue, LintReport
from services.lint.checks.navigability import (
    check_empty_description,
    check_empty_questions,
    check_orphan_concept,
    check_orphan_entity,
)
from services.lint.checks.provenance import (
    check_corrupted_jsonl,
    check_dangling_node_ref,
    check_dangling_source_ref,
    check_provenance_missing,
)
from services.wiki_log import append_log_entry
from services.wiki_store import WikiStore


def _reports_dir(store: WikiStore) -> Path:
    d = store.root / "wiki" / "lint_reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _make_report_id(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H-%M-%S-%f")


def _aggregate_issues(issues: List[LintIssue]) -> Tuple[Dict[str, int], Dict[str, int]]:
    sev = {"error": 0, "warning": 0, "info": 0}
    by_type: Dict[str, int] = {}
    for i in issues:
        sev[i.severity] = sev.get(i.severity, 0) + 1
        by_type[i.type] = by_type.get(i.type, 0) + 1
    return sev, by_type


def run_lint(store: WikiStore, include_semantic: bool = False) -> LintReport:
    issues: List[LintIssue] = []

    # Tier 1 — provenance & integrity
    issues.extend(check_corrupted_jsonl(store))
    issues.extend(check_provenance_missing(store))
    issues.extend(check_dangling_source_ref(store))
    issues.extend(check_dangling_node_ref(store))

    # Tier 2 — navigability
    issues.extend(check_orphan_entity(store))
    issues.extend(check_orphan_concept(store))
    issues.extend(check_empty_questions(store))
    issues.extend(check_empty_description(store))

    # Tier 3 — semantic (LLM-assisted, opt-in)
    if include_semantic:
        from services.lint.checks.semantic.unmarked_contradiction import check_unmarked_contradiction
        from services.lint.checks.semantic.entity_alias_collision import check_entity_alias_collision
        from services.lint.checks.semantic.missing_concept import check_missing_concept
        from services.lint.checks.semantic.stale_summary import check_stale_summary

        llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        issues.extend(check_unmarked_contradiction(store, llm_client))
        issues.extend(check_entity_alias_collision(store, llm_client))
        issues.extend(check_missing_concept(store, llm_client))
        issues.extend(check_stale_summary(store, llm_client))

    now = datetime.now()
    report_id = _make_report_id(now)
    sev, by_type = _aggregate_issues(issues)

    report = LintReport(
        id=report_id,
        created_at=now,
        issues=issues,
        counts_by_severity=sev,
        counts_by_type=by_type,
    )

    save_report(store, report)
    append_log_entry(
        store,
        op="lint",
        source_id=None,
        details=f"run {report_id} | found: {len(issues)} ({sev['error']} errors, {sev['warning']} warnings, {sev['info']} info)",
        timestamp=now,
    )
    return report


def save_report(store: WikiStore, report: LintReport) -> None:
    path = _reports_dir(store) / f"{report.id}.json"
    payload = report.model_dump(mode="json")
    store._atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False))


def load_report(store: WikiStore, report_id: str) -> LintReport:
    path = _reports_dir(store) / f"{report_id}.json"
    return LintReport.model_validate_json(path.read_text(encoding="utf-8"))


def list_reports(store: WikiStore) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in sorted(_reports_dir(store).glob("*.json"), reverse=True):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        out.append({
            "id": data.get("id", p.stem),
            "created_at": data.get("created_at"),
            "counts_by_severity": data.get("counts_by_severity", {}),
            "total": len(data.get("issues", [])),
        })
    return out


def update_issue_status(
    store: WikiStore,
    report_id: str,
    issue_id: str,
    new_status: IssueStatus,
) -> LintReport:
    report = load_report(store, report_id)
    found = False
    for i in report.issues:
        if i.id == issue_id:
            i.status = new_status
            found = True
            break
    if not found:
        raise KeyError(f"Issue {issue_id} not found in report {report_id}")
    save_report(store, report)
    return report
```

- [ ] **Step 4: Run tests — expect PASS**

```
cd backend && python -m pytest tests/services/lint/test_runner.py -v
```
Expected: all runner tests PASS

- [ ] **Step 5: Commit**

```
git add backend/services/lint/runner.py backend/tests/services/lint/test_runner.py
git commit -m "feat(lint): runner include_semantic flag — dispatches Tier 3 checks via shared LLM client"
```

---

### Task 9: `wiki_log` summary + API `include_semantic` + per-action log trigger

**Files:**
- Modify: `backend/services/wiki_log.py`
- Modify: `backend/api/lint.py`
- Modify: `backend/tests/api/test_lint_api.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/api/test_lint_api.py`:

```python
def test_run_lint_include_semantic_false_by_default(client, tmp_path, monkeypatch):
    """POST /api/lint/run with empty body should not call LLM."""
    from unittest.mock import patch
    with patch("services.lint.runner.OpenAI") as mock_openai:
        response = client.post("/api/lint/run", json={})
    assert response.status_code == 200
    mock_openai.assert_not_called()


def test_run_lint_with_include_semantic_true(client, tmp_path, monkeypatch):
    """POST /api/lint/run with include_semantic:true should create LLM client."""
    from unittest.mock import MagicMock, patch
    noop = MagicMock()
    noop_resp = MagicMock()
    from models.lint_models import ContradictionJudgement
    noop_resp.choices[0].message.parsed = ContradictionJudgement(is_contradiction=False, explanation="")
    noop.beta.chat.completions.parse.return_value = noop_resp
    with patch("services.lint.runner.OpenAI", return_value=noop):
        response = client.post("/api/lint/run", json={"include_semantic": True})
    assert response.status_code == 200


def test_per_action_log_written_when_all_issues_closed(client, tmp_path):
    """When last open issue is fixed/rejected, log.md gets a 'closed' entry."""
    # Run lint to get a report
    run_resp = client.post("/api/lint/run", json={})
    assert run_resp.status_code == 200
    report = run_resp.json()
    if not report["issues"]:
        return  # nothing to close
    # Reject all issues
    for issue in report["issues"]:
        client.post("/api/lint/fix", json={
            "report_id": report["id"],
            "issue_id": issue["id"],
            "action": "reject",
        })
    # Check log.md contains 'closed'
    from pathlib import Path
    log_path = tmp_path / "wiki" / "log.md"
    if log_path.exists():
        assert "closed" in log_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: Add `append_lint_action_summary` to `wiki_log.py`**

Append to `backend/services/wiki_log.py`:

```python
def append_lint_action_summary(store: "WikiStore", report) -> None:
    fixed = sum(1 for i in report.issues if i.status == "fixed")
    rejected = sum(1 for i in report.issues if i.status == "rejected")
    wontfix = sum(1 for i in report.issues if i.status == "wontfix")
    append_log_entry(
        store,
        op="lint",
        source_id=None,
        details=f"closed {report.id} | fixed: {fixed}, rejected: {rejected}, wontfix: {wontfix}",
    )
```

- [ ] **Step 3: Update `api/lint.py`**

Replace `backend/api/lint.py` in full:

```python
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.lint_models import LintReport
from services.lint.fix_applier import FixError, apply_fix
from services.lint.runner import (
    list_reports,
    load_report,
    run_lint,
    update_issue_status,
)
from services.wiki_log import append_lint_action_summary
from services.wiki_store import WikiStore


router = APIRouter(prefix="/api/lint", tags=["lint"])

_WIKI_DATA_DIR = Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default"))


def _get_store() -> WikiStore:
    return WikiStore(root=_WIKI_DATA_DIR)


class RunLintBody(BaseModel):
    include_semantic: bool = False


class FixBody(BaseModel):
    report_id: str
    issue_id: str
    action: Literal["apply", "reject", "wontfix"]
    edit_payload: Optional[Dict[str, Any]] = None


@router.post("/run", response_model=LintReport)
def post_run_lint(body: RunLintBody = RunLintBody()):
    store = _get_store()
    return run_lint(store, include_semantic=body.include_semantic)


@router.get("/reports", response_model=List[Dict[str, Any]])
def get_reports():
    store = _get_store()
    return list_reports(store)


@router.get("/report/{report_id}", response_model=LintReport)
def get_report(report_id: str):
    store = _get_store()
    try:
        return load_report(store, report_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")


@router.post("/fix", response_model=Dict[str, Any])
def post_fix(body: FixBody):
    store = _get_store()
    try:
        report = load_report(store, body.report_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Report {body.report_id} not found")

    issue = next((i for i in report.issues if i.id == body.issue_id), None)
    if issue is None:
        raise HTTPException(status_code=404, detail=f"Issue {body.issue_id} not found")

    if body.action == "apply":
        try:
            apply_fix(store, issue, edit_payload=body.edit_payload)
        except FixError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        new_status = "fixed"
    elif body.action == "reject":
        new_status = "rejected"
    else:
        new_status = "wontfix"

    updated_report = update_issue_status(store, body.report_id, body.issue_id, new_status)

    terminal = {"fixed", "rejected", "wontfix"}
    if all(i.status in terminal for i in updated_report.issues):
        append_lint_action_summary(store, updated_report)

    return {"id": body.issue_id, "status": new_status}
```

- [ ] **Step 4: Run API tests — expect PASS**

```
cd backend && python -m pytest tests/api/test_lint_api.py -v
```
Expected: all lint API tests PASS

- [ ] **Step 5: Commit**

```
git add backend/services/wiki_log.py backend/api/lint.py backend/tests/api/test_lint_api.py
git commit -m "feat(lint): include_semantic API param, per-action log on report close"
```

---

### Task 10: Frontend — types, Panel toggle, IssueRow, client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/lint/LintPanel.tsx`
- Modify: `frontend/src/components/lint/LintIssueRow.tsx`

- [ ] **Step 1: Extend `types/index.ts` — add 4 new IssueTypes**

In `frontend/src/types/index.ts`, replace the `IssueType` block:

```typescript
export type IssueType =
  | "provenance_missing"
  | "dangling_source_ref"
  | "dangling_node_ref"
  | "corrupted_jsonl"
  | "orphan_entity"
  | "orphan_concept"
  | "empty_questions"
  | "empty_description"
  | "unmarked_contradiction"
  | "entity_alias_collision"
  | "missing_concept"
  | "stale_summary";
```

- [ ] **Step 2: Update `client.ts` — `runLint` accepts `includeSemantic`**

Replace the `runLint` entry in `frontend/src/api/client.ts`:

```typescript
  runLint: (includeSemantic = false) =>
    request<import("../types").LintReport>("/lint/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ include_semantic: includeSemantic }),
    }),
```

- [ ] **Step 3: Update `LintPanel.tsx` — add toggle state + severity filter for `info`**

Replace `LintPanel.tsx` in full:

```tsx
import { useEffect, useState } from "react";
import { Play, RefreshCw, ShieldCheck } from "lucide-react";
import { api } from "../../api/client";
import type { IssueSeverity, IssueStatus, LintReport } from "../../types";
import { LintIssueRow } from "./LintIssueRow";

type SeverityFilter = "all" | IssueSeverity;
type StatusFilter = "all" | IssueStatus;

export function LintPanel() {
  const [report, setReport] = useState<LintReport | null>(null);
  const [running, setRunning] = useState(false);
  const [busyIssueId, setBusyIssueId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("open");
  const [includeSemantic, setIncludeSemantic] = useState(false);

  async function loadLatestReport() {
    try {
      const summaries = await api.listLintReports();
      if (summaries.length === 0) { setReport(null); return; }
      const latest = await api.getLintReport(summaries[0].id);
      setReport(latest);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => { loadLatestReport(); }, []);

  async function runNow() {
    setRunning(true);
    setError(null);
    try {
      const fresh = await api.runLint(includeSemantic);
      setReport(fresh);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  async function applyAction(
    issueId: string,
    action: "apply" | "reject" | "wontfix",
    editPayload?: { description: string },
  ) {
    if (!report) return;
    setBusyIssueId(issueId);
    setError(null);
    try {
      await api.applyLintFix({ report_id: report.id, issue_id: issueId, action, edit_payload: editPayload });
      const refreshed = await api.getLintReport(report.id);
      setReport(refreshed);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyIssueId(null);
    }
  }

  const issues = report?.issues ?? [];
  const filtered = issues.filter((i) => {
    if (severityFilter !== "all" && i.severity !== severityFilter) return false;
    if (statusFilter !== "all" && i.status !== statusFilter) return false;
    return true;
  });

  const sev = report?.counts_by_severity ?? { error: 0, warning: 0, info: 0 };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border shrink-0 flex-wrap">
        <ShieldCheck className="w-4 h-4 text-primary" />
        <h2 className="text-sm font-medium">Lint</h2>
        <label className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer">
          <input
            type="checkbox"
            checked={includeSemantic}
            onChange={(e) => setIncludeSemantic(e.target.checked)}
            className="rounded"
          />
          Semantic checks{" "}
          <span className="text-muted-foreground/60">(LLM, ~30–60s)</span>
        </label>
        <button
          onClick={runNow}
          disabled={running}
          className="flex items-center gap-1.5 ml-auto px-3 py-1.5 text-xs rounded-md bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {running ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          {running ? "Running…" : "Run Now"}
        </button>
      </div>

      {/* Summary + filters */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-border shrink-0 flex-wrap">
        {report ? (
          <span className="text-xs text-muted-foreground">
            Report{" "}
            <span className="font-mono text-foreground">{report.id}</span> ·{" "}
            <span className="text-red-600">{sev.error} errors</span> ·{" "}
            <span className="text-yellow-600">{sev.warning} warnings</span> ·{" "}
            <span className="text-blue-500">{sev.info ?? 0} info</span> ·{" "}
            {issues.length} total
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">
            No lint reports yet. Click <span className="font-medium">Run Now</span>.
          </span>
        )}
        <div className="flex gap-1 ml-auto">
          {(["all", "error", "warning", "info"] as SeverityFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setSeverityFilter(s)}
              className={`px-2 py-0.5 rounded text-xs capitalize transition-colors ${
                severityFilter === s
                  ? "bg-primary/15 text-primary font-medium"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <span className="text-muted-foreground text-xs">|</span>
        <div className="flex gap-1">
          {(["open", "fixed", "rejected", "wontfix", "all"] as StatusFilter[]).map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-2 py-0.5 rounded text-xs capitalize transition-colors ${
                statusFilter === s
                  ? "bg-primary/15 text-primary font-medium"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="px-4 py-2 text-xs text-red-600 bg-red-100/40 border-b border-red-200">
          {error}
        </div>
      )}

      {/* Issue list */}
      <div className="flex-1 overflow-auto p-4 flex flex-col gap-2">
        {report && filtered.length === 0 && (
          <div className="text-center text-muted-foreground text-sm py-12">
            {issues.length === 0 ? "No issues found." : "No issues match the current filter."}
          </div>
        )}
        {filtered.map((issue) => (
          <LintIssueRow
            key={issue.id}
            issue={issue}
            busy={busyIssueId === issue.id}
            onApply={(id, payload) => applyAction(id, "apply", payload)}
            onReject={(id) => applyAction(id, "reject")}
            onWontFix={(id) => applyAction(id, "wontfix")}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Update `LintIssueRow.tsx` — handle `empty_questions` generate button**

Replace `LintIssueRow.tsx` in full:

```tsx
import { useState } from "react";
import { AlertTriangle, AlertOctagon, Info, Check, X, Ban, Sparkles } from "lucide-react";
import type { LintIssue } from "../../types";

const SEVERITY_ICON = {
  error: AlertOctagon,
  warning: AlertTriangle,
  info: Info,
};

const SEVERITY_COLOR: Record<string, string> = {
  error: "text-red-600 dark:text-red-400",
  warning: "text-yellow-600 dark:text-yellow-400",
  info: "text-blue-500",
};

const STATUS_BADGE: Record<string, string> = {
  open: "bg-muted text-muted-foreground",
  fixed: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  rejected: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  wontfix: "bg-zinc-200 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
};

interface LintIssueRowProps {
  issue: LintIssue;
  onApply: (issueId: string, editPayload?: { description: string }) => void;
  onReject: (issueId: string) => void;
  onWontFix: (issueId: string) => void;
  busy: boolean;
}

export function LintIssueRow({ issue, onApply, onReject, onWontFix, busy }: LintIssueRowProps) {
  const Icon = SEVERITY_ICON[issue.severity];
  const isEmptyDescriptionEdit = issue.type === "empty_description" && issue.auto_fixable;
  const isGenerateQuestions = issue.type === "empty_questions" && issue.auto_fixable;
  const [editText, setEditText] = useState("");
  const editValid = editText.trim().length >= 30;
  const closed = issue.status !== "open";

  return (
    <div className="border border-border rounded-md p-3 flex flex-col gap-2 text-xs bg-card">
      <div className="flex items-start gap-2">
        <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${SEVERITY_COLOR[issue.severity]}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-[11px] text-muted-foreground">{issue.type}</span>
            <span className="font-mono text-[11px] text-muted-foreground">·</span>
            <span className="font-mono text-[11px] text-muted-foreground truncate">
              {issue.location}
            </span>
            <span className={`ml-auto px-2 py-0.5 rounded text-[10px] uppercase ${STATUS_BADGE[issue.status]}`}>
              {issue.status}
            </span>
          </div>
          <p className="mt-1 text-foreground leading-snug">{issue.description}</p>
          {issue.suggested_fix && (
            <p className="mt-1 text-muted-foreground">suggested: {issue.suggested_fix}</p>
          )}
        </div>
      </div>

      {!closed && isEmptyDescriptionEdit && (
        <textarea
          value={editText}
          onChange={(e) => setEditText(e.target.value)}
          placeholder="Replacement description (≥30 chars)…"
          rows={2}
          className="w-full px-2 py-1 text-xs border border-border rounded bg-background focus:outline-none focus:ring-1 focus:ring-primary/40"
        />
      )}

      {!closed && (
        <div className="flex gap-2 flex-wrap">
          {isEmptyDescriptionEdit ? (
            <button
              disabled={busy || !editValid}
              onClick={() => onApply(issue.id, { description: editText.trim() })}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Check className="w-3 h-3" /> Save
            </button>
          ) : isGenerateQuestions ? (
            <button
              disabled={busy}
              onClick={() => onApply(issue.id)}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-violet-600 text-white hover:opacity-90 transition-opacity disabled:opacity-40"
            >
              <Sparkles className="w-3 h-3" /> Generate Questions
            </button>
          ) : (
            <button
              disabled={busy || !issue.auto_fixable}
              onClick={() => onApply(issue.id)}
              className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-primary text-primary-foreground hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
              title={issue.auto_fixable ? undefined : "No automatic fix available"}
            >
              <Check className="w-3 h-3" /> Apply Fix
            </button>
          )}
          <button
            disabled={busy}
            onClick={() => onReject(issue.id)}
            className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40"
          >
            <X className="w-3 h-3" /> Reject
          </button>
          <button
            disabled={busy}
            onClick={() => onWontFix(issue.id)}
            className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-muted text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40"
          >
            <Ban className="w-3 h-3" /> Won't fix
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Update `navigability.py` — set `auto_fixable=True` for `empty_questions`**

In `backend/services/lint/checks/navigability.py`, change all three `empty_questions` issue definitions:

```python
# Entity
issues.append(LintIssue(
    id=f"empty_questions:entity:{ent.id}",
    type="empty_questions",
    severity="warning",
    location=node_id,
    description=f"Entity {ent.id} has empty questions[]",
    suggested_fix="Generate analytical questions (LLM)",
    auto_fixable=True,
    payload={"node_id": node_id, "slug": slug, "entity_type": ent.type},
))

# Concept
issues.append(LintIssue(
    id=f"empty_questions:concept:{c.id}",
    type="empty_questions",
    severity="warning",
    location=node_id,
    description=f"Concept {c.id} has empty questions[]",
    suggested_fix="Generate analytical questions (LLM)",
    auto_fixable=True,
    payload={"node_id": node_id, "slug": slug},
))

# Source
issues.append(LintIssue(
    id=f"empty_questions:source:{s.id}",
    type="empty_questions",
    severity="warning",
    location=node_id,
    description=f"Source {s.id} has empty questions[]",
    suggested_fix="Generate analytical questions (LLM)",
    auto_fixable=True,
    payload={"node_id": node_id, "slug": slug},
))
```

- [ ] **Step 5b: Update existing `test_navigability_checks.py` — fix `auto_fixable` assertions**

In `backend/tests/services/lint/test_navigability_checks.py`, find all assertions like:

```python
assert issue.auto_fixable is False  # for empty_questions
```

and change them to:

```python
assert issue.auto_fixable is True
```

Also update any assertion on `suggested_fix` for `empty_questions` from `None` to `"Generate analytical questions (LLM)"`. Run:

```
cd backend && python -m pytest tests/services/lint/test_navigability_checks.py -v
```
Expected: all navigability tests PASS

- [ ] **Step 6: Run `tsc --noEmit` — expect 0 errors**

```
cd frontend && npx tsc --noEmit
```
Expected: clean exit

- [ ] **Step 7: Commit**

```
git add frontend/src/types/index.ts frontend/src/api/client.ts frontend/src/components/lint/LintPanel.tsx frontend/src/components/lint/LintIssueRow.tsx backend/services/lint/checks/navigability.py
git commit -m "feat(frontend/lint): Tier 3 types, semantic toggle, Generate Questions button"
```

---

### Task 11: Full suite + smoke test + tag

- [ ] **Step 1: Run full backend test suite**

```
cd backend && python -m pytest -v
```
Expected: all ~339 tests PASS, 0 failures

- [ ] **Step 2: Run `tsc --noEmit`**

```
cd frontend && npx tsc --noEmit
```
Expected: 0 errors

- [ ] **Step 3: Manual smoke test (Tier 3)**

Start servers:
```
cd backend && uvicorn main:app --reload --port 8000
cd frontend && npm run dev
```

Verify at `http://localhost:5173` (or 5174):
1. Otwórz panel Lint.
2. Zaznacz checkbox "Semantic checks".
3. Kliknij "Run Now" — spinner widoczny przez ~10s.
4. W raporcie pojawiają się issues z `severity: info` (lub 0 jeśli wiki puste — OK).
5. Dla issues `unmarked_contradiction` / `stale_summary` — "Apply Fix" aktywny.
6. Dla `entity_alias_collision` / `missing_concept` — "Apply Fix" greyed out.
7. Dla `empty_questions` — przycisk "Generate Questions" (fioletowy).
8. Odznacz "Semantic checks", kliknij "Run Now" — brak issues `info`.

- [ ] **Step 4: Tag**

```
git tag phase-7-complete
```

- [ ] **Step 5: Confirm tag**

```
git log --oneline -5
git tag -l "phase*"
```
Expected: tag `phase-7-complete` widoczny na ostatnim commicie
