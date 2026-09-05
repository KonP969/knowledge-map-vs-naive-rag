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


def _make_source(store, slug, src_id, folder=None):
    src = Source(
        id=src_id, title=f"Title {src_id}", type="txt",
        raw_path=f"raw/{slug}/parsed.md",
        ingested_at=datetime(2026, 4, 29, 10, 0, 0),
        summary="A test.", key_takeaways=[], questions=[], tags=[],
        folder=folder,
    )
    store.write_source(src, slug=slug)


def test_get_wiki_sources_includes_folder(client, tmp_path):
    from unittest.mock import patch

    store = WikiStore(root=tmp_path)
    _make_source(store, "with-folder", "src_001", folder="Praca")
    _make_source(store, "no-folder", "src_002")

    with patch("api.wiki._get_store", return_value=store):
        response = client.get("/api/wiki/sources")

    data = sorted(response.json(), key=lambda d: d["id"])
    assert data[0]["folder"] == "Praca"
    assert data[1]["folder"] is None


def test_set_sources_folder_bulk_assigns(client, tmp_path):
    from unittest.mock import patch

    store = WikiStore(root=tmp_path)
    _make_source(store, "a", "src_001")
    _make_source(store, "b", "src_002")
    _make_source(store, "c", "src_003")

    with patch("api.wiki._get_store", return_value=store):
        response = client.post(
            "/api/wiki/sources/folder",
            json={"slugs": ["a", "b"], "folder": "Wnętrza"},
        )

    assert response.status_code == 200
    assert response.json()["updated"] == 2
    assert store.read_source("a").folder == "Wnętrza"
    assert store.read_source("b").folder == "Wnętrza"
    assert store.read_source("c").folder is None


def test_set_sources_folder_null_clears(client, tmp_path):
    from unittest.mock import patch

    store = WikiStore(root=tmp_path)
    _make_source(store, "a", "src_001", folder="Wnętrza")

    with patch("api.wiki._get_store", return_value=store):
        response = client.post(
            "/api/wiki/sources/folder",
            json={"slugs": ["a"], "folder": None},
        )

    assert response.status_code == 200
    assert store.read_source("a").folder is None


def test_set_sources_folder_unknown_slug_returns_404(client, tmp_path):
    from unittest.mock import patch

    store = WikiStore(root=tmp_path)
    _make_source(store, "a", "src_001")

    with patch("api.wiki._get_store", return_value=store):
        response = client.post(
            "/api/wiki/sources/folder",
            json={"slugs": ["a", "ghost"], "folder": "X"},
        )

    assert response.status_code == 404


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


def test_get_claims_by_id_returns_requested_claims_with_span(client, tmp_path):
    from unittest.mock import patch
    from models.wiki_models import Claim, Span

    store = WikiStore(root=tmp_path)
    store.append_claim(Claim(id="cl_001", text="A fact.", subject_id="entity:e_001", source_id="src_001",
                             span=Span(start=2, end=5, text="fac"), confidence=0.9, polarity="asserts"))
    store.append_claim(Claim(id="cl_002", text="B fact.", subject_id="entity:e_002", source_id="src_001",
                             span=Span(start=0, end=1, text="B"), confidence=0.8, polarity="denies"))

    with patch("api.wiki._get_store", return_value=store):
        resp = client.get("/api/wiki/claims-by-id?ids=cl_002,cl_999")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1  # cl_999 missing -> skipped
    assert data[0]["id"] == "cl_002"
    assert data[0]["span"] == {"start": 0, "end": 1, "text": "B"}
    assert data[0]["polarity"] == "denies"


def test_get_claims_by_id_empty_returns_empty(client):
    resp = client.get("/api/wiki/claims-by-id?ids=")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_claim_context_returns_window_around_fragment(client, tmp_path):
    from unittest.mock import patch
    from models.wiki_models import Claim, Span

    store = WikiStore(root=tmp_path)
    src = Source(id="src_001", title="Book", type="pdf", raw_path="raw/book/parsed.md",
                 ingested_at=datetime(2026, 6, 1), summary="S", key_takeaways=[], questions=[], tags=[])
    store.write_source(src, slug="book")
    raw_file = store.root / "raw" / "book" / "parsed.md"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    # PDF artifact "Pe nguin" — locate must still find the clean span text
    raw_file.write_text("AAAA Pe nguin supports copyright. BBBB", encoding="utf-8")
    store.append_claim(Claim(id="cl_001", text="...", subject_id="entity:e_001", source_id="src_001",
                             span=Span(start=999, end=1000, text="Penguin supports copyright"),
                             confidence=0.9, polarity="asserts"))

    with patch("api.wiki._get_store", return_value=store):
        resp = client.get("/api/wiki/claim-context?id=cl_001&window=5")

    assert resp.status_code == 200
    d = resp.json()
    assert d["located"] is True
    assert d["match"].replace(" ", "") == "Penguinsupportscopyright"
    assert d["source_title"] == "Book"
    assert d["slug"] == "book"
    assert "AAAA" in d["before"]


def test_get_claim_context_missing_claim_returns_404(client, tmp_path):
    from unittest.mock import patch
    store = WikiStore(root=tmp_path)
    with patch("api.wiki._get_store", return_value=store):
        resp = client.get("/api/wiki/claim-context?id=cl_999")
    assert resp.status_code == 404


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
    # Variant #2: claim carries its verbatim span (offsets + literal text into raw source)
    assert data["claims"][0]["span"] == {"start": 0, "end": 14, "text": "Room is neutral."}
    assert len(data["edges"]) == 1
    assert data["edges"][0]["id"] == "edge_001"


def test_delete_source_prunes_its_claims_from_semantic_index(client, tmp_path):
    # Deleting a source must also drop its claim vectors, or the index keeps stale
    # vectors whose ids get recycled on the next ingest (wrong semantic results).
    from unittest.mock import patch
    from models.wiki_models import Claim, Span
    from services.semantic_index import add_claims_to_index, load_claim_index

    store = WikiStore(root=tmp_path)
    _make_source(store, "doomed", "src_001")
    claim = Claim(id="cl_001", text="doomed fact", subject_id="concept:c_001",
                  source_id="src_001", span=Span(start=0, end=1, text="x"),
                  confidence=1.0, polarity="asserts")
    store.append_claim(claim)
    add_claims_to_index(store, [claim], embed_fn=lambda batch: [[1.0, 0.0] for _ in batch])

    assert "cl_001" in load_claim_index(store)

    with patch("api.wiki._get_store", return_value=store):
        resp = client.delete("/api/wiki/source/doomed")
    assert resp.status_code == 200
    assert "cl_001" not in load_claim_index(store)


def test_delete_source_prunes_orphaned_entities_and_concepts(client, tmp_path):
    from unittest.mock import patch
    from models.wiki_models import Claim, Edge, Span
    store = WikiStore(root=tmp_path)
    _make_source(store, "doomed", "src_001")
    store.write_entity(Entity(id="e_001", type="Product", aliases=[], description="d",
                              mentions_count=1, questions=["q?"], tags=["t"]), slug="only-here")
    store.write_concept(Concept(id="c_001", definition="d", examples=[], related=[],
                                questions=[], tags=[]), slug="only-concept")
    store.append_claim(Claim(id="cl_001", text="t", subject_id="entity:e_001",
                             source_id="src_001", span=Span(start=0, end=1, text="x"),
                             confidence=0.9, polarity="asserts"))
    store.append_edge(Edge(id="ed_001", **{"from": "entity:e_001"}, to="concept:c_001",
                           relation="associated_with", source_id="src_001",
                           span=Span(start=0, end=1, text="x"), confidence=0.8))

    with patch("api.wiki._get_store", return_value=store):
        resp = client.delete("/api/wiki/source/doomed")

    assert resp.status_code == 200
    body = resp.json()
    assert body["pruned_entities"] == ["e_001"]
    assert body["pruned_concepts"] == ["c_001"]
    assert store.read_entity("only-here", "Product") is None
    assert store.read_concept("only-concept") is None


def test_delete_source_keeps_nodes_referenced_by_another_source(client, tmp_path):
    from unittest.mock import patch
    from models.wiki_models import Claim, Span
    store = WikiStore(root=tmp_path)
    _make_source(store, "doomed", "src_001")
    _make_source(store, "survivor", "src_002")
    store.write_entity(Entity(id="e_001", type="Product", aliases=[], description="d",
                              mentions_count=2, questions=[], tags=[]), slug="shared")
    store.append_claim(Claim(id="cl_001", text="from doomed", subject_id="entity:e_001",
                             source_id="src_001", span=Span(start=0, end=1, text="x"),
                             confidence=0.9, polarity="asserts"))
    store.append_claim(Claim(id="cl_002", text="from survivor", subject_id="entity:e_001",
                             source_id="src_002", span=Span(start=0, end=1, text="y"),
                             confidence=0.9, polarity="asserts"))

    with patch("api.wiki._get_store", return_value=store):
        resp = client.delete("/api/wiki/source/doomed")

    assert resp.status_code == 200
    assert resp.json()["pruned_entities"] == []
    assert store.read_entity("shared", "Product") is not None


def test_delete_source_regenerates_index(client, tmp_path):
    import json
    from unittest.mock import patch
    from services.wiki_index import regenerate_index
    store = WikiStore(root=tmp_path)
    _make_source(store, "doomed", "src_001")
    _make_source(store, "survivor", "src_002")
    regenerate_index(store)
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    assert len(json.loads(index_path.read_text(encoding="utf-8"))["sources"]) == 2

    with patch("api.wiki._get_store", return_value=store):
        resp = client.delete("/api/wiki/source/doomed")

    assert resp.status_code == 200
    remaining = json.loads(index_path.read_text(encoding="utf-8"))["sources"]
    assert [s["slug"] for s in remaining] == ["survivor"]
