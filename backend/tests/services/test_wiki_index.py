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
