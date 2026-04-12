import os
import chromadb
from typing import List, Dict, Any, Optional

_client: Optional[chromadb.ClientAPI] = None
_collection = None
COLLECTION_NAME = "rag_chunks"


def _get_collection():
    global _client, _collection
    if _collection is None:
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        _client = chromadb.PersistentClient(path=persist_dir)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_chunks(
    chunk_ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: List[Dict[str, Any]],
) -> None:
    col = _get_collection()
    col.upsert(
        ids=chunk_ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def query_chunks(
    query_embedding: List[float],
    n_results: int = 5,
    where: Optional[Dict] = None,
) -> Dict[str, Any]:
    col = _get_collection()
    count = col.count()
    params = {
        "query_embeddings": [query_embedding],
        "n_results": min(n_results, count) if count > 0 else 1,
        "include": ["documents", "metadatas", "distances", "embeddings"],
    }
    if where:
        params["where"] = where
    return col.query(**params)


def delete_by_document(document_id: str) -> None:
    col = _get_collection()
    results = col.get(where={"document_id": document_id})
    if results["ids"]:
        col.delete(ids=results["ids"])


def get_all_embeddings() -> Dict[str, Any]:
    col = _get_collection()
    return col.get(include=["embeddings", "metadatas", "documents"])


def reset_collection() -> None:
    global _client, _collection
    _collection = None          # force _get_collection to re-open _client from disk
    _get_collection()
    try:
        _client.delete_collection(COLLECTION_NAME)
    except ValueError:
        pass  # collection did not exist yet — that is fine
    _collection = None          # force _get_collection to recreate the collection
    _get_collection()
