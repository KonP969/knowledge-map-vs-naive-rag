from unittest.mock import patch
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from main import app
from services.wiki_store import WikiStore
from models.wiki_models import Source
from models.ingest_models import IngestResult


@pytest.fixture
def client():
    return TestClient(app)


def _fake_ingest_factory(store):
    """Returns an ingest_source stand-in that writes a real Source so set_source_folder works."""
    def _fake_ingest(file_path, store):  # signature matches ingest_source(file_path=, store=)
        slug = "scraped-article"
        store.write_source(Source(
            id="src_900", title="Scraped", type="txt", raw_path="raw/x/parsed.md",
            ingested_at=datetime(2026, 6, 9), summary="s",
            key_takeaways=[], questions=[], tags=[],
        ), slug=slug)
        return IngestResult(
            source_id="src_900", slug=slug, status="ok",
            entities_created=0, entities_merged=0, concepts_created=0, concepts_merged=0,
            claims_added=0, edges_added=0, conflicts=[], duration_ms=1.0, llm_calls=0,
        )
    return _fake_ingest


def test_crawl_assigns_folder_to_scraped_source(client, tmp_path):
    store = WikiStore(root=tmp_path)
    fake_crawl = {"articles": [{"title": "A", "url": "http://x/a", "text": "body " * 50}], "error": None}
    with patch("api.crawl.crawl_url", return_value=fake_crawl), \
         patch("api.crawl._get_store", return_value=store), \
         patch("api.crawl.ingest_source", side_effect=_fake_ingest_factory(store)):
        resp = client.post("/api/crawl/ingest", json={"url": "http://x/blog", "max_articles": 5, "folder": "Blog PORTA"})
        _ = resp.text  # consume the streamed body
    assert resp.status_code == 200
    assert store.read_source("scraped-article").folder == "Blog PORTA"


def test_crawl_without_folder_leaves_source_unfiled(client, tmp_path):
    store = WikiStore(root=tmp_path)
    fake_crawl = {"articles": [{"title": "A", "url": "http://x/a", "text": "body " * 50}], "error": None}
    with patch("api.crawl.crawl_url", return_value=fake_crawl), \
         patch("api.crawl._get_store", return_value=store), \
         patch("api.crawl.ingest_source", side_effect=_fake_ingest_factory(store)):
        resp = client.post("/api/crawl/ingest", json={"url": "http://x/blog", "max_articles": 5})
        _ = resp.text
    assert store.read_source("scraped-article").folder is None


def test_crawl_folder_assignment_failure_is_non_fatal(client, tmp_path):
    store = WikiStore(root=tmp_path)
    fake_crawl = {"articles": [{"title": "A", "url": "http://x/a", "text": "body " * 50}], "error": None}
    with patch("api.crawl.crawl_url", return_value=fake_crawl), \
         patch("api.crawl._get_store", return_value=store), \
         patch("api.crawl.ingest_source", side_effect=_fake_ingest_factory(store)), \
         patch.object(store, "set_source_folder", side_effect=RuntimeError("disk error")):
        resp = client.post("/api/crawl/ingest", json={"url": "http://x/blog", "max_articles": 5, "folder": "Blog"})
        body = resp.text
    assert resp.status_code == 200
    assert '"status": "ok"' in body  # article still reported ok despite folder failure


def test_crawl_max_articles_accepts_100_rejects_101(client):
    with patch("api.crawl.crawl_url", return_value={"articles": [], "error": "stop"}):
        ok = client.post("/api/crawl/ingest", json={"url": "http://x/blog", "max_articles": 100})
    assert ok.status_code == 200
    bad = client.post("/api/crawl/ingest", json={"url": "http://x/blog", "max_articles": 101})
    assert bad.status_code == 422
