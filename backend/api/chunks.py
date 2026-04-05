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

# Parent-child: child_chunk_id -> parent content (larger context window)
_parent_store: Dict[str, str] = {}

PARENT_SIZE_MULTIPLIER = 3


def _build_parent_map(text: str, child_chunks: List[Chunk], child_chunk_size: int) -> Dict[str, str]:
    """For each child chunk, find/create a larger parent chunk and return mapping."""
    parent_size = max(800, child_chunk_size * PARENT_SIZE_MULTIPLIER)
    raw_parents = chunk_fixed_size(text, chunk_size=parent_size, overlap=0)
    mapping: Dict[str, str] = {}
    for child in child_chunks:
        parent_content = None
        for p in raw_parents:
            if p["start_char"] <= child.start_char < p["end_char"]:
                parent_content = p["content"]
                break
        if parent_content is None and raw_parents:
            # fallback: nearest parent
            nearest = min(raw_parents, key=lambda p: abs(p["start_char"] - child.start_char))
            parent_content = nearest["content"]
        if parent_content:
            mapping[child.id] = parent_content
    return mapping


def _build_chunk_response(raw_chunks: List[dict], doc_id: str, overlap: int = 0, chunk_size: int = 0) -> ChunkResponse:
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
    overlap_pct = round(overlap / chunk_size * 100, 1) if chunk_size > 0 else 0.0
    stats = ChunkStats(
        count=len(chunks),
        avg_length=sum(lengths) / len(lengths) if lengths else 0.0,
        min_length=min(lengths) if lengths else 0,
        max_length=max(lengths) if lengths else 0,
        overlap_pct=overlap_pct,
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

    response = _build_chunk_response(raw, req.document_id, overlap=req.overlap, chunk_size=req.chunk_size)
    _chunks_store[req.document_id] = response

    # Build parent-child mapping for richer context during retrieval
    parent_map = _build_parent_map(text, response.chunks, req.chunk_size or 500)
    _parent_store.update(parent_map)

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


def get_parent_content(child_id: str) -> str | None:
    """Returns parent (larger context) chunk content for a given child chunk ID."""
    return _parent_store.get(child_id)
