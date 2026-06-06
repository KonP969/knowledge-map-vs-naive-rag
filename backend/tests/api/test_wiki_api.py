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


def test_get_wiki_sources_shape(client, tmp_path):
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


def test_get_wiki_edges_returns_list(client):
    response = client.get("/api/wiki/edges")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_wiki_edges_shape(client, tmp_path):
    from unittest.mock import patch
    from models.wiki_models import Edge, Span

    store = WikiStore(root=tmp_path)
    edge = Edge(
        id="edge_001", **{"from": "entity:e_001"},
        to="concept:c_001", relation="associated_with",
        source_id="src_001",
        span=Span(start=0, end=10, text="bedroom"),
        confidence=0.8,
    )
    store.append_edge(edge)

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/edges")

    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "edge_001"
    assert data[0]["from"] == "entity:e_001"
    assert data[0]["to"] == "concept:c_001"
    assert data[0]["relation"] == "associated_with"
    assert data[0]["confidence"] == 0.8


def test_get_source_raw_returns_text(client, tmp_path):
    from unittest.mock import patch

    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="Test Source", type="txt",
        raw_path="raw/test-source/parsed.md",
        ingested_at=datetime(2026, 4, 29, 10, 0, 0),
        summary="A short summary.", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, slug="test-source")
    raw_file = store.root / "raw" / "test-source" / "parsed.md"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    full_text = "# Full article\n\nMuch longer original text than the summary."
    raw_file.write_text(full_text, encoding="utf-8")

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/source-raw?slug=test-source")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "test-source"
    assert data["title"] == "Test Source"
    assert data["raw_text"] == full_text


def test_get_source_raw_missing_source_returns_404(client, tmp_path):
    from unittest.mock import patch

    store = WikiStore(root=tmp_path)
    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/source-raw?slug=nonexistent")

    assert response.status_code == 404


def test_get_source_raw_missing_raw_file_returns_404(client, tmp_path):
    from unittest.mock import patch

    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="Test Source", type="txt",
        raw_path="raw/test-source/parsed.md",
        ingested_at=datetime(2026, 4, 29, 10, 0, 0),
        summary="A short summary.", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, slug="test-source")  # no raw file created

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/source-raw?slug=test-source")

    assert response.status_code == 404


def test_get_wiki_node_detail_invalid_id_returns_400(client):
    response = client.get("/api/wiki/node-detail?id=invalidnoprefix")
    assert response.status_code == 400


def test_get_wiki_node_detail_entity(client, tmp_path):
    from unittest.mock import patch
    from models.wiki_models import Entity, Source
    from services.wiki_index import regenerate_index

    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="T", type="txt",
        raw_path="r/x.md", ingested_at=datetime(2026, 5, 1),
        summary="S", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, slug="test-source")
    entity = Entity(
        id="e_001", type="Place", aliases=["room"],
        description="A room.", mentions_count=1,
        questions=["q?"], tags=["space"],
    )
    store.write_entity(entity, slug="test-room")
    regenerate_index(store)

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/node-detail?id=entity:e_001")

    assert response.status_code == 200
    data = response.json()
    assert data["node_type"] == "entity"
    assert data["entity_type"] == "Place"
    assert data["description"] == "A room."
    assert isinstance(data["claims"], list)
    assert isinstance(data["edges"], list)


def test_get_wiki_node_detail_concept(client, tmp_path):
    from unittest.mock import patch
    from models.wiki_models import Concept, Source
    from services.wiki_index import regenerate_index

    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="T", type="txt",
        raw_path="r/x.md", ingested_at=datetime(2026, 5, 1),
        summary="S", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, slug="test-source")
    concept = Concept(
        id="c_001", definition="Neutral colors palette.",
        examples=[], related=[], questions=["What?"], tags=["color"],
    )
    store.write_concept(concept, slug="neutral-palette")
    regenerate_index(store)

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/node-detail?id=concept:c_001")

    assert response.status_code == 200
    data = response.json()
    assert data["node_type"] == "concept"
    assert "neutral" in data["description"].lower()
    assert isinstance(data["claims"], list)
    assert isinstance(data["edges"], list)


def test_get_wiki_node_detail_includes_claims_and_edges(client, tmp_path):
    from unittest.mock import patch
    from models.wiki_models import Entity, Source, Claim, Edge, Span
    from services.wiki_index import regenerate_index

    store = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="T", type="txt",
        raw_path="r/x.md", ingested_at=datetime(2026, 5, 1),
        summary="S", key_takeaways=[], questions=[], tags=[],
    )
    store.write_source(src, slug="test-source")
    entity = Entity(
        id="e_001", type="Place", aliases=[],
        description="A room.", mentions_count=1,
        questions=[], tags=[],
    )
    store.write_entity(entity, slug="test-room")
    claim = Claim(
        id="cl_001", text="Room is neutral.",
        subject_id="entity:e_001", source_id="src_001",
        span=Span(start=0, end=14, text="Room is neutral."),
        confidence=0.9, polarity="asserts",
    )
    store.append_claim(claim)
    edge = Edge(
        id="edge_001", **{"from": "entity:e_001"},
        to="concept:c_001", relation="associated_with",
        source_id="src_001",
        span=Span(start=0, end=5, text="room"),
        confidence=0.8,
    )
    store.append_edge(edge)
    regenerate_index(store)

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/node-detail?id=entity:e_001")

    data = response.json()
    assert len(data["claims"]) == 1
    assert data["claims"][0]["id"] == "cl_001"
    assert len(data["edges"]) == 1
    assert data["edges"][0]["id"] == "edge_001"
