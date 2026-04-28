# Phase 1: Data Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the file-backed knowledge map data layer (Pydantic models, file I/O, index/log management, conventions document, sample fixtures) as the foundation for Phases 2–9.

**Architecture:** Wiki state lives on disk as mixed Markdown (narrative pages with YAML frontmatter) and JSONL (structured claims/edges). A `wiki_store` service handles atomic file I/O; `wiki_index` regenerates `index.md`/`index.json` after every mutation; `wiki_log` appends timestamped entries. Slugs are deterministic (lowercase, hyphenated, ASCII-folded) and unique per layer. All file writes use tmp-file + rename for atomicity.

**Tech Stack:** Python 3.9+, Pydantic v2, python-frontmatter (YAML+MD parser), pytest, pathlib (no DB).

**Spec:** `docs/superpowers/specs/2026-04-27-knowledge-map-rag-design.md`

---

## Roadmap (all 9 phases)

This plan covers **Phase 1** only. Phases 2–9 will each get their own plan once the previous phase ships.

| Phase | Scope | Status |
|---|---|---|
| **1. Data Layer** | wiki_store, wiki_index, wiki_log, models, conventions, fixtures | **THIS PLAN** |
| 2. Ingest | source_classifier (Stage 2 LLM), conflict_detector, 5-stage pipeline, Sources + Ingest Pipeline panels | TBD |
| 3. Retrieval | Stages 1–5 (intent_parser, candidate_filter, selection, context_assembly, answer_generator), Chat with Trace, basic Knowledge Map (Browser), Index & Log panel | TBD |
| 4. Agent fallback | 10-tool agent loop, fallback triggers, trace integration | TBD |
| 5. Graph view | Knowledge Map → Graph tab (react-flow), filters, NodeDetailDrawer | TBD |
| 6. Lint Tier 1+2 | provenance/integrity/navigability checks + Lint panel | TBD |
| 7. Lint Tier 3 | semantic checks (LLM-assisted) | TBD |
| 8. Tutorial rewrite | 6 sections, interactive walkthroughs | TBD |
| 9. Cleanup | remove dead code (chunkers/embeddings/vector_store), update README, migration notes | TBD |

---

## File Structure (Phase 1)

**Create:**
- `backend/wiki_data/.example/raw/.gitkeep`
- `backend/wiki_data/.example/wiki/.gitkeep`
- `backend/schema/KNOWLEDGE_MAP.md`
- `backend/services/_slug.py`
- `backend/services/wiki_store.py`
- `backend/services/wiki_index.py`
- `backend/services/wiki_log.py`
- `backend/models/wiki_models.py`
- `backend/tests/services/__init__.py`
- `backend/tests/services/test_slug.py`
- `backend/tests/services/test_wiki_store.py`
- `backend/tests/services/test_wiki_index.py`
- `backend/tests/services/test_wiki_log.py`
- `backend/tests/services/test_integration_round_trip.py`
- `backend/tests/fixtures/sample_sources/source_a.md`
- `backend/tests/fixtures/sample_sources/source_b.md`
- `backend/tests/fixtures/sample_sources/source_c.md`
- `backend/tests/fixtures/golden_vault/` (committed expected state)

**Modify:**
- `.gitignore` — add `backend/wiki_data/` (except `.example/`)
- `backend/requirements.txt` — add `python-frontmatter`, pin `pydantic>=2`

---

## Task 1: Setup directories, gitignore, dependencies

**Files:**
- Create: `backend/wiki_data/.example/raw/.gitkeep`, `backend/wiki_data/.example/wiki/.gitkeep`, `backend/schema/.gitkeep`
- Modify: `.gitignore`, `backend/requirements.txt`

- [ ] **Step 1: Add wiki_data to .gitignore (keeping .example tracked)**

Append to `.gitignore`:

```
# Knowledge map data — gitignored, except bundled .example/
backend/wiki_data/*
!backend/wiki_data/.example/
!backend/wiki_data/.example/**
```

- [ ] **Step 2: Create directory placeholders**

```bash
mkdir -p backend/wiki_data/.example/raw backend/wiki_data/.example/wiki backend/schema
touch backend/wiki_data/.example/raw/.gitkeep backend/wiki_data/.example/wiki/.gitkeep backend/schema/.gitkeep
```

- [ ] **Step 3: Add dependencies**

Append to `backend/requirements.txt`:

```
python-frontmatter==1.1.0
pydantic>=2.5.0
```

- [ ] **Step 4: Install and verify**

```bash
cd backend && pip install -r requirements.txt && python -c "import frontmatter; from pydantic import BaseModel; print('ok')"
```

Expected output: `ok`

- [ ] **Step 5: Commit**

```bash
git add .gitignore backend/wiki_data/.example/ backend/schema/.gitkeep backend/requirements.txt
git commit -m "chore: scaffold wiki_data and schema dirs, add deps"
```

---

## Task 2: Slug utility

**Files:**
- Create: `backend/services/_slug.py`, `backend/tests/services/__init__.py`, `backend/tests/services/test_slug.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/__init__.py` (empty file).

Create `backend/tests/services/test_slug.py`:

```python
import pytest
from services._slug import slugify, ensure_unique


def test_slugify_lowercase_hyphenated():
    assert slugify("Hello World") == "hello-world"


def test_slugify_strips_diacritics():
    assert slugify("Łazienka — sypialnia") == "lazienka-sypialnia"


def test_slugify_collapses_whitespace():
    assert slugify("  multiple   spaces  ") == "multiple-spaces"


def test_slugify_strips_punctuation():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_preserves_digits():
    assert slugify("Q1 2023 Report") == "q1-2023-report"


def test_slugify_empty_input_raises():
    with pytest.raises(ValueError):
        slugify("")


def test_ensure_unique_appends_suffix_if_taken():
    assert ensure_unique("foo", existing={"foo", "foo-2"}) == "foo-3"


def test_ensure_unique_returns_same_if_free():
    assert ensure_unique("foo", existing={"bar"}) == "foo"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/test_slug.py -v
```

Expected: ImportError or 7 failures (module not found).

- [ ] **Step 3: Implement slug utility**

Create `backend/services/_slug.py`:

```python
import re
import unicodedata


def slugify(text: str) -> str:
    if not text or not text.strip():
        raise ValueError("Cannot slugify empty string")

    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_only.lower()
    cleaned = re.sub(r"[^a-z0-9\s-]", "", lowered)
    collapsed = re.sub(r"[\s-]+", "-", cleaned).strip("-")

    if not collapsed:
        raise ValueError(f"Slugification of {text!r} produced empty result")
    return collapsed


def ensure_unique(slug: str, existing: set[str]) -> str:
    if slug not in existing:
        return slug
    n = 2
    while f"{slug}-{n}" in existing:
        n += 1
    return f"{slug}-{n}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/test_slug.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/_slug.py backend/tests/services/__init__.py backend/tests/services/test_slug.py
git commit -m "feat(slug): deterministic slug generation with uniqueness helper"
```

---

## Task 3: Pydantic models for the 4 wiki layers + Edge

**Files:**
- Create: `backend/models/wiki_models.py`
- Create: `backend/tests/services/test_wiki_models.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/test_wiki_models.py`:

```python
import pytest
from datetime import datetime
from models.wiki_models import (
    Source, Entity, Concept, Claim, Edge,
    EntityType, RelationType, Polarity, Span
)


def test_source_minimal_valid():
    src = Source(
        id="src_001",
        title="Skandynawska sypialnia",
        type="article",
        raw_path="raw/skandynawska-sypialnia/parsed.md",
        ingested_at=datetime(2026, 4, 28, 10, 0, 0),
        summary="Krótkie streszczenie.",
        key_takeaways=["pkt 1"],
        questions=["jakie kolory?"],
        tags=["sypialnia"],
    )
    assert src.id == "src_001"


def test_entity_requires_valid_type():
    with pytest.raises(ValueError):
        Entity(id="e_001", type="UnknownType", description="x", questions=[], tags=[])


def test_entity_aliases_default_empty():
    e = Entity(id="e_001", type="Person", description="x", questions=[], tags=[])
    assert e.aliases == []


def test_concept_parent_optional():
    c = Concept(id="c_001", definition="def", examples=[], related=[], questions=[], tags=[])
    assert c.parent_concept is None


def test_claim_polarity_valid():
    span = Span(start=10, end=42, text="excerpt")
    cl = Claim(
        id="cl_001", text="X is Y", subject_id="entity:e_001",
        source_id="src_001", span=span, confidence=0.9, polarity="asserts"
    )
    assert cl.polarity == "asserts"


def test_claim_polarity_invalid_rejected():
    span = Span(start=0, end=10, text="x")
    with pytest.raises(ValueError):
        Claim(id="cl_001", text="X", subject_id="entity:e_001",
              source_id="src_001", span=span, confidence=0.5, polarity="maybe")


def test_claim_confidence_bounds():
    span = Span(start=0, end=10, text="x")
    with pytest.raises(ValueError):
        Claim(id="cl_001", text="X", subject_id="entity:e_001",
              source_id="src_001", span=span, confidence=1.5, polarity="asserts")


def test_edge_relation_must_be_in_closed_list():
    span = Span(start=0, end=10, text="x")
    with pytest.raises(ValueError):
        Edge(id="ed_001", from_="entity:a", to="entity:b",
             relation="randomly_invented", source_id="src_001",
             span=span, confidence=0.8)


def test_edge_with_valid_relation():
    span = Span(start=0, end=10, text="x")
    ed = Edge(id="ed_001", from_="entity:a", to="concept:c1",
              relation="associated_with", source_id="src_001",
              span=span, confidence=0.8)
    assert ed.relation == "associated_with"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/test_wiki_models.py -v
```

Expected: ImportError (module not found).

- [ ] **Step 3: Implement models**

Create `backend/models/wiki_models.py`:

```python
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


EntityType = Literal["Person", "Org", "Product", "Place", "Event"]

RelationType = Literal[
    "mentions", "defines", "contradicts", "supports", "derives_from",
    "instance_of", "part_of", "associated_with", "causes", "precedes",
]

Polarity = Literal["asserts", "denies"]


class Span(BaseModel):
    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)
    text: str


class Source(BaseModel):
    id: str
    title: str
    type: str
    raw_path: str
    ingested_at: datetime
    source_url: Optional[str] = None
    summary: str
    key_takeaways: List[str]
    questions: List[str]
    tags: List[str]


class Entity(BaseModel):
    id: str
    type: EntityType
    aliases: List[str] = Field(default_factory=list)
    description: str
    mentions_count: int = 0
    questions: List[str]
    tags: List[str]


class Concept(BaseModel):
    id: str
    parent_concept: Optional[str] = None
    definition: str
    examples: List[str]
    related: List[str]
    questions: List[str]
    tags: List[str]


class Claim(BaseModel):
    id: str
    text: str
    subject_id: str
    source_id: str
    span: Span
    confidence: float = Field(..., ge=0.0, le=1.0)
    polarity: Polarity
    related_claim_ids: List[str] = Field(default_factory=list)


class Edge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_: str = Field(..., alias="from")
    to: str
    relation: RelationType
    source_id: str
    span: Span
    confidence: float = Field(..., ge=0.0, le=1.0)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/test_wiki_models.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/models/wiki_models.py backend/tests/services/test_wiki_models.py
git commit -m "feat(models): wiki layer Pydantic models (Source/Entity/Concept/Claim/Edge)"
```

---

## Task 4: wiki_store — read operations

**Files:**
- Create: `backend/services/wiki_store.py`
- Create: `backend/tests/services/test_wiki_store.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/test_wiki_store.py`:

```python
import pytest
from datetime import datetime
from pathlib import Path
from services.wiki_store import WikiStore
from models.wiki_models import Source, Entity, Concept, Claim, Edge, Span


@pytest.fixture
def store(tmp_path):
    return WikiStore(root=tmp_path)


@pytest.fixture
def sample_source():
    return Source(
        id="src_001",
        title="Skandynawska sypialnia",
        type="article",
        raw_path="raw/skandynawska-sypialnia/parsed.md",
        ingested_at=datetime(2026, 4, 28, 10, 0, 0),
        summary="Krótkie streszczenie.",
        key_takeaways=["pkt 1", "pkt 2"],
        questions=["jakie kolory są typowe?"],
        tags=["sypialnia", "skandynawia"],
    )


def test_read_missing_source_returns_none(store):
    assert store.read_source("nonexistent") is None


def test_read_source_after_write(store, sample_source):
    store.write_source(sample_source, slug="skandynawska-sypialnia")
    loaded = store.read_source("skandynawska-sypialnia")
    assert loaded.id == sample_source.id
    assert loaded.title == sample_source.title
    assert loaded.questions == sample_source.questions


def test_list_sources_empty(store):
    assert store.list_sources() == []


def test_list_sources_after_writes(store, sample_source):
    store.write_source(sample_source, slug="a")
    other = sample_source.model_copy(update={"id": "src_002", "title": "B"})
    store.write_source(other, slug="b")
    slugs = store.list_sources()
    assert sorted(slugs) == ["a", "b"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/test_wiki_store.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement initial wiki_store with read + write_source (minimal to pass tests)**

Create `backend/services/wiki_store.py`:

```python
from pathlib import Path
from typing import List, Optional
import frontmatter
from models.wiki_models import Source, Entity, Concept, Claim, Edge


SOURCES_DIR = "30-Sources"
ENTITIES_DIR = "20-Entities"
CONCEPTS_DIR = "10-Concepts"
INDEX_DIR = "00-Index"


class WikiStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        (self.root / "wiki" / SOURCES_DIR).mkdir(parents=True, exist_ok=True)
        (self.root / "wiki" / ENTITIES_DIR).mkdir(parents=True, exist_ok=True)
        (self.root / "wiki" / CONCEPTS_DIR).mkdir(parents=True, exist_ok=True)
        (self.root / "wiki" / INDEX_DIR).mkdir(parents=True, exist_ok=True)
        (self.root / "raw").mkdir(parents=True, exist_ok=True)

    def _source_path(self, slug: str) -> Path:
        return self.root / "wiki" / SOURCES_DIR / f"{slug}.md"

    def write_source(self, source: Source, slug: str) -> None:
        path = self._source_path(slug)
        body = source.summary
        post = frontmatter.Post(content=body, **self._source_frontmatter(source))
        self._atomic_write(path, frontmatter.dumps(post))

    def read_source(self, slug: str) -> Optional[Source]:
        path = self._source_path(slug)
        if not path.exists():
            return None
        post = frontmatter.load(path)
        return Source(
            id=post["id"],
            title=post["title"],
            type=post["type"],
            raw_path=post["raw_path"],
            ingested_at=post["ingested_at"],
            source_url=post.get("source_url"),
            summary=post.content.strip(),
            key_takeaways=post.get("key_takeaways", []),
            questions=post.get("questions", []),
            tags=post.get("tags", []),
        )

    def list_sources(self) -> List[str]:
        d = self.root / "wiki" / SOURCES_DIR
        return [p.stem for p in d.glob("*.md")]

    def _source_frontmatter(self, source: Source) -> dict:
        return {
            "id": source.id,
            "title": source.title,
            "type": source.type,
            "raw_path": source.raw_path,
            "ingested_at": source.ingested_at.isoformat(),
            "source_url": source.source_url,
            "key_takeaways": source.key_takeaways,
            "questions": source.questions,
            "tags": source.tags,
        }

    def _atomic_write(self, path: Path, content: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/test_wiki_store.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/wiki_store.py backend/tests/services/test_wiki_store.py
git commit -m "feat(wiki_store): atomic source read/write/list with YAML frontmatter"
```

---

## Task 5: wiki_store — entity, concept, claim, edge writers

**Files:**
- Modify: `backend/services/wiki_store.py`
- Modify: `backend/tests/services/test_wiki_store.py`

- [ ] **Step 1: Add failing tests**

Append to `backend/tests/services/test_wiki_store.py`:

```python
@pytest.fixture
def sample_entity():
    return Entity(
        id="e_001", type="Place", aliases=["bedroom"],
        description="Sypialnia.", mentions_count=3,
        questions=["jakie kolory?"], tags=["pomieszczenie"]
    )


@pytest.fixture
def sample_concept():
    return Concept(
        id="c_001", parent_concept=None, definition="Neutralna kolorystyka.",
        examples=["beż", "biel"], related=["minimalizm"],
        questions=["jakie odcienie?"], tags=["kolory"]
    )


@pytest.fixture
def sample_claim():
    return Claim(
        id="cl_001", text="Sypialnia używa kolorów neutralnych.",
        subject_id="entity:e_001", source_id="src_001",
        span=Span(start=100, end=160, text="..."),
        confidence=0.92, polarity="asserts",
    )


@pytest.fixture
def sample_edge():
    return Edge(
        id="ed_001", **{"from": "entity:e_001"}, to="concept:c_001",
        relation="associated_with", source_id="src_001",
        span=Span(start=200, end=260, text="..."), confidence=0.88,
    )


def test_write_and_read_entity(store, sample_entity):
    store.write_entity(sample_entity, slug="sypialnia")
    loaded = store.read_entity(slug="sypialnia", entity_type="Place")
    assert loaded.id == sample_entity.id
    assert loaded.aliases == ["bedroom"]


def test_write_and_read_concept(store, sample_concept):
    store.write_concept(sample_concept, slug="kolory-neutralne")
    loaded = store.read_concept("kolory-neutralne")
    assert loaded.examples == ["beż", "biel"]


def test_append_claim_and_read_back(store, sample_claim):
    store.append_claim(sample_claim)
    claims = store.read_all_claims()
    assert len(claims) == 1
    assert claims[0].text == sample_claim.text


def test_append_multiple_claims(store, sample_claim):
    store.append_claim(sample_claim)
    second = sample_claim.model_copy(update={"id": "cl_002"})
    store.append_claim(second)
    assert len(store.read_all_claims()) == 2


def test_append_edge_and_read_back(store, sample_edge):
    store.append_edge(sample_edge)
    edges = store.read_all_edges()
    assert len(edges) == 1
    assert edges[0].relation == "associated_with"


def test_claims_dedup_by_hash(store, sample_claim):
    store.append_claim(sample_claim)
    store.append_claim(sample_claim)  # same content
    claims = store.read_all_claims()
    assert len(claims) == 1


def test_edges_dedup_by_tuple(store, sample_edge):
    store.append_edge(sample_edge)
    store.append_edge(sample_edge)
    edges = store.read_all_edges()
    assert len(edges) == 1
```

- [ ] **Step 2: Run new tests to confirm they fail**

```bash
cd backend && pytest tests/services/test_wiki_store.py -v -k "entity or concept or claim or edge"
```

Expected: 7 failures (AttributeError — methods don't exist).

- [ ] **Step 3: Add entity/concept methods + claims.jsonl + edges.jsonl handling**

Add the following methods INSIDE the existing `WikiStore` class in `backend/services/wiki_store.py` (do **not** replace the methods from Task 4 — extend the class). Also add `import json` and `import hashlib` to the top of the file:

```python
def _entity_path(self, slug: str, entity_type: str) -> Path:
    return self.root / "wiki" / ENTITIES_DIR / entity_type / f"{slug}.md"


def write_entity(self, entity: Entity, slug: str) -> None:
    path = self._entity_path(slug, entity.type)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = entity.description
    post = frontmatter.Post(content=body, **{
        "id": entity.id, "type": entity.type, "aliases": entity.aliases,
        "mentions_count": entity.mentions_count,
        "questions": entity.questions, "tags": entity.tags,
    })
    self._atomic_write(path, frontmatter.dumps(post))


def read_entity(self, slug: str, entity_type: str) -> Optional[Entity]:
    path = self._entity_path(slug, entity_type)
    if not path.exists():
        return None
    post = frontmatter.load(path)
    return Entity(
        id=post["id"], type=post["type"],
        aliases=post.get("aliases", []),
        description=post.content.strip(),
        mentions_count=post.get("mentions_count", 0),
        questions=post.get("questions", []),
        tags=post.get("tags", []),
    )


def _concept_path(self, slug: str) -> Path:
    return self.root / "wiki" / CONCEPTS_DIR / f"{slug}.md"


def write_concept(self, concept: Concept, slug: str) -> None:
    path = self._concept_path(slug)
    body = concept.definition
    post = frontmatter.Post(content=body, **{
        "id": concept.id, "parent_concept": concept.parent_concept,
        "examples": concept.examples, "related": concept.related,
        "questions": concept.questions, "tags": concept.tags,
    })
    self._atomic_write(path, frontmatter.dumps(post))


def read_concept(self, slug: str) -> Optional[Concept]:
    path = self._concept_path(slug)
    if not path.exists():
        return None
    post = frontmatter.load(path)
    return Concept(
        id=post["id"],
        parent_concept=post.get("parent_concept"),
        definition=post.content.strip(),
        examples=post.get("examples", []),
        related=post.get("related", []),
        questions=post.get("questions", []),
        tags=post.get("tags", []),
    )


def _claims_path(self) -> Path:
    return self.root / "wiki" / "claims.jsonl"


def _edges_path(self) -> Path:
    return self.root / "wiki" / "edges.jsonl"


def _claim_dedup_key(self, claim: Claim) -> str:
    raw = f"{claim.subject_id}|{claim.text.strip().lower()}|{claim.polarity}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _edge_dedup_key(self, edge: Edge) -> str:
    return f"{edge.from_}|{edge.to}|{edge.relation}|{edge.source_id}"


def append_claim(self, claim: Claim) -> bool:
    path = self._claims_path()
    existing_keys = {self._claim_dedup_key(c) for c in self.read_all_claims()}
    key = self._claim_dedup_key(claim)
    if key in existing_keys:
        return False
    with path.open("a", encoding="utf-8") as f:
        f.write(claim.model_dump_json() + "\n")
    return True


def append_edge(self, edge: Edge) -> bool:
    path = self._edges_path()
    existing_keys = {self._edge_dedup_key(e) for e in self.read_all_edges()}
    key = self._edge_dedup_key(edge)
    if key in existing_keys:
        return False
    with path.open("a", encoding="utf-8") as f:
        f.write(edge.model_dump_json(by_alias=True) + "\n")
    return True


def read_all_claims(self) -> List[Claim]:
    path = self._claims_path()
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(Claim.model_validate_json(line))
    return out


def read_all_edges(self) -> List[Edge]:
    path = self._edges_path()
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(Edge.model_validate_json(line))
    return out
```

After this step, `wiki_store.py` has ONE class `WikiStore` with: `__init__`, `_atomic_write`, `_source_frontmatter`, `_source_path`, `write_source`, `read_source`, `list_sources` (from Task 4) + everything added in this step.

- [ ] **Step 4: Run all wiki_store tests**

```bash
cd backend && pytest tests/services/test_wiki_store.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/wiki_store.py backend/tests/services/test_wiki_store.py
git commit -m "feat(wiki_store): entity/concept/claim/edge persistence with dedup"
```

---

## Task 6: wiki_store — merge operations for re-ingest

**Files:**
- Modify: `backend/services/wiki_store.py`
- Modify: `backend/tests/services/test_wiki_store.py`

- [ ] **Step 1: Add failing tests**

Append to `backend/tests/services/test_wiki_store.py`:

```python
def test_entity_exists_check(store, sample_entity):
    assert not store.entity_exists("sypialnia", "Place")
    store.write_entity(sample_entity, slug="sypialnia")
    assert store.entity_exists("sypialnia", "Place")


def test_merge_entity_combines_aliases(store, sample_entity):
    store.write_entity(sample_entity, slug="sypialnia")
    updated = sample_entity.model_copy(update={
        "aliases": ["bedroom", "schlafzimmer"],
        "mentions_count": 5,
    })
    store.merge_entity(updated, slug="sypialnia")
    loaded = store.read_entity("sypialnia", "Place")
    assert sorted(loaded.aliases) == ["bedroom", "schlafzimmer"]
    assert loaded.mentions_count == 5


def test_merge_concept_combines_examples(store, sample_concept):
    store.write_concept(sample_concept, slug="kolory-neutralne")
    updated = sample_concept.model_copy(update={
        "examples": ["beż", "biel", "szary"],
    })
    store.merge_concept(updated, slug="kolory-neutralne")
    loaded = store.read_concept("kolory-neutralne")
    assert sorted(loaded.examples) == ["beż", "biel", "szary"]
```

- [ ] **Step 2: Run new tests to verify failure**

```bash
cd backend && pytest tests/services/test_wiki_store.py -v -k "exists or merge"
```

Expected: 3 failures (AttributeError).

- [ ] **Step 3: Implement merge methods**

Add the following methods inside the `WikiStore` class in `backend/services/wiki_store.py`:

```python
def entity_exists(self, slug: str, entity_type: str) -> bool:
    return self._entity_path(slug, entity_type).exists()


def concept_exists(self, slug: str) -> bool:
    return self._concept_path(slug).exists()


def merge_entity(self, new: Entity, slug: str) -> None:
    existing = self.read_entity(slug, new.type)
    if existing is None:
        self.write_entity(new, slug)
        return
    merged_aliases = sorted(set(existing.aliases) | set(new.aliases))
    merged_questions = sorted(set(existing.questions) | set(new.questions))
    merged_tags = sorted(set(existing.tags) | set(new.tags))
    merged = existing.model_copy(update={
        "aliases": merged_aliases,
        "description": new.description if new.description.strip() else existing.description,
        "mentions_count": max(existing.mentions_count, new.mentions_count),
        "questions": merged_questions,
        "tags": merged_tags,
    })
    self.write_entity(merged, slug)


def merge_concept(self, new: Concept, slug: str) -> None:
    existing = self.read_concept(slug)
    if existing is None:
        self.write_concept(new, slug)
        return
    merged = existing.model_copy(update={
        "examples": sorted(set(existing.examples) | set(new.examples)),
        "related": sorted(set(existing.related) | set(new.related)),
        "questions": sorted(set(existing.questions) | set(new.questions)),
        "tags": sorted(set(existing.tags) | set(new.tags)),
        "definition": new.definition if new.definition.strip() else existing.definition,
    })
    self.write_concept(merged, slug)
```

- [ ] **Step 4: Run all wiki_store tests**

```bash
cd backend && pytest tests/services/test_wiki_store.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/wiki_store.py backend/tests/services/test_wiki_store.py
git commit -m "feat(wiki_store): merge operations for entity/concept re-ingest"
```

---

## Task 7: wiki_index — regenerate index.md and index.json

**Files:**
- Create: `backend/services/wiki_index.py`
- Create: `backend/tests/services/test_wiki_index.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/test_wiki_index.py`:

```python
import json
import pytest
from datetime import datetime
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from models.wiki_models import Source, Entity, Concept


@pytest.fixture
def store(tmp_path):
    s = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="Test source", type="article",
        raw_path="raw/x", ingested_at=datetime(2026, 4, 28),
        summary="sum", key_takeaways=[], questions=["q1"], tags=["t1"],
    )
    s.write_source(src, slug="test-source")
    e = Entity(id="e_001", type="Place", description="d",
               questions=["q2"], tags=[])
    s.write_entity(e, slug="test-place")
    c = Concept(id="c_001", definition="d", examples=[], related=[],
                questions=[], tags=[])
    s.write_concept(c, slug="test-concept")
    return s


def test_regenerate_writes_index_md(store):
    regenerate_index(store)
    md = (store.root / "wiki" / "00-Index" / "index.md").read_text(encoding="utf-8")
    assert "# Wiki Index" in md
    assert "test-source" in md
    assert "test-place" in md
    assert "test-concept" in md


def test_regenerate_writes_index_json(store):
    regenerate_index(store)
    j = json.loads((store.root / "wiki" / "00-Index" / "index.json").read_text(encoding="utf-8"))
    assert "sources" in j and "entities" in j and "concepts" in j
    assert len(j["sources"]) == 1
    assert j["sources"][0]["slug"] == "test-source"
    assert j["sources"][0]["questions"] == ["q1"]


def test_index_json_groups_entities_by_type(store):
    regenerate_index(store)
    j = json.loads((store.root / "wiki" / "00-Index" / "index.json").read_text(encoding="utf-8"))
    place_entries = [e for e in j["entities"] if e["type"] == "Place"]
    assert len(place_entries) == 1


def test_regenerate_overwrites_previous(store):
    regenerate_index(store)
    e2 = Entity(id="e_002", type="Person", description="d", questions=[], tags=[])
    store.write_entity(e2, slug="alice")
    regenerate_index(store)
    j = json.loads((store.root / "wiki" / "00-Index" / "index.json").read_text(encoding="utf-8"))
    assert len(j["entities"]) == 2
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd backend && pytest tests/services/test_wiki_index.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement wiki_index**

Create `backend/services/wiki_index.py`:

```python
import json
from pathlib import Path
from typing import List
from services.wiki_store import WikiStore, ENTITIES_DIR


def regenerate_index(store: WikiStore) -> None:
    sources = _collect_sources(store)
    entities = _collect_entities(store)
    concepts = _collect_concepts(store)

    index_data = {
        "sources": sources,
        "entities": entities,
        "concepts": concepts,
    }
    json_path = store.root / "wiki" / "00-Index" / "index.json"
    md_path = store.root / "wiki" / "00-Index" / "index.md"

    store._atomic_write(json_path, json.dumps(index_data, indent=2, ensure_ascii=False))
    store._atomic_write(md_path, _render_markdown(sources, entities, concepts))


def _collect_sources(store: WikiStore) -> List[dict]:
    out = []
    for slug in sorted(store.list_sources()):
        s = store.read_source(slug)
        out.append({
            "slug": slug, "id": s.id, "title": s.title,
            "tags": s.tags, "questions": s.questions,
            "summary": s.summary[:200],
        })
    return out


def _collect_entities(store: WikiStore) -> List[dict]:
    out = []
    base = store.root / "wiki" / ENTITIES_DIR
    if not base.exists():
        return out
    for type_dir in sorted(base.iterdir()):
        if not type_dir.is_dir():
            continue
        for path in sorted(type_dir.glob("*.md")):
            slug = path.stem
            e = store.read_entity(slug, type_dir.name)
            if e is None:
                continue
            out.append({
                "slug": slug, "id": e.id, "type": e.type,
                "aliases": e.aliases, "tags": e.tags,
                "questions": e.questions,
                "description_preview": e.description[:200],
            })
    return out


def _collect_concepts(store: WikiStore) -> List[dict]:
    out = []
    for slug in sorted(p.stem for p in (store.root / "wiki" / "10-Concepts").glob("*.md")):
        c = store.read_concept(slug)
        out.append({
            "slug": slug, "id": c.id,
            "parent_concept": c.parent_concept,
            "tags": c.tags, "questions": c.questions,
            "definition_preview": c.definition[:200],
        })
    return out


def _render_markdown(sources: List[dict], entities: List[dict], concepts: List[dict]) -> str:
    lines = ["# Wiki Index", ""]
    lines.append(f"**Sources ({len(sources)})**")
    lines.append("")
    for s in sources:
        lines.append(f"- [{s['title']}](../30-Sources/{s['slug']}.md) — {s['summary']}")
    lines.append("")
    lines.append(f"**Entities ({len(entities)})**")
    lines.append("")
    for e in entities:
        lines.append(f"- `{e['type']}` [{e['slug']}](../20-Entities/{e['type']}/{e['slug']}.md) — {e['description_preview']}")
    lines.append("")
    lines.append(f"**Concepts ({len(concepts)})**")
    lines.append("")
    for c in concepts:
        lines.append(f"- [{c['slug']}](../10-Concepts/{c['slug']}.md) — {c['definition_preview']}")
    lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/services/test_wiki_index.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/wiki_index.py backend/tests/services/test_wiki_index.py
git commit -m "feat(wiki_index): regenerate index.md and index.json from vault state"
```

---

## Task 8: wiki_log — append timestamped entries

**Files:**
- Create: `backend/services/wiki_log.py`
- Create: `backend/tests/services/test_wiki_log.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/test_wiki_log.py`:

```python
import pytest
from datetime import datetime
from pathlib import Path
from services.wiki_store import WikiStore
from services.wiki_log import append_log_entry


@pytest.fixture
def store(tmp_path):
    return WikiStore(root=tmp_path)


def test_append_creates_log_if_missing(store):
    append_log_entry(store, op="ingest", source_id="src_001",
                     details="title=test, +3 entities, +5 claims",
                     timestamp=datetime(2026, 4, 28, 11, 30))
    log = (store.root / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "## [2026-04-28 11:30]" in log
    assert "ingest" in log
    assert "src_001" in log


def test_append_multiple_entries_in_order(store):
    append_log_entry(store, op="ingest", source_id="src_001", details="a",
                     timestamp=datetime(2026, 4, 28, 10, 0))
    append_log_entry(store, op="lint", source_id=None, details="run b",
                     timestamp=datetime(2026, 4, 28, 11, 0))
    log = (store.root / "wiki" / "log.md").read_text(encoding="utf-8")
    a_idx = log.find("[2026-04-28 10:00]")
    b_idx = log.find("[2026-04-28 11:00]")
    assert 0 < a_idx < b_idx


def test_log_format_includes_op_type(store):
    append_log_entry(store, op="query", source_id=None,
                     details="q='kolory sypialni'",
                     timestamp=datetime(2026, 4, 28, 12, 0))
    log = (store.root / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "query" in log
    assert "'kolory sypialni'" in log
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd backend && pytest tests/services/test_wiki_log.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement wiki_log**

Create `backend/services/wiki_log.py`:

```python
from datetime import datetime
from typing import Optional
from services.wiki_store import WikiStore


def append_log_entry(
    store: WikiStore,
    op: str,
    source_id: Optional[str],
    details: str,
    timestamp: Optional[datetime] = None,
) -> None:
    ts = timestamp or datetime.now()
    ts_fmt = ts.strftime("%Y-%m-%d %H:%M")
    src_part = f" | {source_id}" if source_id else ""
    line = f"## [{ts_fmt}] {op}{src_part} | {details}\n"

    log_path = store.root / "wiki" / "log.md"
    if not log_path.exists():
        log_path.write_text("# Wiki Log\n\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line)
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/services/test_wiki_log.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/wiki_log.py backend/tests/services/test_wiki_log.py
git commit -m "feat(wiki_log): timestamped append-only operation log"
```

---

## Task 9: KNOWLEDGE_MAP.md conventions document

**Files:**
- Create: `backend/schema/KNOWLEDGE_MAP.md`

- [ ] **Step 1: Write the conventions document**

Create `backend/schema/KNOWLEDGE_MAP.md`:

```markdown
# Knowledge Map — Conventions

This document is the constitution for the wiki layer. The LLM and the codebase follow these rules verbatim.

## Layers

1. **Sources** (`wiki/30-Sources/<slug>.md`) — leaves; one per ingested raw source.
2. **Entities** (`wiki/20-Entities/<Type>/<slug>.md`) — typed: Person, Org, Product, Place, Event.
3. **Concepts** (`wiki/10-Concepts/<slug>.md`) — cross-cutting bridges between entities.
4. **Claims** (`wiki/claims.jsonl`) — atomic statements with provenance.
5. **Edges** (`wiki/edges.jsonl`) — typed relations between nodes.

Plus:
- `wiki/00-Index/index.md` (human catalog) and `wiki/00-Index/index.json` (machine-readable). Regenerated after every mutation.
- `wiki/log.md` — chronological append-only operation log.

## Slug rules

- Lowercase, hyphenated, ASCII-folded. Example: "Łazienka — sypialnia" → `lazienka-sypialnia`.
- Stripped of punctuation; whitespace and hyphens collapsed.
- Unique per layer; on collision append `-2`, `-3`, ... (deterministic).

## Frontmatter (YAML at top of every .md)

Every page has YAML frontmatter; `description`/`summary`/`definition` is the post body.

### Source

```yaml
id: "src_<n>"
title: "..."
type: "article|pdf|docx|txt|url"
raw_path: "raw/<slug>/parsed.md"
ingested_at: "2026-04-28T10:00:00"
source_url: "https://..."   # optional
key_takeaways: ["..."]
questions: ["..."]
tags: ["..."]
```

### Entity

```yaml
id: "e_<n>"
type: "Person|Org|Product|Place|Event"
aliases: ["..."]
mentions_count: 0
questions: ["..."]
tags: ["..."]
```

### Concept

```yaml
id: "c_<n>"
parent_concept: "..."   # optional
examples: ["..."]
related: ["..."]
questions: ["..."]
tags: ["..."]
```

## Claims (one JSON object per line in claims.jsonl)

```json
{"id": "cl_<n>", "text": "...", "subject_id": "entity:e_001|concept:c_001",
 "source_id": "src_<n>", "span": {"start": 0, "end": 0, "text": "..."},
 "confidence": 0.0, "polarity": "asserts|denies", "related_claim_ids": []}
```

Dedup key: `sha256(subject_id|normalized_text|polarity)`. On dedup, append `source_id` to existing claim's source list (Phase 2 detail).

## Edges (one JSON object per line in edges.jsonl)

```json
{"id": "ed_<n>", "from": "entity:e_001", "to": "concept:c_001",
 "relation": "<closed list>", "source_id": "src_<n>",
 "span": {"start": 0, "end": 0, "text": "..."}, "confidence": 0.0}
```

Closed list of relations (10): `mentions`, `defines`, `contradicts`, `supports`, `derives_from`, `instance_of`, `part_of`, `associated_with`, `causes`, `precedes`. Free-form relations are rejected.

Dedup key: `(from, to, relation, source_id)`.

## Provenance invariant

**Every claim, every edge, and every assertion in entity/concept descriptions has `source_id + span`. No exceptions.** The Lint workflow (Phase 6) enforces this.

## Topology

- Sources have **one** structural link — to their primary hub (Concept or Entity).
- Cross-entity routing only via Concepts (the "thin bridges").
- Result: graph reads as 5–20 islands with thin bridges, not a single tangle.

## Operations

- **Ingest**: parse → classify (LLM Pydantic) → resolve+template-generate → optional conflict detection → save. See Phase 2 spec.
- **Query**: parse intent → filter candidates → select → assemble context → answer. See Phase 3 spec.
- **Lint**: check provenance, integrity, navigability (Tier 1+2 deterministic), semantic (Tier 3 LLM). See Phase 6/7 spec.

## Atomic writes

All file writes go via tmp file + rename. Never write directly to a final path.
```

- [ ] **Step 2: Commit**

```bash
git add backend/schema/KNOWLEDGE_MAP.md
git commit -m "docs(schema): add KNOWLEDGE_MAP.md conventions document"
```

---

## Task 10: Sample fixtures for integration tests

**Files:**
- Create: `backend/tests/fixtures/sample_sources/source_a.md`
- Create: `backend/tests/fixtures/sample_sources/source_b.md`
- Create: `backend/tests/fixtures/sample_sources/source_c.md`

- [ ] **Step 1: Create 3 sample raw sources**

Create `backend/tests/fixtures/sample_sources/source_a.md`:

```markdown
# Sypialnia w stylu skandynawskim

Skandynawska sypialnia opiera się na neutralnej palecie kolorów: bieli, beżu i szarości. Drewno jest dominującym materiałem, najczęściej dębowe lub sosnowe.

Tekstylia są naturalne — len, bawełna, wełna. Oświetlenie ciepłe, rozproszone.

Klucz: minimalizm i funkcjonalność.
```

Create `backend/tests/fixtures/sample_sources/source_b.md`:

```markdown
# Łazienka w stylu skandynawskim

Łazienka skandynawska wykorzystuje neutralne kolory — biel, jasny szary, beż. Drewniane elementy (półki, dekoracje) wprowadzają ciepło.

Płytki najczęściej w odcieniu jasno-szarym. Oświetlenie naturalne mocno preferowane.

Akcesoria: ceramika, kamień, len.
```

Create `backend/tests/fixtures/sample_sources/source_c.md`:

```markdown
# Salon japandi — fuzja stylów

Japandi łączy japoński minimalizm ze skandynawską przytulnością. Kolory: biel, beż, czerń, ciemny brąz.

Materiały: drewno (jasne i ciemne), bambus, len, wełna.

Filozofia: piękno w prostocie, świadome wybory.
```

- [ ] **Step 2: Commit**

```bash
git add backend/tests/fixtures/sample_sources/
git commit -m "test(fixtures): add 3 sample raw sources for integration tests"
```

---

## Task 11: Integration test — full round trip

**Files:**
- Create: `backend/tests/services/test_integration_round_trip.py`

- [ ] **Step 1: Write the integration test**

Create `backend/tests/services/test_integration_round_trip.py`:

```python
import json
import pytest
from datetime import datetime
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from services.wiki_log import append_log_entry
from models.wiki_models import (
    Source, Entity, Concept, Claim, Edge, Span
)


def test_full_round_trip_writes_reads_indexes_and_logs(tmp_path):
    store = WikiStore(root=tmp_path)

    src = Source(
        id="src_001", title="Sypialnia skandynawska", type="article",
        raw_path="raw/sypialnia/parsed.md",
        ingested_at=datetime(2026, 4, 28, 10, 0, 0),
        summary="Streszczenie sypialni.", key_takeaways=["minimalizm"],
        questions=["jakie kolory?"], tags=["sypialnia"],
    )
    store.write_source(src, slug="sypialnia-skandynawska")

    bedroom = Entity(
        id="e_001", type="Place", aliases=["bedroom"],
        description="Sypialnia.", mentions_count=1,
        questions=["jakie kolory?"], tags=["pomieszczenie"],
    )
    store.write_entity(bedroom, slug="sypialnia")

    bathroom = Entity(
        id="e_002", type="Place", aliases=["bathroom"],
        description="Łazienka.", mentions_count=1,
        questions=["jakie kolory?"], tags=["pomieszczenie"],
    )
    store.write_entity(bathroom, slug="lazienka")

    neutral_colors = Concept(
        id="c_001", definition="Neutralne kolory.",
        examples=["biel", "beż", "szary"], related=[],
        questions=["jakie odcienie?"], tags=["kolory"],
    )
    store.write_concept(neutral_colors, slug="kolory-neutralne")

    span = Span(start=0, end=20, text="excerpt")
    store.append_claim(Claim(
        id="cl_001", text="Sypialnia używa kolorów neutralnych.",
        subject_id="entity:e_001", source_id="src_001",
        span=span, confidence=0.92, polarity="asserts",
    ))
    store.append_claim(Claim(
        id="cl_002", text="Łazienka używa kolorów neutralnych.",
        subject_id="entity:e_002", source_id="src_001",
        span=span, confidence=0.88, polarity="asserts",
    ))

    store.append_edge(Edge(
        id="ed_001", **{"from": "entity:e_001"}, to="concept:c_001",
        relation="associated_with", source_id="src_001",
        span=span, confidence=0.9,
    ))
    store.append_edge(Edge(
        id="ed_002", **{"from": "entity:e_002"}, to="concept:c_001",
        relation="associated_with", source_id="src_001",
        span=span, confidence=0.9,
    ))

    regenerate_index(store)
    append_log_entry(store, op="ingest", source_id="src_001",
                     details="+2 entities, +1 concept, +2 claims, +2 edges",
                     timestamp=datetime(2026, 4, 28, 10, 5))

    # Read back
    assert store.read_source("sypialnia-skandynawska").title == "Sypialnia skandynawska"
    assert store.read_entity("sypialnia", "Place").id == "e_001"
    assert store.read_entity("lazienka", "Place").id == "e_002"
    assert store.read_concept("kolory-neutralne").id == "c_001"
    assert len(store.read_all_claims()) == 2
    assert len(store.read_all_edges()) == 2

    idx = json.loads((tmp_path / "wiki" / "00-Index" / "index.json").read_text(encoding="utf-8"))
    assert len(idx["sources"]) == 1
    assert len(idx["entities"]) == 2
    assert len(idx["concepts"]) == 1

    log = (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "src_001" in log
    assert "ingest" in log

    # Verify cross-document synthesis is structurally enabled:
    # both bedroom and bathroom edges point to neutral_colors concept.
    edges = store.read_all_edges()
    targets_to_concept = [e for e in edges if e.to == "concept:c_001"]
    sources_of_those = {e.from_ for e in targets_to_concept}
    assert sources_of_those == {"entity:e_001", "entity:e_002"}
```

- [ ] **Step 2: Run integration test**

```bash
cd backend && pytest tests/services/test_integration_round_trip.py -v
```

Expected: 1 passed.

- [ ] **Step 3: Run full test suite to ensure nothing broke**

```bash
cd backend && pytest tests/services/ -v
```

Expected: all green (≥ 30 tests).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/services/test_integration_round_trip.py
git commit -m "test(integration): full vault round-trip exercising all data layer ops"
```

---

## Self-Review Checklist (post-execution, before merging Phase 1)

- [ ] All 33+ tests passing (`pytest tests/services/ -v`)
- [ ] No `chunkers/`, `embeddings_service`, `vector_store`, `query_expander` references introduced (Phase 1 should not touch deprecated code yet — that's Phase 9)
- [ ] `backend/wiki_data/.example/` exists with `.gitkeep` files
- [ ] `backend/schema/KNOWLEDGE_MAP.md` exists
- [ ] Atomic writes verified (no `.tmp` files left in fixtures after tests)
- [ ] All Pydantic models reject malformed input (per Task 3 tests)
- [ ] Re-ingest merge preserves data (per Task 6 tests)
- [ ] Integration test demonstrates cross-document edges-to-concept linkage (the structural fix for hard-eval failure)

---

## What Phase 1 explicitly does NOT do

- No HTTP API endpoints (Phase 2 adds them).
- No frontend changes (Phase 2 onwards).
- No removal of legacy services (`chunkers/`, `embeddings_service.py`, `vector_store.py`, etc.) — that's Phase 9.
- No LLM calls of any kind (Phase 2 introduces `source_classifier`).
- No Lint workflow (Phase 6).

The data layer is an internal Python API consumed by future phases via direct imports.

---

## Done criterion for Phase 1

A new contributor can:

1. `pip install -r backend/requirements.txt`
2. `cd backend && pytest tests/services/ -v` → all green
3. Inspect `backend/schema/KNOWLEDGE_MAP.md` and understand wiki conventions
4. Use `WikiStore`, `regenerate_index`, `append_log_entry` from a Python REPL to manually build a small vault on disk
5. Confirm files are human-readable, openable in any editor or Obsidian

When the integration test passes and the conventions doc is in place, Phase 2 can begin.
