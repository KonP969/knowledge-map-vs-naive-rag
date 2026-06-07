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


# ── raw text ─────────────────────────────────────────────────────────────────

def test_read_raw_text_missing_source_returns_none(store):
    assert store.read_raw_text("nonexistent") is None


def test_read_raw_text_source_without_raw_file_returns_none(store, sample_source):
    store.write_source(sample_source, slug="skandynawska-sypialnia")
    # source exists but the raw parsed.md file was never created
    assert store.read_raw_text("skandynawska-sypialnia") is None


def test_read_raw_text_returns_file_content(store, sample_source):
    store.write_source(sample_source, slug="skandynawska-sypialnia")
    raw_file = store.root / "raw" / "skandynawska-sypialnia" / "parsed.md"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    full_text = "# Pełny artykuł\n\nDługa treść źródła, znacznie dłuższa niż streszczenie."
    raw_file.write_text(full_text, encoding="utf-8")
    assert store.read_raw_text("skandynawska-sypialnia") == full_text


# ── source folder (UX Round 3 #2) ────────────────────────────────────────────

def test_source_folder_defaults_to_none(store, sample_source):
    store.write_source(sample_source, slug="skandynawska-sypialnia")
    loaded = store.read_source("skandynawska-sypialnia")
    assert loaded.folder is None


def test_read_source_backward_compat_without_folder_field(store, sample_source):
    # A source file written before the `folder` field existed has no folder key.
    store.write_source(sample_source, slug="skandynawska-sypialnia")
    path = store._source_path("skandynawska-sypialnia")
    text = path.read_text(encoding="utf-8")
    assert "folder" not in text  # write must not emit folder when None
    loaded = store.read_source("skandynawska-sypialnia")
    assert loaded.folder is None


def test_set_source_folder_persists(store, sample_source):
    store.write_source(sample_source, slug="skandynawska-sypialnia")
    store.set_source_folder("skandynawska-sypialnia", "Wnętrza")
    loaded = store.read_source("skandynawska-sypialnia")
    assert loaded.folder == "Wnętrza"


def test_set_source_folder_none_clears(store, sample_source):
    store.write_source(sample_source, slug="skandynawska-sypialnia")
    store.set_source_folder("skandynawska-sypialnia", "Wnętrza")
    store.set_source_folder("skandynawska-sypialnia", None)
    loaded = store.read_source("skandynawska-sypialnia")
    assert loaded.folder is None


def test_set_source_folder_preserves_other_fields(store, sample_source):
    store.write_source(sample_source, slug="skandynawska-sypialnia")
    store.set_source_folder("skandynawska-sypialnia", "Wnętrza")
    loaded = store.read_source("skandynawska-sypialnia")
    assert loaded.title == sample_source.title
    assert loaded.questions == sample_source.questions
    assert loaded.tags == sample_source.tags


def test_set_source_folder_raises_when_missing(store):
    with pytest.raises(FileNotFoundError):
        store.set_source_folder("nonexistent", "Wnętrza")


# ── entity / concept / claim / edge ──────────────────────────────────────────

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
    store.append_claim(sample_claim)
    claims = store.read_all_claims()
    assert len(claims) == 1


def test_edges_dedup_by_tuple(store, sample_edge):
    store.append_edge(sample_edge)
    store.append_edge(sample_edge)
    edges = store.read_all_edges()
    assert len(edges) == 1


# ── merge operations ──────────────────────────────────────────────────────────

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


# ── Phase 6 deletes/updates ────────────────────────────────────────────────

def test_delete_claim_removes_line(tmp_path):
    store = WikiStore(root=tmp_path)
    c1 = Claim(id="cl_001", text="a", subject_id="entity:e_001", source_id="src_001",
               span=Span(start=0, end=1, text="a"), confidence=0.9, polarity="asserts")
    c2 = Claim(id="cl_002", text="b", subject_id="entity:e_001", source_id="src_001",
               span=Span(start=0, end=1, text="b"), confidence=0.9, polarity="asserts")
    store.append_claim(c1)
    store.append_claim(c2)

    deleted = store.delete_claim("cl_001")
    assert deleted is True

    remaining = store.read_all_claims()
    assert len(remaining) == 1
    assert remaining[0].id == "cl_002"


def test_delete_claim_returns_false_for_missing_id(tmp_path):
    store = WikiStore(root=tmp_path)
    assert store.delete_claim("cl_999") is False


def test_delete_claims_by_source_removes_only_that_source(tmp_path):
    store = WikiStore(root=tmp_path)
    a1 = Claim(id="cl_001", text="a1", subject_id="entity:e_001", source_id="src_001",
               span=Span(start=0, end=1, text="a"), confidence=0.9, polarity="asserts")
    a2 = Claim(id="cl_002", text="a2", subject_id="entity:e_001", source_id="src_001",
               span=Span(start=0, end=1, text="b"), confidence=0.9, polarity="asserts")
    b1 = Claim(id="cl_003", text="b1", subject_id="entity:e_002", source_id="src_002",
               span=Span(start=0, end=1, text="c"), confidence=0.9, polarity="asserts")
    store.append_claim(a1)
    store.append_claim(a2)
    store.append_claim(b1)

    removed = store.delete_claims_by_source("src_001")
    assert removed == 2

    remaining = store.read_all_claims()
    assert [c.id for c in remaining] == ["cl_003"]


def test_delete_claims_by_source_no_match_returns_zero(tmp_path):
    store = WikiStore(root=tmp_path)
    assert store.delete_claims_by_source("src_999") == 0


def test_delete_edges_by_source_removes_only_that_source(tmp_path):
    store = WikiStore(root=tmp_path)
    e1 = Edge(id="ed_001", **{"from": "source:src_001"}, to="entity:e_001",
              relation="mentions", source_id="src_001",
              span=Span(start=0, end=1, text="x"), confidence=1.0)
    e2 = Edge(id="ed_002", **{"from": "source:src_002"}, to="entity:e_002",
              relation="mentions", source_id="src_002",
              span=Span(start=0, end=1, text="y"), confidence=1.0)
    store.append_edge(e1)
    store.append_edge(e2)

    removed = store.delete_edges_by_source("src_001")
    assert removed == 1
    assert [e.id for e in store.read_all_edges()] == ["ed_002"]


def test_delete_edge_removes_line(tmp_path):
    store = WikiStore(root=tmp_path)
    e1 = Edge(id="ed_001", **{"from": "entity:a"}, to="entity:b",
              relation="mentions", source_id="src_001",
              span=Span(start=0, end=1, text="x"), confidence=0.9)
    e2 = Edge(id="ed_002", **{"from": "entity:c"}, to="entity:d",
              relation="mentions", source_id="src_001",
              span=Span(start=0, end=1, text="x"), confidence=0.9)
    store.append_edge(e1)
    store.append_edge(e2)

    assert store.delete_edge("ed_001") is True
    remaining = store.read_all_edges()
    assert len(remaining) == 1
    assert remaining[0].id == "ed_002"


def test_delete_jsonl_line_removes_line_and_creates_backup(tmp_path):
    store = WikiStore(root=tmp_path)
    path = store.root / "wiki" / "claims.jsonl"
    path.write_text("good1\nGARBAGE\ngood2\n", encoding="utf-8")

    store.delete_jsonl_line(path, line_no=2)

    assert path.read_text(encoding="utf-8") == "good1\ngood2\n"
    backup = path.with_suffix(".jsonl.bak")
    assert backup.exists()
    assert "GARBAGE" in backup.read_text(encoding="utf-8")


def test_delete_entity_removes_file(tmp_path):
    store = WikiStore(root=tmp_path)
    ent = Entity(id="e_001", type="Place", aliases=[], description="A long description with chars.",
                 mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(ent, slug="test")
    assert store.entity_exists("test", "Place")

    assert store.delete_entity("test", "Place") is True
    assert not store.entity_exists("test", "Place")


def test_delete_entity_returns_false_for_missing(tmp_path):
    store = WikiStore(root=tmp_path)
    assert store.delete_entity("nope", "Place") is False


def test_delete_concept_removes_file(tmp_path):
    store = WikiStore(root=tmp_path)
    c = Concept(id="c_001", definition="A long concept definition with characters.",
                examples=[], related=[], questions=["q?"], tags=[])
    store.write_concept(c, slug="test")
    assert store.concept_exists("test")
    assert store.delete_concept("test") is True
    assert not store.concept_exists("test")


def test_update_entity_description_persists(tmp_path):
    store = WikiStore(root=tmp_path)
    ent = Entity(id="e_001", type="Place", aliases=[], description="short",
                 mentions_count=0, questions=["q?"], tags=[])
    store.write_entity(ent, slug="test")

    new_desc = "A much longer and more descriptive description."
    store.update_entity_description("test", "Place", new_desc)

    reread = store.read_entity("test", "Place")
    assert reread.description == new_desc


def test_update_concept_description_persists(tmp_path):
    store = WikiStore(root=tmp_path)
    c = Concept(id="c_001", definition="short",
                examples=[], related=[], questions=["q?"], tags=[])
    store.write_concept(c, slug="test")

    new_def = "A longer concept definition with plenty of characters."
    store.update_concept_description("test", new_def)

    reread = store.read_concept("test")
    assert reread.definition == new_def


def test_update_entity_description_raises_when_missing(tmp_path):
    store = WikiStore(root=tmp_path)
    with pytest.raises(FileNotFoundError):
        store.update_entity_description("nope", "Place", "new desc")


def test_update_concept_description_raises_when_missing(tmp_path):
    store = WikiStore(root=tmp_path)
    with pytest.raises(FileNotFoundError):
        store.update_concept_description("nope", "new def")
