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
