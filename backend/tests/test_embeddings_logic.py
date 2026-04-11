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
