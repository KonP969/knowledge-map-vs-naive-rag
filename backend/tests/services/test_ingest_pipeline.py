import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from services.wiki_store import WikiStore
from models.ingest_models import (
    SourceClassification, EntityMention, ConceptMention, ClaimExtraction, IngestResult
)
from models.wiki_models import Span


@pytest.fixture(autouse=True)
def _no_embed(monkeypatch):
    # ingest now updates the semantic index; keep these unit tests offline/fast.
    monkeypatch.setattr("services.ingest_pipeline.add_claims_to_index", lambda *a, **k: None)


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
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    assert isinstance(result, IngestResult)
    assert result.status == "ok"


def test_pipeline_creates_source_in_store(txt_file, store):
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    source = store.read_source(result.slug)
    assert source is not None
    assert source.title == "Scandinavian Bedroom"


def test_pipeline_creates_entity_in_store(txt_file, store):
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        run_ingest(txt_file, store)
    entity = store.read_entity("sypialnia", "Place")
    assert entity is not None


def test_pipeline_creates_concept_in_store(txt_file, store):
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        run_ingest(txt_file, store)
    concept = store.read_concept("neutral-palette")
    assert concept is not None


def test_pipeline_appends_claim(txt_file, store):
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    claims = store.read_all_claims()
    assert len(claims) == result.claims_added
    assert result.claims_added == 1


def test_pipeline_appends_edges(txt_file, store):
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    edges = store.read_all_edges()
    assert len(edges) >= 1
    assert result.edges_added >= 1


def test_pipeline_writes_log_entry(txt_file, store):
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    log_path = store.root / "wiki" / "log.md"
    assert log_path.exists()
    log = log_path.read_text(encoding="utf-8")
    assert result.source_id in log


def test_pipeline_regenerates_index(txt_file, store):
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        run_ingest(txt_file, store)
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    assert index_path.exists()
    idx = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(idx["sources"]) == 1


def test_pipeline_result_counts_match(txt_file, store):
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    assert result.entities_created == 1
    assert result.concepts_created == 1
    assert result.llm_calls == 1  # only Stage 2 (no conflicts → Stage 4 skipped)


def test_pipeline_parsed_md_exists(txt_file, store):
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    parsed_md = store.root / "raw" / result.slug / "parsed.md"
    assert parsed_md.exists()


def test_pipeline_duration_ms_positive(txt_file, store):
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        result = run_ingest(txt_file, store)
    assert result.duration_ms > 0


def test_pipeline_returns_error_on_parse_failure(store):
    from services.ingest_pipeline import ingest_source
    from pathlib import Path
    bad_path = Path("/nonexistent/file.txt")
    result = ingest_source(file_path=bad_path, store=store)
    assert result.status == "error"
    assert result.error is not None
    assert result.duration_ms >= 0


# helper to avoid repeating the import
def run_ingest(file_path, store):
    from services.ingest_pipeline import ingest_source
    return ingest_source(file_path=file_path, store=store)


def test_pipeline_logs_warning_when_semantic_index_update_fails(txt_file, store, monkeypatch, caplog):
    # The embed hook is non-fatal, but it must not fail silently: a swallowed
    # exception left the semantic index stale with no trace (blog-ingest regression).
    import logging

    def _boom(*a, **k):
        raise RuntimeError("embedding backend down")

    monkeypatch.setattr("services.ingest_pipeline.add_claims_to_index", _boom)
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        with caplog.at_level(logging.WARNING):
            from services.ingest_pipeline import ingest_source
            result = ingest_source(file_path=txt_file, store=store)

    assert result.status == "ok"  # still non-fatal
    assert any("semantic index" in r.message.lower() for r in caplog.records)


def test_failed_ingest_removes_its_raw_dir(txt_file, store):
    # A classify failure (e.g. no API key) used to leave an orphaned raw/<slug>/ behind.
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=RuntimeError("boom")):
        result = run_ingest(txt_file, store)
    assert result.status == "error"
    assert not (store.root / "raw" / "designarticle").exists()


def test_failed_ingest_keeps_a_raw_dir_it_did_not_create(txt_file, store):
    pre_existing = store.root / "raw" / "designarticle"
    pre_existing.mkdir(parents=True)
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=RuntimeError("boom")):
        run_ingest(txt_file, store)
    assert pre_existing.exists()


def test_same_filename_twice_does_not_overwrite_first_raw_copy(txt_file, store, tmp_path):
    with patch("services.ingest_pipeline.classify_source_chunked", side_effect=_mock_classify):
        first = run_ingest(txt_file, store)
        other = tmp_path / "other" / "design_article.txt"
        other.parent.mkdir()
        other.write_text("A different article with the same filename.", encoding="utf-8")
        second = run_ingest(other, store)

    assert (first.slug, second.slug) == ("designarticle", "designarticle-2")
    assert "Scandinavian" in (store.root / "raw" / "designarticle" / "parsed.md").read_text()
    assert "different" in (store.root / "raw" / "designarticle-2" / "parsed.md").read_text()
