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
