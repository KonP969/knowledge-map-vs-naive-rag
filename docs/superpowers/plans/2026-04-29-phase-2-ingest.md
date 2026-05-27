# Phase 2: Ingest Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the 5-stage ingest pipeline (Parse → Classify → Resolve → Conflict Detection → Save+Log+Reindex) with a FastAPI endpoint, wiki read-only API endpoints, and two frontend panels (SourcesPanel, IngestPipelinePanel) that let users upload files and observe ingestion results.

**Architecture:** Ingestion is a sequential pipeline orchestrated by `ingest_pipeline.py`. Stages 1, 3, and 5 are deterministic (no LLM). Stages 2 and 4 call OpenAI via `client.beta.chat.completions.parse()` for structured output. The pipeline reads/writes via the existing `WikiStore` API. The backend exposes `POST /api/ingest/source` and `GET /api/wiki/{sources,entities,concepts}` endpoints. The frontend adds two new panels wired into the existing Sidebar + App.tsx panel-switching pattern.

**Tech Stack:** Python 3.9+, FastAPI, Pydantic v2, OpenAI SDK 1.51.0 (structured output), PyPDF2, python-docx, pytest + unittest.mock; React 19 + TypeScript + Vite + Tailwind CSS, lucide-react.

**Phase 1 baseline:** 39 tests green on commit `320d1ab`.

---

## Scope decision: one plan or two?

**Recommendation: One plan, backend-first sequencing.** The frontend panels are thin wrappers over the backend API. Implementing frontend before the API exists makes every frontend step require a mock server. Sequencing backend tasks first (Tasks 1–9) then frontend tasks (Tasks 10–11) allows the frontend to be tested against the real API. Both backend and frontend are included in this single plan.

---

## File Structure (Phase 2)

**Create (backend):**
- `backend/models/ingest_models.py` — EntityMention, ConceptMention, ClaimExtraction, SourceClassification, ConflictReport, IngestResult
- `backend/services/parser.py` — Stage 1: parse raw file to markdown + manifest
- `backend/services/source_classifier.py` — Stage 2: OpenAI structured output call
- `backend/services/resolver.py` — Stage 3: deterministic WikiStore mapping
- `backend/services/conflict_detector.py` — Stage 4: conditional LLM conflict check
- `backend/services/ingest_pipeline.py` — orchestrates all 5 stages
- `backend/api/ingest.py` — FastAPI router: POST /api/ingest/source
- `backend/api/wiki.py` — FastAPI router: GET /api/wiki/sources, /entities, /concepts
- `backend/tests/services/__init__.py` — already exists
- `backend/tests/models/__init__.py` — new
- `backend/tests/models/test_ingest_models.py`
- `backend/tests/api/__init__.py` — new
- `backend/tests/api/test_ingest_api.py`
- `backend/tests/api/test_wiki_api.py`
- `backend/tests/services/test_parser.py`
- `backend/tests/services/test_source_classifier.py`
- `backend/tests/services/test_conflict_detector.py`
- `backend/tests/services/test_resolver.py`
- `backend/tests/services/test_ingest_pipeline.py`
- `backend/tests/fixtures/sample.txt` — minimal text fixture for parser tests
- `backend/tests/fixtures/sample.pdf` — minimal PDF fixture (created programmatically in conftest)

**Create (frontend):**
- `frontend/src/components/wiki/SourcesPanel.tsx`
- `frontend/src/components/wiki/IngestPipelinePanel.tsx`

**Modify:**
- `backend/main.py` — include ingest and wiki routers
- `frontend/src/App.tsx` — add "sources" and "ingest" panels
- `frontend/src/types/index.ts` — add wiki + ingest TypeScript types
- `frontend/src/api/client.ts` — add ingest and wiki API calls
- `frontend/src/components/layout/Sidebar.tsx` — add Sources and Ingest entries

---

## Task 1: Ingest models

**Files:**
- Create: `backend/models/ingest_models.py`
- Create: `backend/tests/models/__init__.py`
- Create: `backend/tests/models/test_ingest_models.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/models/__init__.py` (empty).

Create `backend/tests/models/test_ingest_models.py`:

```python
import pytest
from models.ingest_models import (
    EntityMention, ConceptMention, ClaimExtraction,
    SourceClassification, ConflictReport, IngestResult,
)
from models.wiki_models import Span


def test_entity_mention_valid():
    em = EntityMention(
        name="IKEA",
        type="Org",
        aliases=["IKEA Group"],
        description="Swedish furniture retailer.",
        span=Span(start=0, end=4, text="IKEA"),
    )
    assert em.name == "IKEA"
    assert em.type == "Org"


def test_entity_mention_invalid_type():
    with pytest.raises(Exception):
        EntityMention(
            name="IKEA",
            type="Company",  # not in EntityType
            aliases=[],
            description="x",
            span=Span(start=0, end=4, text="IKEA"),
        )


def test_concept_mention_valid():
    cm = ConceptMention(
        name="neutral palette",
        definition="A color scheme using whites, beiges, and grays.",
        span=Span(start=10, end=24, text="neutral palette"),
    )
    assert cm.name == "neutral palette"


def test_claim_extraction_valid_polarity():
    ce = ClaimExtraction(
        text="IKEA uses sustainable materials.",
        subject_name="IKEA",
        subject_type="entity",
        span=Span(start=0, end=31, text="IKEA uses sustainable materials."),
        confidence=0.9,
        polarity="asserts",
    )
    assert ce.subject_type == "entity"


def test_claim_extraction_invalid_subject_type():
    with pytest.raises(Exception):
        ClaimExtraction(
            text="X",
            subject_name="X",
            subject_type="relation",  # invalid
            span=Span(start=0, end=1, text="X"),
            confidence=0.5,
            polarity="asserts",
        )


def test_source_classification_valid():
    sc = SourceClassification(
        title="Scandinavian Bedroom",
        description="Article about Scandinavian bedroom design.",
        tags=["bedroom", "scandinavian"],
        questions=["What colors are typical?"],
        key_takeaways=["Minimalism is key."],
        entity_mentions=[],
        concept_mentions=[],
        claims=[],
    )
    assert sc.title == "Scandinavian Bedroom"


def test_conflict_report_valid():
    cr = ConflictReport(
        new_claim_id="cl_002",
        existing_claim_id="cl_001",
        description="Claim contradicts an existing assertion.",
    )
    assert cr.new_claim_id == "cl_002"


def test_ingest_result_status_enum():
    with pytest.raises(Exception):
        IngestResult(
            source_id="src_001",
            slug="test-source",
            status="unknown",  # invalid
            entities_created=0, entities_merged=0,
            concepts_created=0, concepts_merged=0,
            claims_added=0, edges_added=0,
            conflicts=[], duration_ms=100.0, llm_calls=1,
        )


def test_ingest_result_ok():
    result = IngestResult(
        source_id="src_001",
        slug="test-source",
        status="ok",
        entities_created=2, entities_merged=0,
        concepts_created=1, concepts_merged=0,
        claims_added=3, edges_added=3,
        conflicts=[], duration_ms=1234.5, llm_calls=1,
    )
    assert result.status == "ok"
    assert result.error is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/models/test_ingest_models.py -v
```

Expected: ImportError — `models.ingest_models` not found.

- [ ] **Step 3: Implement ingest models**

Create `backend/models/ingest_models.py`:

```python
from typing import List, Literal, Optional
from pydantic import BaseModel
from models.wiki_models import EntityType, Polarity, Span


class EntityMention(BaseModel):
    name: str
    type: EntityType
    aliases: List[str]
    description: str
    span: Span


class ConceptMention(BaseModel):
    name: str
    definition: str
    span: Span


class ClaimExtraction(BaseModel):
    text: str
    subject_name: str
    subject_type: Literal["entity", "concept"]
    span: Span
    confidence: float
    polarity: Polarity


class SourceClassification(BaseModel):
    title: str
    description: str
    tags: List[str]
    questions: List[str]
    key_takeaways: List[str]
    entity_mentions: List[EntityMention]
    concept_mentions: List[ConceptMention]
    claims: List[ClaimExtraction]


class ConflictReport(BaseModel):
    new_claim_id: str
    existing_claim_id: str
    description: str


class IngestResult(BaseModel):
    source_id: str
    slug: str
    status: Literal["ok", "partial", "error"]
    entities_created: int
    entities_merged: int
    concepts_created: int
    concepts_merged: int
    claims_added: int
    edges_added: int
    conflicts: List[ConflictReport]
    duration_ms: float
    llm_calls: int
    error: Optional[str] = None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/models/test_ingest_models.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/models/ingest_models.py backend/tests/models/__init__.py backend/tests/models/test_ingest_models.py
git commit -m "feat(models): ingest pipeline Pydantic models (SourceClassification, IngestResult, etc.)"
```

---

## Task 2: Stage 1 — Parser (deterministic)

**Files:**
- Create: `backend/services/parser.py`
- Create: `backend/tests/services/test_parser.py`
- Create: `backend/tests/fixtures/sample.txt` (empty placeholder; actual content written in test)

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/test_parser.py`:

```python
import json
import pytest
from pathlib import Path
from services.parser import parse_source


@pytest.fixture
def txt_file(tmp_path):
    p = tmp_path / "article.txt"
    p.write_text(
        "Scandinavian bedroom design relies on neutral colors.\n"
        "Wood is the dominant material — oak or pine.\n"
        "Textiles are natural: linen, cotton, wool.",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def pdf_file(tmp_path):
    """Create a minimal PDF using PyPDF2 internals — no dependency on external tools."""
    import PyPDF2
    from PyPDF2 import PdfWriter
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    out = tmp_path / "article.pdf"
    with out.open("wb") as f:
        writer.write(f)
    return out


def test_parse_txt_writes_parsed_md(txt_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    result = parse_source(txt_file, store_root=store_root)
    parsed_md = store_root / "raw" / result["slug"] / "parsed.md"
    assert parsed_md.exists()
    content = parsed_md.read_text(encoding="utf-8")
    assert "Scandinavian" in content


def test_parse_txt_writes_manifest_json(txt_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    result = parse_source(txt_file, store_root=store_root)
    manifest_path = store_root / "raw" / result["slug"] / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "char_count" in manifest
    assert manifest["char_count"] > 0
    assert "language" in manifest
    assert "sections" in manifest


def test_parse_txt_returns_slug_and_text(txt_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    result = parse_source(txt_file, store_root=store_root)
    assert "slug" in result
    assert "text" in result
    assert len(result["text"]) > 0


def test_parse_txt_slug_is_deterministic(txt_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    r1 = parse_source(txt_file, store_root=store_root)
    # Second call on same file should produce the same slug
    store_root2 = tmp_path / "wiki_root2"
    r2 = parse_source(txt_file, store_root=store_root2)
    assert r1["slug"] == r2["slug"]


def test_parse_unsupported_extension_raises(tmp_path):
    bad = tmp_path / "file.odt"
    bad.write_bytes(b"data")
    with pytest.raises(ValueError, match="Unsupported"):
        parse_source(bad, store_root=tmp_path / "root")


def test_parse_pdf_produces_output(pdf_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    # blank PDF — text may be empty but files must be written
    result = parse_source(pdf_file, store_root=store_root)
    parsed_md = store_root / "raw" / result["slug"] / "parsed.md"
    manifest_path = store_root / "raw" / result["slug"] / "manifest.json"
    assert parsed_md.exists()
    assert manifest_path.exists()


def test_manifest_contains_char_count(txt_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    result = parse_source(txt_file, store_root=store_root)
    manifest_path = store_root / "raw" / result["slug"] / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["char_count"] == len(result["text"])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/test_parser.py -v
```

Expected: ImportError — `services.parser` not found.

- [ ] **Step 3: Implement parser**

Create `backend/services/parser.py`:

```python
import json
import os
from pathlib import Path
from typing import Any, Dict

import PyPDF2
from docx import Document

from services._slug import slugify


def parse_source(file_path: Path, store_root: Path) -> Dict[str, Any]:
    """
    Stage 1 (deterministic). Reads the raw file, extracts text, writes:
      <store_root>/raw/<slug>/parsed.md
      <store_root>/raw/<slug>/manifest.json
    Returns {"slug": str, "text": str, "raw_dir": Path}.
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    if ext == ".txt":
        text = _parse_txt(file_path)
    elif ext == ".pdf":
        text = _parse_pdf(file_path)
    elif ext == ".docx":
        text = _parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext!r}. Allowed: .txt, .pdf, .docx")

    slug = slugify(file_path.stem)
    raw_dir = Path(store_root) / "raw" / slug
    raw_dir.mkdir(parents=True, exist_ok=True)

    parsed_md = raw_dir / "parsed.md"
    _atomic_write(parsed_md, text)

    sections = _detect_sections(text)
    language = _detect_language(text)
    manifest = {
        "slug": slug,
        "original_filename": file_path.name,
        "char_count": len(text),
        "language": language,
        "sections": sections,
    }
    manifest_path = raw_dir / "manifest.json"
    _atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))

    return {"slug": slug, "text": text, "raw_dir": raw_dir}


def _parse_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_pdf(path: Path) -> str:
    parts = []
    with path.open("rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                parts.append(extracted)
    return "\n".join(parts)


def _parse_docx(path: Path) -> str:
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _detect_sections(text: str) -> list:
    """Return list of detected section headings (lines starting with # or all-caps short lines)."""
    sections = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            sections.append(stripped.lstrip("#").strip())
        elif stripped.isupper() and 3 <= len(stripped) <= 60:
            sections.append(stripped)
    return sections


def _detect_language(text: str) -> str:
    """Heuristic: if text contains common Polish function words → 'pl', else 'en'."""
    polish_markers = {"jest", "są", "tego", "się", "przez", "oraz", "jako"}
    words = set(text.lower().split())
    if polish_markers & words:
        return "pl"
    return "en"


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/test_parser.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/parser.py backend/tests/services/test_parser.py
git commit -m "feat(parser): Stage 1 deterministic file parser — TXT/PDF/DOCX to parsed.md + manifest.json"
```

---

## Task 3: Stage 2 — Source Classifier (LLM, mocked in tests)

**Files:**
- Create: `backend/services/source_classifier.py`
- Create: `backend/tests/services/test_source_classifier.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/test_source_classifier.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from models.ingest_models import (
    SourceClassification, EntityMention, ConceptMention, ClaimExtraction
)
from models.wiki_models import Span


# ── shared fixture ────────────────────────────────────────────────────────────

FIXED_CLASSIFICATION = SourceClassification(
    title="Scandinavian Bedroom",
    description="Article about Scandinavian bedroom design principles.",
    tags=["bedroom", "scandinavian", "design"],
    questions=["What colors are typical?", "What materials are used?"],
    key_takeaways=["Neutral palette is central.", "Wood dominates."],
    entity_mentions=[
        EntityMention(
            name="Sypialnia",
            type="Place",
            aliases=["bedroom"],
            description="A bedroom in Scandinavian style.",
            span=Span(start=0, end=8, text="Sypialnia"),
        )
    ],
    concept_mentions=[
        ConceptMention(
            name="neutral palette",
            definition="Color scheme using whites, beiges, and grays.",
            span=Span(start=20, end=35, text="neutral palette"),
        )
    ],
    claims=[
        ClaimExtraction(
            text="Scandinavian bedrooms use neutral colors.",
            subject_name="Sypialnia",
            subject_type="entity",
            span=Span(start=0, end=40, text="Scandinavian bedrooms use neutral colors."),
            confidence=0.95,
            polarity="asserts",
        )
    ],
)


def _make_mock_response(classification: SourceClassification):
    """Build a mock object that mimics openai structured output response."""
    mock_msg = MagicMock()
    mock_msg.parsed = classification
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


# ── tests ─────────────────────────────────────────────────────────────────────

def test_classify_source_returns_source_classification():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = classify_source("Some article text about Scandinavian bedroom design.")

    assert isinstance(result, SourceClassification)
    assert result.title == "Scandinavian Bedroom"


def test_classify_source_passes_text_to_llm():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        classify_source("TEXT_SENTINEL_VALUE")

        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        # The text must appear somewhere in the messages
        messages = call_kwargs.kwargs.get("messages") or call_kwargs.args[0]
        all_content = " ".join(
            m["content"] for m in messages if isinstance(m.get("content"), str)
        )
        assert "TEXT_SENTINEL_VALUE" in all_content


def test_classify_source_uses_source_classification_response_format():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        classify_source("some text")

        call_kwargs = mock_client.beta.chat.completions.parse.call_args
        response_format = (
            call_kwargs.kwargs.get("response_format")
            or call_kwargs.args[4]
            if len(call_kwargs.args) > 4
            else None
        )
        assert response_format is SourceClassification


def test_classify_source_entity_mentions_present():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = classify_source("some text")

    assert len(result.entity_mentions) == 1
    assert result.entity_mentions[0].name == "Sypialnia"


def test_classify_source_concept_mentions_present():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = classify_source("some text")

    assert len(result.concept_mentions) == 1
    assert result.concept_mentions[0].name == "neutral palette"


def test_classify_source_claims_present():
    from services.source_classifier import classify_source

    mock_response = _make_mock_response(FIXED_CLASSIFICATION)

    with patch("services.source_classifier._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_get_client.return_value = mock_client

        result = classify_source("some text")

    assert len(result.claims) == 1
    assert result.claims[0].polarity == "asserts"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/test_source_classifier.py -v
```

Expected: ImportError — `services.source_classifier` not found.

- [ ] **Step 3: Implement source_classifier**

Create `backend/services/source_classifier.py`:

```python
import os
from openai import OpenAI
from models.ingest_models import SourceClassification

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a knowledge extraction engine for a structured wiki.

Given an article or document, extract:
1. A clean title and short description.
2. Tags (3-10 lowercase keywords).
3. 2-5 questions the document answers.
4. 2-5 key takeaways.
5. Named entity mentions (Person, Org, Product, Place, Event) with their span positions in the TEXT.
6. Concept mentions (abstract ideas, design principles, techniques) with their span positions.
7. Factual claims — atomic statements with subject, confidence (0-1), and polarity (asserts/denies).

For spans: start/end are character offsets into the DOCUMENT TEXT. text is the exact substring.
For entities and concepts: canonical name only — no duplicates.
"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def classify_source(text: str, model: str = None) -> SourceClassification:
    """
    Stage 2: LLM structured output call.
    Returns a SourceClassification parsed from the document text.
    """
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    client = _get_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"DOCUMENT TEXT:\n\n{text}"},
        ],
        response_format=SourceClassification,
    )
    return response.choices[0].message.parsed
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/test_source_classifier.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/source_classifier.py backend/tests/services/test_source_classifier.py
git commit -m "feat(source_classifier): Stage 2 LLM structured output call via openai.beta.chat.completions.parse"
```

---

## Task 4: Stage 3 — Resolver (deterministic)

**Files:**
- Create: `backend/services/resolver.py`
- Create: `backend/tests/services/test_resolver.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/test_resolver.py`:

```python
import pytest
from services.wiki_store import WikiStore
from models.ingest_models import (
    SourceClassification, EntityMention, ConceptMention, ClaimExtraction,
)
from models.wiki_models import Entity, Concept, Span
from services.resolver import resolve_classification


@pytest.fixture
def store(tmp_path):
    return WikiStore(root=tmp_path)


@pytest.fixture
def simple_classification():
    return SourceClassification(
        title="Scandinavian Bedroom",
        description="Article about bedroom design.",
        tags=["bedroom"],
        questions=["What materials?"],
        key_takeaways=["Wood dominates."],
        entity_mentions=[
            EntityMention(
                name="Sypialnia",
                type="Place",
                aliases=["bedroom"],
                description="A Scandinavian bedroom.",
                span=Span(start=0, end=8, text="Sypialnia"),
            )
        ],
        concept_mentions=[
            ConceptMention(
                name="neutral palette",
                definition="Whites, beiges, and grays.",
                span=Span(start=10, end=24, text="neutral palette"),
            )
        ],
        claims=[
            ClaimExtraction(
                text="Sypialnia uses neutral palette.",
                subject_name="Sypialnia",
                subject_type="entity",
                span=Span(start=0, end=30, text="Sypialnia uses neutral palette."),
                confidence=0.9,
                polarity="asserts",
            )
        ],
    )


def test_resolve_creates_new_entity(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    assert result["entities_created"] == 1
    assert result["entities_merged"] == 0


def test_resolve_creates_new_concept(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    assert result["concepts_created"] == 1
    assert result["concepts_merged"] == 0


def test_resolve_entity_persisted_in_store(store, simple_classification):
    resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    entity = store.read_entity("sypialnia", "Place")
    assert entity is not None
    assert entity.type == "Place"


def test_resolve_concept_persisted_in_store(store, simple_classification):
    resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    concept = store.read_concept("neutral-palette")
    assert concept is not None


def test_resolve_merges_existing_entity(store, simple_classification):
    # Pre-create entity with same name
    existing = Entity(
        id="e_001", type="Place", aliases=["room"],
        description="Existing description.",
        questions=[], tags=["old-tag"],
    )
    store.write_entity(existing, slug="sypialnia")

    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    assert result["entities_created"] == 0
    assert result["entities_merged"] == 1
    # aliases should be merged
    entity = store.read_entity("sypialnia", "Place")
    assert "bedroom" in entity.aliases
    assert "room" in entity.aliases


def test_resolve_merges_existing_concept(store, simple_classification):
    existing = Concept(
        id="c_001",
        definition="Old definition.",
        examples=["white"], related=[],
        questions=[], tags=["old"],
    )
    store.write_concept(existing, slug="neutral-palette")

    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    assert result["concepts_created"] == 0
    assert result["concepts_merged"] == 1


def test_resolve_creates_claims(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    assert len(result["claims"]) == 1
    assert result["claims"][0].polarity == "asserts"


def test_resolve_creates_mentions_edges(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    # One edge per entity mention + one per concept mention
    assert len(result["edges"]) >= 1
    relations = [e.relation for e in result["edges"]]
    assert "mentions" in relations


def test_resolve_claim_subject_id_uses_resolved_entity_id(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    claim = result["claims"][0]
    # subject_id must start with "entity:" or "concept:"
    assert claim.subject_id.startswith("entity:") or claim.subject_id.startswith("concept:")


def test_resolve_entity_id_format(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    entity = store.read_entity("sypialnia", "Place")
    assert entity.id.startswith("e_")


def test_resolve_concept_id_format(store, simple_classification):
    result = resolve_classification(
        classification=simple_classification,
        source_id="src_001",
        store=store,
    )
    concept = store.read_concept("neutral-palette")
    assert concept.id.startswith("c_")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/test_resolver.py -v
```

Expected: ImportError — `services.resolver` not found.

- [ ] **Step 3: Implement resolver**

Create `backend/services/resolver.py`:

```python
from typing import Any, Dict, List
from services.wiki_store import WikiStore
from services._slug import slugify
from models.ingest_models import SourceClassification, EntityMention, ConceptMention
from models.wiki_models import Entity, Concept, Claim, Edge, Span


def resolve_classification(
    classification: SourceClassification,
    source_id: str,
    store: WikiStore,
) -> Dict[str, Any]:
    """
    Stage 3 (deterministic). Maps SourceClassification → WikiStore objects.
    Returns a dict with resolved entities, concepts, claims, edges, and counters.
    """
    entities_created = 0
    entities_merged = 0
    concepts_created = 0
    concepts_merged = 0

    # --- build a lookup of existing entity/concept counts for ID generation ---
    existing_entity_ids = {
        e.id
        for slug in store.list_sources()  # walk entities via index would be cleaner in Phase 3
        # We need a different approach: count existing IDs by reading them.
        # Simpler: use a sequential counter seeded by current store state.
        # We query the index JSON if present; otherwise count 0.
        # For Phase 2 we keep it simple: read claims for max id.
    }

    # Count existing entities by scanning 20-Entities dirs
    from services.wiki_store import ENTITIES_DIR
    from models.wiki_models import EntityType
    entity_count = _count_existing_entities(store)
    concept_count = _count_existing_concepts(store)
    claim_count = len(store.read_all_claims())
    edge_count = len(store.read_all_edges())

    # --- entity slug → resolved Entity map ---
    slug_to_entity: Dict[str, Entity] = {}

    for em in classification.entity_mentions:
        slug = slugify(em.name)
        if store.entity_exists(slug, em.type):
            new_entity = Entity(
                id=store.read_entity(slug, em.type).id,
                type=em.type,
                aliases=em.aliases,
                description=em.description,
                mentions_count=1,
                questions=classification.questions,
                tags=classification.tags,
            )
            store.merge_entity(new_entity, slug)
            entities_merged += 1
        else:
            entity_count += 1
            eid = f"e_{entity_count:03d}"
            new_entity = Entity(
                id=eid,
                type=em.type,
                aliases=em.aliases,
                description=em.description,
                mentions_count=1,
                questions=classification.questions,
                tags=classification.tags,
            )
            store.write_entity(new_entity, slug)
            entities_created += 1
        slug_to_entity[em.name] = store.read_entity(slug, em.type)

    # --- concept slug → resolved Concept map ---
    slug_to_concept: Dict[str, Concept] = {}

    for cm in classification.concept_mentions:
        slug = slugify(cm.name)
        if store.concept_exists(slug):
            new_concept = Concept(
                id=store.read_concept(slug).id,
                definition=cm.definition,
                examples=[],
                related=[],
                questions=classification.questions,
                tags=classification.tags,
            )
            store.merge_concept(new_concept, slug)
            concepts_merged += 1
        else:
            concept_count += 1
            cid = f"c_{concept_count:03d}"
            new_concept = Concept(
                id=cid,
                definition=cm.definition,
                examples=[],
                related=[],
                questions=classification.questions,
                tags=classification.tags,
            )
            store.write_concept(new_concept, slug)
            concepts_created += 1
        slug_to_concept[cm.name] = store.read_concept(slug)

    # --- build claims ---
    claims: List[Claim] = []
    for ce in classification.claims:
        claim_count += 1
        cid = f"cl_{claim_count:03d}"

        # resolve subject_id
        if ce.subject_type == "entity" and ce.subject_name in slug_to_entity:
            entity = slug_to_entity[ce.subject_name]
            subject_id = f"entity:{entity.id}"
        elif ce.subject_type == "concept" and ce.subject_name in slug_to_concept:
            concept = slug_to_concept[ce.subject_name]
            subject_id = f"concept:{concept.id}"
        else:
            # fallback: use raw name as subject
            subject_id = f"{ce.subject_type}:{slugify(ce.subject_name)}"

        claim = Claim(
            id=cid,
            text=ce.text,
            subject_id=subject_id,
            source_id=source_id,
            span=ce.span,
            confidence=ce.confidence,
            polarity=ce.polarity,
        )
        claims.append(claim)

    # --- build edges: source → entity (mentions relation) ---
    edges: List[Edge] = []

    for em in classification.entity_mentions:
        entity = slug_to_entity.get(em.name)
        if entity is None:
            continue
        edge_count += 1
        edge = Edge(
            id=f"ed_{edge_count:03d}",
            **{"from": f"source:{source_id}"},
            to=f"entity:{entity.id}",
            relation="mentions",
            source_id=source_id,
            span=em.span,
            confidence=1.0,
        )
        edges.append(edge)

    for cm in classification.concept_mentions:
        concept = slug_to_concept.get(cm.name)
        if concept is None:
            continue
        edge_count += 1
        edge = Edge(
            id=f"ed_{edge_count:03d}",
            **{"from": f"source:{source_id}"},
            to=f"concept:{concept.id}",
            relation="mentions",
            source_id=source_id,
            span=cm.span,
            confidence=1.0,
        )
        edges.append(edge)

    return {
        "entities_created": entities_created,
        "entities_merged": entities_merged,
        "concepts_created": concepts_created,
        "concepts_merged": concepts_merged,
        "claims": claims,
        "edges": edges,
        "entity_map": slug_to_entity,
        "concept_map": slug_to_concept,
    }


def _count_existing_entities(store: WikiStore) -> int:
    from services.wiki_store import ENTITIES_DIR
    base = store.root / "wiki" / ENTITIES_DIR
    if not base.exists():
        return 0
    return sum(1 for type_dir in base.iterdir() if type_dir.is_dir()
               for _ in type_dir.glob("*.md"))


def _count_existing_concepts(store: WikiStore) -> int:
    base = store.root / "wiki" / "10-Concepts"
    if not base.exists():
        return 0
    return sum(1 for _ in base.glob("*.md"))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/test_resolver.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/resolver.py backend/tests/services/test_resolver.py
git commit -m "feat(resolver): Stage 3 deterministic entity/concept/claim/edge resolution from SourceClassification"
```

---

## Task 5: Stage 4 — Conflict Detector (conditional LLM, mocked in tests)

**Files:**
- Create: `backend/services/conflict_detector.py`
- Create: `backend/tests/services/test_conflict_detector.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/test_conflict_detector.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from models.wiki_models import Claim, Span
from models.ingest_models import ConflictReport


def _make_claim(id, text, subject_id, polarity, source_id="src_001"):
    return Claim(
        id=id, text=text, subject_id=subject_id,
        source_id=source_id,
        span=Span(start=0, end=len(text), text=text[:20]),
        confidence=0.9, polarity=polarity,
    )


def test_no_conflicts_when_no_denying_claims():
    from services.conflict_detector import detect_conflicts

    new_claims = [
        _make_claim("cl_002", "Bedroom uses wood.", "entity:e_001", "asserts"),
    ]
    existing_claims = [
        _make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000"),
    ]

    result = detect_conflicts(new_claims, existing_claims)
    assert result == []


def test_no_conflicts_when_no_matching_subject():
    from services.conflict_detector import detect_conflicts

    new_claims = [
        _make_claim("cl_002", "Bathroom avoids wood.", "entity:e_002", "denies"),
    ]
    existing_claims = [
        _make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000"),
    ]
    # Different subject_id — no conflict possible
    result = detect_conflicts(new_claims, existing_claims)
    assert result == []


def test_skips_llm_when_no_potential_conflicts():
    from services.conflict_detector import detect_conflicts

    new_claims = [
        _make_claim("cl_002", "Bedroom uses white.", "entity:e_001", "asserts"),
    ]
    existing_claims = [
        _make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000"),
    ]

    with patch("services.conflict_detector._get_client") as mock_get_client:
        result = detect_conflicts(new_claims, existing_claims)
        mock_get_client.assert_not_called()

    assert result == []


def test_calls_llm_when_denies_claim_matches_subject():
    from services.conflict_detector import detect_conflicts

    new_claims = [
        _make_claim("cl_002", "Bedroom does not use wood.", "entity:e_001", "denies"),
    ]
    existing_claims = [
        _make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000"),
    ]

    mock_conflict = ConflictReport(
        new_claim_id="cl_002",
        existing_claim_id="cl_001",
        description="Direct contradiction on wood usage.",
    )

    # Build mock response
    mock_msg = MagicMock()

    class _FakeConflictList:
        conflicts: list = [mock_conflict]

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

    new_claims = [
        _make_claim("cl_002", "Bedroom does not use plastic.", "entity:e_001", "denies"),
    ]
    existing_claims = [
        _make_claim("cl_001", "Bedroom uses wood.", "entity:e_001", "asserts", "src_000"),
    ]

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/test_conflict_detector.py -v
```

Expected: ImportError — `services.conflict_detector` not found.

- [ ] **Step 3: Implement conflict_detector**

Create `backend/services/conflict_detector.py`:

```python
import os
from typing import List
from pydantic import BaseModel
from openai import OpenAI

from models.wiki_models import Claim
from models.ingest_models import ConflictReport

_client: OpenAI = None


class _ConflictList(BaseModel):
    conflicts: List[ConflictReport]


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def detect_conflicts(
    new_claims: List[Claim],
    existing_claims: List[Claim],
    model: str = None,
) -> List[ConflictReport]:
    """
    Stage 4 (conditional LLM). Only runs if:
      - At least one new_claim has polarity == "denies"
      - At least one existing_claim with same subject_id has polarity == "asserts"
    Returns list of ConflictReport (empty if no conflicts found or no LLM call needed).
    """
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    # Find new denying claims
    denying = [c for c in new_claims if c.polarity == "denies"]
    if not denying:
        return []

    # For each denying claim, find existing asserting claims on the same subject
    candidate_pairs = []
    for new_cl in denying:
        matching = [
            ec for ec in existing_claims
            if ec.subject_id == new_cl.subject_id and ec.polarity == "asserts"
        ]
        for ex_cl in matching:
            candidate_pairs.append((new_cl, ex_cl))

    if not candidate_pairs:
        return []

    # Build prompt for LLM
    pairs_text = "\n\n".join(
        f"NEW (id={nc.id}): \"{nc.text}\"\n"
        f"EXISTING (id={ec.id}): \"{ec.text}\""
        for nc, ec in candidate_pairs
    )
    prompt = (
        "You are a conflict detection assistant. "
        "For each pair of claims below, determine if they contradict each other. "
        "Return only genuine contradictions.\n\n"
        f"CLAIM PAIRS:\n{pairs_text}"
    )

    client = _get_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format=_ConflictList,
    )
    return response.choices[0].message.parsed.conflicts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/test_conflict_detector.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/services/conflict_detector.py backend/tests/services/test_conflict_detector.py
git commit -m "feat(conflict_detector): Stage 4 conditional LLM conflict detection between denying and asserting claims"
```

---

## Task 6: Stage 5 + Pipeline orchestration

**Files:**
- Create: `backend/services/ingest_pipeline.py`
- Create: `backend/tests/services/test_ingest_pipeline.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/services/test_ingest_pipeline.py`:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from services.wiki_store import WikiStore
from models.ingest_models import (
    SourceClassification, EntityMention, ConceptMention, ClaimExtraction, IngestResult
)
from models.wiki_models import Span


@pytest.fixture
def store(tmp_path):
    return WikiStore(root=tmp_path)


@pytest.fixture
def txt_file(tmp_path):
    p = tmp_path / "design_article.txt"
    p.write_text(
        "Scandinavian bedroom design uses neutral colors.\n"
        "Wood is the dominant material.",
        encoding="utf-8",
    )
    return p


FIXED_CLASSIFICATION = SourceClassification(
    title="Scandinavian Bedroom",
    description="Article about bedroom design.",
    tags=["bedroom", "scandinavian"],
    questions=["What colors?"],
    key_takeaways=["Neutral palette."],
    entity_mentions=[
        EntityMention(
            name="Sypialnia",
            type="Place",
            aliases=["bedroom"],
            description="A Scandinavian bedroom.",
            span=Span(start=0, end=8, text="Sypialnia"),
        )
    ],
    concept_mentions=[
        ConceptMention(
            name="neutral palette",
            definition="Whites, beiges, and grays.",
            span=Span(start=10, end=24, text="neutral palette"),
        )
    ],
    claims=[
        ClaimExtraction(
            text="Sypialnia uses neutral palette.",
            subject_name="Sypialnia",
            subject_type="entity",
            span=Span(start=0, end=30, text="Sypialnia uses neutral palette."),
            confidence=0.9,
            polarity="asserts",
        )
    ],
)


def _mock_classify(text: str, model=None):
    return FIXED_CLASSIFICATION


def test_pipeline_returns_ingest_result(txt_file, store):
    with patch("services.ingest_pipeline.classify_source", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    assert isinstance(result, IngestResult)
    assert result.status == "ok"


def test_pipeline_creates_source_in_store(txt_file, store):
    with patch("services.ingest_pipeline.classify_source", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    source = store.read_source(result.slug)
    assert source is not None
    assert source.title == "Scandinavian Bedroom"


def test_pipeline_creates_entity_in_store(txt_file, store):
    with patch("services.ingest_pipeline.classify_source", side_effect=_mock_classify):
        run_ingest(txt_file, store)
    entity = store.read_entity("sypialnia", "Place")
    assert entity is not None


def test_pipeline_creates_concept_in_store(txt_file, store):
    with patch("services.ingest_pipeline.classify_source", side_effect=_mock_classify):
        run_ingest(txt_file, store)
    concept = store.read_concept("neutral-palette")
    assert concept is not None


def test_pipeline_appends_claim(txt_file, store):
    with patch("services.ingest_pipeline.classify_source", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    claims = store.read_all_claims()
    assert len(claims) == result.claims_added
    assert result.claims_added == 1


def test_pipeline_appends_edges(txt_file, store):
    with patch("services.ingest_pipeline.classify_source", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    edges = store.read_all_edges()
    assert len(edges) >= 1
    assert result.edges_added >= 1


def test_pipeline_writes_log_entry(txt_file, store):
    with patch("services.ingest_pipeline.classify_source", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    log_path = store.root / "wiki" / "log.md"
    assert log_path.exists()
    log = log_path.read_text(encoding="utf-8")
    assert result.source_id in log


def test_pipeline_regenerates_index(txt_file, store):
    with patch("services.ingest_pipeline.classify_source", side_effect=_mock_classify):
        run_ingest(txt_file, store)
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    assert index_path.exists()
    idx = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(idx["sources"]) == 1


def test_pipeline_result_counts_match(txt_file, store):
    with patch("services.ingest_pipeline.classify_source", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    assert result.entities_created == 1
    assert result.concepts_created == 1
    assert result.llm_calls == 1  # only Stage 2 (no conflicts → Stage 4 skipped)


def test_pipeline_parsed_md_exists(txt_file, store):
    with patch("services.ingest_pipeline.classify_source", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    parsed_md = store.root / "raw" / result.slug / "parsed.md"
    assert parsed_md.exists()


def test_pipeline_duration_ms_positive(txt_file, store):
    with patch("services.ingest_pipeline.classify_source", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    assert result.duration_ms > 0


# helper to avoid repeating the import
def run_ingest(file_path, store):
    from services.ingest_pipeline import ingest_source
    return ingest_source(file_path=file_path, store=store)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/services/test_ingest_pipeline.py -v
```

Expected: ImportError — `services.ingest_pipeline` not found.

- [ ] **Step 3: Implement ingest_pipeline**

Create `backend/services/ingest_pipeline.py`:

```python
import time
from datetime import datetime
from pathlib import Path

from models.ingest_models import IngestResult
from models.wiki_models import Source
from services._slug import slugify, ensure_unique
from services.parser import parse_source
from services.source_classifier import classify_source
from services.resolver import resolve_classification
from services.conflict_detector import detect_conflicts
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from services.wiki_log import append_log_entry


def ingest_source(file_path: Path, store: WikiStore) -> IngestResult:
    """
    Orchestrates the 5-stage ingest pipeline.
    Stage 1: Parse
    Stage 2: Classify (LLM)
    Stage 3: Resolve (deterministic)
    Stage 4: Conflict Detection (conditional LLM)
    Stage 5: Save + Log + Reindex
    """
    t_start = time.time()
    llm_calls = 0
    file_path = Path(file_path)

    try:
        # ── Stage 1: Parse ────────────────────────────────────────────────────
        parsed = parse_source(file_path, store_root=store.root)
        slug = parsed["slug"]
        text = parsed["text"]

        # Ensure unique slug among existing sources
        existing_slugs = set(store.list_sources())
        slug = ensure_unique(slug, existing_slugs)

        # Generate source ID
        source_count = len(existing_slugs) + 1
        source_id = f"src_{source_count:03d}"

        # ── Stage 2: Classify (LLM) ────────────────────────────────────────────
        classification = classify_source(text)
        llm_calls += 1

        # ── Stage 3: Resolve (deterministic) ──────────────────────────────────
        resolved = resolve_classification(
            classification=classification,
            source_id=source_id,
            store=store,
        )

        # ── Stage 4: Conflict Detection (conditional LLM) ─────────────────────
        existing_claims = store.read_all_claims()
        conflicts = detect_conflicts(resolved["claims"], existing_claims)
        if conflicts:
            llm_calls += 1

        # ── Stage 5: Save + Log + Reindex ─────────────────────────────────────
        source = Source(
            id=source_id,
            title=classification.title,
            type=file_path.suffix.lstrip(".").lower(),
            raw_path=str(store.root / "raw" / slug / "parsed.md"),
            ingested_at=datetime.utcnow(),
            source_url=None,
            summary=classification.description,
            key_takeaways=classification.key_takeaways,
            questions=classification.questions,
            tags=classification.tags,
        )
        store.write_source(source, slug=slug)

        claims_added = 0
        for claim in resolved["claims"]:
            if store.append_claim(claim):
                claims_added += 1

        edges_added = 0
        for edge in resolved["edges"]:
            if store.append_edge(edge):
                edges_added += 1

        duration_ms = (time.time() - t_start) * 1000

        append_log_entry(
            store=store,
            op="ingest",
            source_id=source_id,
            details=(
                f"title={classification.title!r}, "
                f"+{resolved['entities_created']} entities, "
                f"+{resolved['concepts_created']} concepts, "
                f"+{claims_added} claims, "
                f"+{edges_added} edges, "
                f"{len(conflicts)} conflicts"
            ),
        )

        regenerate_index(store)

        return IngestResult(
            source_id=source_id,
            slug=slug,
            status="ok",
            entities_created=resolved["entities_created"],
            entities_merged=resolved["entities_merged"],
            concepts_created=resolved["concepts_created"],
            concepts_merged=resolved["concepts_merged"],
            claims_added=claims_added,
            edges_added=edges_added,
            conflicts=conflicts,
            duration_ms=duration_ms,
            llm_calls=llm_calls,
        )

    except Exception as exc:
        duration_ms = (time.time() - t_start) * 1000
        return IngestResult(
            source_id="",
            slug="",
            status="error",
            entities_created=0, entities_merged=0,
            concepts_created=0, concepts_merged=0,
            claims_added=0, edges_added=0,
            conflicts=[], duration_ms=duration_ms,
            llm_calls=llm_calls, error=str(exc),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/services/test_ingest_pipeline.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Run full test suite to confirm no regressions**

```bash
cd backend && pytest tests/ -v
```

Expected: all ≥ 50 tests green.

- [ ] **Step 6: Commit**

```bash
git add backend/services/ingest_pipeline.py backend/tests/services/test_ingest_pipeline.py
git commit -m "feat(ingest_pipeline): 5-stage orchestration (Parse→Classify→Resolve→Conflict→Save+Log+Reindex)"
```

---

## Task 7: FastAPI ingest router

**Files:**
- Create: `backend/api/ingest.py`
- Create: `backend/tests/api/__init__.py`
- Create: `backend/tests/api/test_ingest_api.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/api/__init__.py` (empty).

Create `backend/tests/api/test_ingest_api.py`:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from models.ingest_models import (
    IngestResult, SourceClassification, EntityMention,
    ConceptMention, ClaimExtraction,
)
from models.wiki_models import Span


FIXED_CLASSIFICATION = SourceClassification(
    title="Test Article",
    description="A test article.",
    tags=["test"],
    questions=["What is tested?"],
    key_takeaways=["Testing works."],
    entity_mentions=[],
    concept_mentions=[],
    claims=[],
)

FIXED_RESULT = IngestResult(
    source_id="src_001",
    slug="test-article",
    status="ok",
    entities_created=0, entities_merged=0,
    concepts_created=0, concepts_merged=0,
    claims_added=0, edges_added=0,
    conflicts=[], duration_ms=150.0, llm_calls=1,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def txt_upload_file(tmp_path):
    p = tmp_path / "test_article.txt"
    p.write_text("This is a test article about design.", encoding="utf-8")
    return p


def test_ingest_source_returns_200(client, txt_upload_file):
    with patch("api.ingest.ingest_source", return_value=FIXED_RESULT):
        with open(txt_upload_file, "rb") as f:
            response = client.post(
                "/api/ingest/source",
                files={"file": ("test_article.txt", f, "text/plain")},
            )
    assert response.status_code == 200


def test_ingest_source_response_shape(client, txt_upload_file):
    with patch("api.ingest.ingest_source", return_value=FIXED_RESULT):
        with open(txt_upload_file, "rb") as f:
            response = client.post(
                "/api/ingest/source",
                files={"file": ("test_article.txt", f, "text/plain")},
            )
    data = response.json()
    assert "source_id" in data
    assert "slug" in data
    assert "status" in data
    assert "entities_created" in data
    assert "claims_added" in data
    assert "duration_ms" in data


def test_ingest_source_status_ok(client, txt_upload_file):
    with patch("api.ingest.ingest_source", return_value=FIXED_RESULT):
        with open(txt_upload_file, "rb") as f:
            response = client.post(
                "/api/ingest/source",
                files={"file": ("test_article.txt", f, "text/plain")},
            )
    assert response.json()["status"] == "ok"


def test_ingest_source_rejects_unsupported_extension(client, tmp_path):
    bad_file = tmp_path / "file.odt"
    bad_file.write_bytes(b"data")
    with open(bad_file, "rb") as f:
        response = client.post(
            "/api/ingest/source",
            files={"file": ("file.odt", f, "application/octet-stream")},
        )
    assert response.status_code == 400


def test_ingest_source_calls_pipeline_once(client, txt_upload_file):
    with patch("api.ingest.ingest_source", return_value=FIXED_RESULT) as mock_pipeline:
        with open(txt_upload_file, "rb") as f:
            client.post(
                "/api/ingest/source",
                files={"file": ("test_article.txt", f, "text/plain")},
            )
    mock_pipeline.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/api/test_ingest_api.py -v
```

Expected: ImportError or 404 — `api.ingest` not found or route missing.

- [ ] **Step 3: Implement ingest API router**

Create `backend/api/ingest.py`:

```python
import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile
from services.ingest_pipeline import ingest_source
from services.wiki_store import WikiStore
from models.ingest_models import IngestResult

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
_WIKI_DATA_DIR = Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default"))


def _get_store() -> WikiStore:
    return WikiStore(root=_WIKI_DATA_DIR)


@router.post("/source", response_model=IngestResult)
async def ingest_source_endpoint(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type {ext!r}. Allowed: {', '.join(_ALLOWED_EXTENSIONS)}",
        )

    contents = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    try:
        # Rename temp file to preserve original extension for slug generation
        named_tmp = tmp_path.parent / file.filename
        tmp_path.rename(named_tmp)
        store = _get_store()
        result = ingest_source(file_path=named_tmp, store=store)
    finally:
        # Clean up — named_tmp may have already been moved by parser
        if named_tmp.exists():
            named_tmp.unlink()

    if result.status == "error":
        raise HTTPException(status_code=500, detail=result.error)

    return result
```

- [ ] **Step 4: Add router to main.py**

In `backend/main.py`, add:

```python
from api.ingest import router as ingest_router
# ...
app.include_router(ingest_router)
```

Add this import alongside the existing router imports. Place `app.include_router(ingest_router)` after `app.include_router(folders_router)`.

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && pytest tests/api/test_ingest_api.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/api/ingest.py backend/tests/api/__init__.py backend/tests/api/test_ingest_api.py backend/main.py
git commit -m "feat(api/ingest): POST /api/ingest/source endpoint with file upload and pipeline delegation"
```

---

## Task 8: FastAPI wiki read API

**Files:**
- Create: `backend/api/wiki.py`
- Create: `backend/tests/api/test_wiki_api.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/api/test_wiki_api.py`:

```python
import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from main import app
from services.wiki_store import WikiStore
from models.wiki_models import Source, Entity, Concept


@pytest.fixture
def client():
    return TestClient(app)


def test_get_wiki_sources_returns_list(client):
    response = client.get("/api/wiki/sources")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_wiki_entities_returns_list(client):
    response = client.get("/api/wiki/entities")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_wiki_concepts_returns_list(client):
    response = client.get("/api/wiki/concepts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_wiki_sources_shape(client, tmp_path, monkeypatch):
    """Write a source to a tmp store, patch the endpoint's store, verify shape."""
    from unittest.mock import patch

    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="Test Source", type="txt",
        raw_path="raw/test-source/parsed.md",
        ingested_at=datetime(2026, 4, 29, 10, 0, 0),
        summary="A test.", key_takeaways=["k1"],
        questions=["q1?"], tags=["t1"],
    )
    store.write_source(src, slug="test-source")

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/sources")

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "src_001"
    assert data[0]["title"] == "Test Source"


def test_get_wiki_entities_shape(client, tmp_path):
    from unittest.mock import patch

    store = WikiStore(root=tmp_path)
    entity = Entity(
        id="e_001", type="Place", aliases=["room"],
        description="A test place.", mentions_count=1,
        questions=[], tags=["space"],
    )
    store.write_entity(entity, slug="test-place")

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/entities")

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "e_001"
    assert data[0]["type"] == "Place"


def test_get_wiki_concepts_shape(client, tmp_path):
    from unittest.mock import patch

    store = WikiStore(root=tmp_path)
    concept = Concept(
        id="c_001", definition="A test concept.", examples=["ex1"],
        related=[], questions=[], tags=["abstract"],
    )
    store.write_concept(concept, slug="test-concept")

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/concepts")

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "c_001"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/api/test_wiki_api.py -v
```

Expected: 404 — `/api/wiki/sources` not found.

- [ ] **Step 3: Implement wiki API router**

Create `backend/api/wiki.py`:

```python
import os
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter
from services.wiki_store import WikiStore, ENTITIES_DIR

router = APIRouter(prefix="/api/wiki", tags=["wiki"])

_WIKI_DATA_DIR = Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default"))


def _get_store() -> WikiStore:
    return WikiStore(root=_WIKI_DATA_DIR)


@router.get("/sources", response_model=List[Dict[str, Any]])
def list_wiki_sources():
    store = _get_store()
    result = []
    for slug in store.list_sources():
        src = store.read_source(slug)
        if src:
            result.append({
                "slug": slug,
                "id": src.id,
                "title": src.title,
                "type": src.type,
                "ingested_at": src.ingested_at.isoformat(),
                "tags": src.tags,
                "questions": src.questions,
                "summary": src.summary,
                "key_takeaways": src.key_takeaways,
                "source_url": src.source_url,
            })
    return result


@router.get("/entities", response_model=List[Dict[str, Any]])
def list_wiki_entities():
    store = _get_store()
    result = []
    base = store.root / "wiki" / ENTITIES_DIR
    if not base.exists():
        return result
    for type_dir in sorted(base.iterdir()):
        if not type_dir.is_dir():
            continue
        for path in sorted(type_dir.glob("*.md")):
            slug = path.stem
            entity = store.read_entity(slug, type_dir.name)
            if entity:
                result.append({
                    "slug": slug,
                    "id": entity.id,
                    "type": entity.type,
                    "aliases": entity.aliases,
                    "description": entity.description,
                    "mentions_count": entity.mentions_count,
                    "tags": entity.tags,
                    "questions": entity.questions,
                })
    return result


@router.get("/concepts", response_model=List[Dict[str, Any]])
def list_wiki_concepts():
    store = _get_store()
    result = []
    concepts_dir = store.root / "wiki" / "10-Concepts"
    if not concepts_dir.exists():
        return result
    for path in sorted(concepts_dir.glob("*.md")):
        slug = path.stem
        concept = store.read_concept(slug)
        if concept:
            result.append({
                "slug": slug,
                "id": concept.id,
                "parent_concept": concept.parent_concept,
                "definition": concept.definition,
                "examples": concept.examples,
                "related": concept.related,
                "tags": concept.tags,
                "questions": concept.questions,
            })
    return result
```

- [ ] **Step 4: Add wiki router to main.py**

In `backend/main.py`, add:

```python
from api.wiki import router as wiki_router
# ...
app.include_router(wiki_router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && pytest tests/api/test_wiki_api.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Run full test suite**

```bash
cd backend && pytest tests/ -v
```

Expected: all tests green.

- [ ] **Step 7: Commit**

```bash
git add backend/api/wiki.py backend/tests/api/test_wiki_api.py backend/main.py
git commit -m "feat(api/wiki): GET /api/wiki/sources, /entities, /concepts read-only endpoints"
```

---

## Task 9: Backend self-review and full test run

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && pytest tests/ -v --tb=short
```

Expected: all tests green (≥ 60 tests).

- [ ] **Step 2: Verify no raw LLM calls in tests (all mocked)**

```bash
cd backend && grep -r "OpenAI\|openai" tests/ --include="*.py" | grep -v "mock\|Mock\|patch"
```

Expected: no lines output (all OpenAI usage in tests is behind a mock).

- [ ] **Step 3: Commit if any fixes were needed from the review**

```bash
git add -p
git commit -m "fix(tests): ensure all LLM calls are mocked in test suite"
```

---

## Task 10: Frontend — TypeScript types and API client extensions

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add types to types/index.ts**

Append to `frontend/src/types/index.ts`:

```typescript
// ── Wiki / Ingest types ────────────────────────────────────────────────────

export type WikiSourceStatus = "ok" | "partial" | "error";

export interface WikiSource {
  slug: string;
  id: string;
  title: string;
  type: string;
  ingested_at: string;
  tags: string[];
  questions: string[];
  summary: string;
  key_takeaways: string[];
  source_url?: string | null;
}

export interface WikiEntity {
  slug: string;
  id: string;
  type: "Person" | "Org" | "Product" | "Place" | "Event";
  aliases: string[];
  description: string;
  mentions_count: number;
  tags: string[];
  questions: string[];
}

export interface WikiConcept {
  slug: string;
  id: string;
  parent_concept?: string | null;
  definition: string;
  examples: string[];
  related: string[];
  tags: string[];
  questions: string[];
}

export interface ConflictReport {
  new_claim_id: string;
  existing_claim_id: string;
  description: string;
}

export interface IngestResult {
  source_id: string;
  slug: string;
  status: WikiSourceStatus;
  entities_created: number;
  entities_merged: number;
  concepts_created: number;
  concepts_merged: number;
  claims_added: number;
  edges_added: number;
  conflicts: ConflictReport[];
  duration_ms: number;
  llm_calls: number;
  error?: string | null;
}

// Extend Panel type
export type Panel =
  | "documents"
  | "chunks"
  | "embeddings"
  | "chat"
  | "metrics"
  | "tutorial"
  | "sources"
  | "ingest";
```

Note: The `Panel` type re-declaration extends the existing union. In practice, you will replace the existing `Panel` line in `types/index.ts` with the extended union above.

- [ ] **Step 2: Add API methods to client.ts**

Append to the `api` object in `frontend/src/api/client.ts`:

```typescript
  // Wiki
  listWikiSources: () => request<import("../types").WikiSource[]>("/wiki/sources"),
  listWikiEntities: () => request<import("../types").WikiEntity[]>("/wiki/entities"),
  listWikiConcepts: () => request<import("../types").WikiConcept[]>("/wiki/concepts"),

  // Ingest
  ingestSource: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<import("../types").IngestResult>("/ingest/source", {
      method: "POST",
      body: form,
    });
  },
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat(frontend/types): add WikiSource, WikiEntity, WikiConcept, IngestResult types and api client methods"
```

---

## Task 11: Frontend — SourcesPanel component

**Files:**
- Create: `frontend/src/components/wiki/SourcesPanel.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Create SourcesPanel**

Create `frontend/src/components/wiki/SourcesPanel.tsx`:

```tsx
import { useState, useEffect, useRef } from "react";
import { Upload, RefreshCw, FileText, Tag, Clock } from "lucide-react";
import { api } from "../../api/client";
import type { WikiSource, IngestResult } from "../../types";

export function SourcesPanel() {
  const [sources, setSources] = useState<WikiSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [lastResult, setLastResult] = useState<IngestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function fetchSources() {
    setLoading(true);
    try {
      const data = await api.listWikiSources();
      setSources(data);
    } catch {
      setError("Failed to load sources.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchSources();
  }, []);

  async function handleFile(file: File) {
    setUploading(true);
    setError(null);
    setLastResult(null);
    try {
      const result = await api.ingestSource(file);
      setLastResult(result);
      if (result.status !== "error") {
        await fetchSources();
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ingest failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="p-6 h-full flex gap-6">
      {/* Left panel: upload zone + result */}
      <div className="w-80 shrink-0 space-y-4">
        <h2 className="font-semibold text-sm">Ingest New Source</h2>

        {/* Drop zone */}
        <div
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const f = e.dataTransfer.files[0];
            if (f) handleFile(f);
          }}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            dragging
              ? "border-primary bg-primary/5"
              : "border-border hover:border-primary/50"
          }`}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
          <Upload className="w-8 h-8 mx-auto mb-2 text-muted-foreground" />
          {uploading ? (
            <p className="text-sm text-muted-foreground">Ingesting…</p>
          ) : (
            <>
              <p className="text-sm font-medium">Drop file or click to ingest</p>
              <p className="text-xs text-muted-foreground mt-1">PDF, DOCX, TXT</p>
            </>
          )}
        </div>

        {error && (
          <p className="text-xs text-red-500">{error}</p>
        )}

        {/* Last ingest result */}
        {lastResult && (
          <div className={`rounded-lg border p-3 text-xs space-y-1 ${
            lastResult.status === "ok"
              ? "border-green-500/40 bg-green-500/5"
              : "border-red-500/40 bg-red-500/5"
          }`}>
            <p className="font-medium">
              {lastResult.status === "ok" ? "Ingested" : "Error"}: {lastResult.slug}
            </p>
            <p>Entities: +{lastResult.entities_created} created, {lastResult.entities_merged} merged</p>
            <p>Concepts: +{lastResult.concepts_created} created, {lastResult.concepts_merged} merged</p>
            <p>Claims: +{lastResult.claims_added} | Edges: +{lastResult.edges_added}</p>
            <p>LLM calls: {lastResult.llm_calls} | {lastResult.duration_ms.toFixed(0)} ms</p>
            {lastResult.conflicts.length > 0 && (
              <p className="text-yellow-600">
                {lastResult.conflicts.length} conflict(s) detected
              </p>
            )}
            {lastResult.error && (
              <p className="text-red-500">{lastResult.error}</p>
            )}
          </div>
        )}
      </div>

      {/* Right panel: sources list */}
      <div className="flex-1 border rounded-lg bg-card border-border overflow-auto p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm">Sources ({sources.length})</h3>
          <button
            onClick={fetchSources}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </button>
        </div>

        {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

        {!loading && sources.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No sources ingested yet. Upload a file to begin.
          </p>
        )}

        <div className="space-y-2">
          {sources.map((src) => (
            <div
              key={src.id}
              className="border border-border rounded-md p-3 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-start gap-2">
                <FileText className="w-4 h-4 mt-0.5 text-muted-foreground shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{src.title}</p>
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{src.summary}</p>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    {src.tags.slice(0, 4).map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-0.5 text-xs bg-muted px-1.5 py-0.5 rounded"
                      >
                        <Tag className="w-2.5 h-2.5" />
                        {tag}
                      </span>
                    ))}
                    <span className="flex items-center gap-0.5 text-xs text-muted-foreground ml-auto">
                      <Clock className="w-2.5 h-2.5" />
                      {new Date(src.ingested_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add Sources entry to Sidebar.tsx**

In `frontend/src/components/layout/Sidebar.tsx`, add the Sources and Ingest nav items. Add these imports and entries:

```tsx
import { FileText, Layers, ScatterChart, MessageSquare, BarChart2, BookOpen, Database, Zap } from "lucide-react";
```

And add to the `NAV` array (after `tutorial`):

```tsx
{ id: "sources" as Panel, label: "Sources", icon: Database },
{ id: "ingest" as Panel, label: "Ingest", icon: Zap },
```

- [ ] **Step 3: Add panel rendering to App.tsx**

In `frontend/src/App.tsx`, add these imports and panel renderings:

```tsx
import { SourcesPanel } from "./components/wiki/SourcesPanel";
import { IngestPipelinePanel } from "./components/wiki/IngestPipelinePanel";
// ...
{activePanel === "sources" && <SourcesPanel />}
{activePanel === "ingest" && <IngestPipelinePanel />}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/wiki/SourcesPanel.tsx frontend/src/App.tsx frontend/src/components/layout/Sidebar.tsx
git commit -m "feat(frontend): SourcesPanel with drag-drop ingest upload and sources list"
```

---

## Task 12: Frontend — IngestPipelinePanel component

**Files:**
- Create: `frontend/src/components/wiki/IngestPipelinePanel.tsx`

- [ ] **Step 1: Create IngestPipelinePanel**

Create `frontend/src/components/wiki/IngestPipelinePanel.tsx`:

```tsx
import { useState } from "react";
import { CheckCircle, Circle, Loader, AlertCircle, Upload, Brain, GitMerge, Shield, Save } from "lucide-react";
import { api } from "../../api/client";
import type { IngestResult } from "../../types";

type StageStatus = "idle" | "running" | "done" | "error" | "skipped";

interface Stage {
  id: number;
  name: string;
  description: string;
  icon: React.ElementType;
  status: StageStatus;
  detail?: string;
}

const INITIAL_STAGES: Stage[] = [
  {
    id: 1, name: "Parse", icon: Upload,
    description: "Extract text from file. Write parsed.md + manifest.json.",
    status: "idle",
  },
  {
    id: 2, name: "Classify", icon: Brain,
    description: "LLM structured output: entities, concepts, claims.",
    status: "idle",
  },
  {
    id: 3, name: "Resolve", icon: GitMerge,
    description: "Map mentions to wiki store. Create or merge.",
    status: "idle",
  },
  {
    id: 4, name: "Conflicts", icon: Shield,
    description: "Conditional LLM: check denying claims vs existing assertions.",
    status: "idle",
  },
  {
    id: 5, name: "Save + Reindex", icon: Save,
    description: "Write source, claims, edges. Append log. Regenerate index.",
    status: "idle",
  },
];

function StageRow({ stage }: { stage: Stage }) {
  const Icon = stage.icon;
  const colors: Record<StageStatus, string> = {
    idle: "text-muted-foreground",
    running: "text-blue-500 animate-pulse",
    done: "text-green-500",
    error: "text-red-500",
    skipped: "text-muted-foreground opacity-50",
  };
  const StatusIcon = {
    idle: Circle,
    running: Loader,
    done: CheckCircle,
    error: AlertCircle,
    skipped: Circle,
  }[stage.status];

  return (
    <div className={`flex items-start gap-3 p-3 rounded-md border ${
      stage.status === "running" ? "border-blue-500/30 bg-blue-500/5" :
      stage.status === "done" ? "border-green-500/30 bg-green-500/5" :
      stage.status === "error" ? "border-red-500/30 bg-red-500/5" :
      "border-border"
    }`}>
      <div className={`mt-0.5 ${colors[stage.status]}`}>
        <StatusIcon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <Icon className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-sm font-medium">Stage {stage.id}: {stage.name}</span>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5">{stage.description}</p>
        {stage.detail && (
          <p className={`text-xs mt-1 ${stage.status === "error" ? "text-red-500" : "text-green-600"}`}>
            {stage.detail}
          </p>
        )}
      </div>
    </div>
  );
}

export function IngestPipelinePanel() {
  const [stages, setStages] = useState<Stage[]>(INITIAL_STAGES);
  const [result, setResult] = useState<IngestResult | null>(null);
  const [running, setRunning] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  function setStageStatus(id: number, status: StageStatus, detail?: string) {
    setStages((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status, detail } : s))
    );
  }

  async function handleIngest() {
    if (!selectedFile || running) return;
    setRunning(true);
    setResult(null);
    setStages(INITIAL_STAGES);

    // Simulate stage-by-stage progress (server is black-box; we animate while waiting)
    setStageStatus(1, "running");
    await new Promise((r) => setTimeout(r, 200));
    setStageStatus(1, "done", "Text extracted.");

    setStageStatus(2, "running");
    await new Promise((r) => setTimeout(r, 300));

    setStageStatus(3, "running");

    let ingestResult: IngestResult;
    try {
      ingestResult = await api.ingestSource(selectedFile);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Unknown error";
      setStageStatus(2, "error", msg);
      setRunning(false);
      return;
    }

    if (ingestResult.status === "error") {
      setStageStatus(2, "error", ingestResult.error ?? "Pipeline error");
      setRunning(false);
      return;
    }

    setStageStatus(2, "done", `${ingestResult.llm_calls} LLM call(s)`);
    setStageStatus(3, "done",
      `+${ingestResult.entities_created} entities, +${ingestResult.concepts_created} concepts`
    );

    if (ingestResult.conflicts.length > 0) {
      setStageStatus(4, "done",
        `${ingestResult.conflicts.length} conflict(s) detected`
      );
    } else {
      setStageStatus(4, "skipped", "No conflicts — skipped");
    }

    setStageStatus(5, "done",
      `+${ingestResult.claims_added} claims, +${ingestResult.edges_added} edges, index updated`
    );

    setResult(ingestResult);
    setRunning(false);
  }

  return (
    <div className="p-6 h-full flex gap-6">
      {/* Left: file selector + trigger */}
      <div className="w-72 shrink-0 space-y-4">
        <h2 className="font-semibold text-sm">Pipeline Visualizer</h2>
        <p className="text-xs text-muted-foreground">
          Select a file and run the ingest pipeline to see each stage execute in real time.
        </p>

        <div className="space-y-2">
          <label className="block text-xs font-medium">File</label>
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            className="block w-full text-xs text-muted-foreground file:mr-2 file:py-1 file:px-2 file:rounded file:border file:border-border file:text-xs file:bg-muted hover:file:bg-muted/80"
            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <button
          onClick={handleIngest}
          disabled={!selectedFile || running}
          className="w-full py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
        >
          {running ? "Running…" : "Run Ingest Pipeline"}
        </button>

        {result && result.status === "ok" && (
          <div className="text-xs space-y-1 border border-border rounded-md p-3">
            <p className="font-medium text-green-600">Pipeline complete</p>
            <p>Source: <code className="font-mono">{result.slug}</code></p>
            <p>{result.duration_ms.toFixed(0)} ms total</p>
          </div>
        )}
      </div>

      {/* Right: stage list */}
      <div className="flex-1 space-y-2">
        <h3 className="font-semibold text-sm mb-3">5-Stage Pipeline</h3>
        {stages.map((stage) => (
          <StageRow key={stage.id} stage={stage} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/wiki/IngestPipelinePanel.tsx
git commit -m "feat(frontend): IngestPipelinePanel with 5-stage visualization and animated progress"
```

---

## Task 13: Final integration check

- [ ] **Step 1: Run complete backend test suite**

```bash
cd backend && pytest tests/ -v --tb=short
```

Expected: all tests green. New total should be ≥ 60 tests.

- [ ] **Step 2: Verify the full test count compared to Phase 1 baseline**

```bash
cd backend && pytest tests/ --co -q | tail -5
```

Expected output ends with something like `62 tests collected`.

- [ ] **Step 3: Start the backend and verify endpoints respond**

```bash
cd backend && uvicorn main:app --reload --port 8000
```

In a second terminal:
```bash
curl -s http://localhost:8000/api/wiki/sources | python -m json.tool
curl -s http://localhost:8000/api/wiki/entities | python -m json.tool
curl -s http://localhost:8000/api/wiki/concepts | python -m json.tool
```

Expected: all return `[]` (empty store) with HTTP 200.

- [ ] **Step 4: Commit final Phase 2 integration tag**

```bash
git add -A
git commit -m "feat(phase-2): complete ingest pipeline — 5 stages, API endpoints, frontend panels" --allow-empty
git tag phase-2-complete
```

---

## Self-Review Checklist (post-execution, before merging Phase 2)

- [ ] All backend tests pass (`pytest tests/ -v`) with ≥ 60 tests green
- [ ] No real OpenAI API calls in tests (all `_get_client()` are mocked via `patch`)
- [ ] `parser.py` raises `ValueError` for unsupported extensions
- [ ] `resolver.py` generates IDs with the `e_NNN`, `c_NNN`, `cl_NNN`, `ed_NNN` format
- [ ] `conflict_detector.py` returns `[]` without calling LLM when no denying claims exist
- [ ] `ingest_pipeline.py` catches all stage exceptions and returns `status="error"`
- [ ] `POST /api/ingest/source` returns 400 for `.odt` and similar unsupported types
- [ ] `GET /api/wiki/sources`, `/entities`, `/concepts` return empty lists on a fresh store (no 500)
- [ ] `SourcesPanel` drag-drop zone accepts PDF/DOCX/TXT and shows IngestResult summary
- [ ] `IngestPipelinePanel` shows all 5 stages and animates through them on a successful run
- [ ] `Sidebar.tsx` shows "Sources" and "Ingest" nav items with correct icons
- [ ] Frontend compiles with no TypeScript errors (`npm run build` from `frontend/`)
- [ ] Phase 1 tests still all green — no regressions (`pytest tests/services/ -v`)

---

## What Phase 2 explicitly does NOT do

- No semantic search or RAG query pipeline (Phase 3).
- No URL/web crawl ingestion (uses existing `web_crawler.py` in Phase 3 or later).
- No Lint workflow (Phase 6).
- No removal of legacy chunker/embeddings services (Phase 9).
- No graph visualization (Phase 5).
- The `WIKI_DATA_DIR` env var defaults to `wiki_data/default` — no multi-tenant or per-user isolation.

---

## Done criterion for Phase 2

A developer can:

1. `cd backend && pytest tests/ -v` → all green (≥ 60 tests)
2. Start the server: `uvicorn main:app --reload`
3. Upload a `.txt` file to `POST /api/ingest/source` (using curl or Postman) and receive an `IngestResult` with `status: "ok"`
4. Call `GET /api/wiki/sources` and see the ingested source listed
5. Open the React app, navigate to "Sources", drag-drop a file, and see the ingest result summary
6. Navigate to "Ingest", select a file, click "Run", and watch all 5 stages animate green

When all backend tests pass and the two frontend panels work end-to-end with the real API, Phase 3 (Retrieval) can begin.

---

### Critical Files for Implementation

- `/c/Users/Konrad/Documents/__projects_and_git_repo_clones/RAG-2.0-Karpathy-Method/backend/services/ingest_pipeline.py`
- `/c/Users/Konrad/Documents/__projects_and_git_repo_clones/RAG-2.0-Karpathy-Method/backend/services/resolver.py`
- `/c/Users/Konrad/Documents/__projects_and_git_repo_clones/RAG-2.0-Karpathy-Method/backend/models/ingest_models.py`
- `/c/Users/Konrad/Documents/__projects_and_git_repo_clones/RAG-2.0-Karpathy-Method/backend/api/ingest.py`
- `/c/Users/Konrad/Documents/__projects_and_git_repo_clones/RAG-2.0-Karpathy-Method/frontend/src/components/wiki/SourcesPanel.tsx`