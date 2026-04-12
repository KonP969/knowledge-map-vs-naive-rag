from services.vector_store import reset_collection, add_chunks, get_all_embeddings
import pytest


def test_reset_collection_clears_data():
    """reset_collection() must remove all previously added data."""
    add_chunks(
        chunk_ids=["test-id-1"],
        embeddings=[[0.1, 0.2, 0.3]],
        documents=["test document"],
        metadatas=[{"document_id": "doc-1", "document_name": "test.txt", "index": 0, "char_count": 13}],
    )
    data_before = get_all_embeddings()
    assert "test-id-1" in data_before["ids"]

    reset_collection()

    data_after = get_all_embeddings()
    assert data_after["ids"] == []


def test_reset_collection_works_when_called_before_any_add():
    """reset_collection() must not crash and must return empty store even if called cold."""
    reset_collection()  # called with _client potentially None
    data = get_all_embeddings()
    assert data["ids"] == []


def test_get_status_returns_doc_counts():
    """Status should list each document_id with its chunk count."""
    reset_collection()
    add_chunks(
        chunk_ids=["c1", "c2", "c3"],
        embeddings=[[0.1] * 3, [0.2] * 3, [0.3] * 3],
        documents=["chunk one", "chunk two", "chunk three"],
        metadatas=[
            {"document_id": "doc-A", "document_name": "a.txt", "index": 0, "char_count": 9},
            {"document_id": "doc-A", "document_name": "a.txt", "index": 1, "char_count": 9},
            {"document_id": "doc-B", "document_name": "b.txt", "index": 0, "char_count": 11},
        ],
    )

    from api.embeddings import _compute_status
    status = _compute_status()
    by_doc = {s.document_id: s.chunk_count for s in status}
    assert by_doc["doc-A"] == 2
    assert by_doc["doc-B"] == 1


def test_get_status_empty():
    """Status must return an empty list when no embeddings exist."""
    reset_collection()
    from api.embeddings import _compute_status
    assert _compute_status() == []
