from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import numpy as np
from sklearn.decomposition import PCA
from models.chunk import Chunk
from services.embeddings_service import embed_texts, embed_query
from services.vector_store import add_chunks, get_all_embeddings, query_chunks, delete_by_document
from api.chunks import get_chunks_for_document
from api.documents import get_document_name

router = APIRouter(prefix="/api/embeddings", tags=["embeddings"])


class EmbedRequest(BaseModel):
    document_id: str


class EmbeddingPoint(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    x: float
    y: float
    content_preview: str


class SimilarityRequest(BaseModel):
    chunk_id_a: str
    chunk_id_b: str


class EmbeddingStatus(BaseModel):
    document_id: str
    chunk_count: int


def _compute_status() -> List[EmbeddingStatus]:
    data = get_all_embeddings()
    counts: Dict[str, int] = {}
    for meta in data["metadatas"]:
        doc_id = meta.get("document_id") or ""
        if not doc_id:
            continue
        counts[doc_id] = counts.get(doc_id, 0) + 1
    return [EmbeddingStatus(document_id=doc_id, chunk_count=count) for doc_id, count in counts.items()]


@router.get("/status", response_model=List[EmbeddingStatus])
def get_embedding_status():
    return _compute_status()


@router.delete("/by-document/{document_id}")
def delete_embeddings_by_document(document_id: str):
    delete_by_document(document_id)
    return {"deleted": document_id}


@router.post("/generate")
def generate_embeddings(req: EmbedRequest):
    chunks: List[Chunk] = get_chunks_for_document(req.document_id)
    if not chunks:
        raise HTTPException(404, "No chunks found for this document. Generate chunks first.")

    texts = [c.content for c in chunks]
    embeddings, elapsed_ms = embed_texts(texts)

    chunk_ids = [c.id for c in chunks]
    doc_name = get_document_name(req.document_id)
    metadatas = [
        {"document_id": c.document_id, "document_name": doc_name, "index": c.index, "char_count": c.char_count}
        for c in chunks
    ]

    add_chunks(
        chunk_ids=chunk_ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )

    return {
        "embedded_count": len(chunks),
        "elapsed_ms": elapsed_ms,
        "model": "text-embedding-3-small",
    }


@router.get("/visualize", response_model=List[EmbeddingPoint])
def visualize_embeddings():
    data = get_all_embeddings()
    if not data["ids"]:
        return []

    embeddings = np.array(data["embeddings"])
    if embeddings.shape[0] < 2:
        coords = np.zeros((embeddings.shape[0], 2))
    else:
        n_components = min(2, embeddings.shape[0])
        pca = PCA(n_components=n_components)
        coords = pca.fit_transform(embeddings)
        if coords.shape[1] == 1:
            coords = np.column_stack([coords, np.zeros(len(coords))])

    points = []
    for i, chunk_id in enumerate(data["ids"]):
        meta = data["metadatas"][i]
        points.append(EmbeddingPoint(
            chunk_id=chunk_id,
            document_id=meta.get("document_id", ""),
            document_name=meta.get("document_name") or meta.get("document_id", "")[:12],
            x=float(coords[i, 0]),
            y=float(coords[i, 1]),
            content_preview=data["documents"][i][:100],
        ))
    return points


@router.get("/similarity")
def get_similarity(chunk_id_a: str, chunk_id_b: str):
    data = get_all_embeddings()

    def find_embedding(cid: str):
        for i, c in enumerate(data["ids"]):
            if c == cid:
                return np.array(data["embeddings"][i])
        return None

    emb_a = find_embedding(chunk_id_a)
    emb_b = find_embedding(chunk_id_b)

    if emb_a is None or emb_b is None:
        raise HTTPException(404, "One or both chunk IDs not found in vector store")

    norm_a = np.linalg.norm(emb_a)
    norm_b = np.linalg.norm(emb_b)
    if norm_a == 0 or norm_b == 0:
        raise HTTPException(400, "Cannot compute similarity with zero vectors")
    cosine = float(np.dot(emb_a, emb_b) / (norm_a * norm_b))
    return {"chunk_id_a": chunk_id_a, "chunk_id_b": chunk_id_b, "cosine_similarity": cosine}
