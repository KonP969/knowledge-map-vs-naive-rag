from fastapi import APIRouter, HTTPException
from typing import List, Dict
from models.chunk import Chunk, ChunkRequest, ChunkResponse, ChunkStats
from services.chunkers.fixed_size import chunk_fixed_size
from services.chunkers.recursive import chunk_recursive
from services.chunkers.semantic import chunk_semantic
from services.token_counter import count_tokens
from api.documents import get_document_text
import uuid

router = APIRouter(prefix="/api/chunks", tags=["chunks"])

# In-memory: document_id -> ChunkResponse
_chunks_store: Dict[str, ChunkResponse] = {}


def _build_chunk_response(raw_chunks: List[dict], doc_id: str, overlap: int = 0) -> ChunkResponse:
    chunks = []
    for raw in raw_chunks:
        chunks.append(Chunk(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            content=raw["content"],
            index=raw["index"],
            char_count=len(raw["content"]),
            token_count=count_tokens(raw["content"]),
            start_char=raw["start_char"],
            end_char=raw["end_char"],
        ))

    lengths = [c.char_count for c in chunks]
    stats = ChunkStats(
        count=len(chunks),
        avg_length=sum(lengths) / len(lengths) if lengths else 0.0,
        min_length=min(lengths) if lengths else 0,
        max_length=max(lengths) if lengths else 0,
        overlap_pct=float(overlap),
    )
    return ChunkResponse(chunks=chunks, stats=stats)


@router.post("/generate", response_model=ChunkResponse)
def generate_chunks(req: ChunkRequest):
    text = get_document_text(req.document_id)

    if req.strategy == "fixed":
        raw = chunk_fixed_size(text, chunk_size=req.chunk_size, overlap=req.overlap)
    elif req.strategy == "recursive":
        seps = req.separators or ["\n\n", "\n", ". ", " "]
        raw = chunk_recursive(text, separators=seps, chunk_size=req.chunk_size)
    elif req.strategy == "semantic":
        raw = chunk_semantic(text)
    else:
        raise HTTPException(400, f"Unknown strategy: {req.strategy}")

    response = _build_chunk_response(raw, req.document_id, overlap=req.overlap)
    _chunks_store[req.document_id] = response
    return response


@router.get("/{document_id}", response_model=ChunkResponse)
def get_chunks(document_id: str):
    if document_id not in _chunks_store:
        raise HTTPException(404, "No chunks generated for this document yet")
    return _chunks_store[document_id]


def get_chunks_for_document(document_id: str) -> List[Chunk]:
    """Helper for embeddings service."""
    if document_id not in _chunks_store:
        return []
    return _chunks_store[document_id].chunks
