import pytest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app
from models.ingest_models import IngestResult


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


def test_ingest_source_keeps_the_uploaded_filename(client, txt_upload_file):
    # The filename drives the slug; a UUID temp name used to replace it.
    seen = {}

    def _fake_ingest(file_path, store):
        seen["name"] = file_path.name
        return FIXED_RESULT

    with patch("api.ingest.ingest_source", side_effect=_fake_ingest):
        with open(txt_upload_file, "rb") as f:
            client.post(
                "/api/ingest/source",
                files={"file": ("My Notes.txt", f, "text/plain")},
            )
    assert seen["name"] == "My Notes.txt"


def test_ingest_source_falls_back_when_filename_cannot_be_slugified(client, txt_upload_file):
    seen = {}

    def _fake_ingest(file_path, store):
        seen["name"] = file_path.name
        return FIXED_RESULT

    with patch("api.ingest.ingest_source", side_effect=_fake_ingest):
        with open(txt_upload_file, "rb") as f:
            client.post("/api/ingest/source", files={"file": ("!!!.txt", f, "text/plain")})
    assert seen["name"] == "upload.txt"
