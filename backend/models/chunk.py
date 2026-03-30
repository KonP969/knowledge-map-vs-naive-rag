from pydantic import BaseModel
from typing import List, Optional


class Chunk(BaseModel):
    id: str
    document_id: str
    content: str
    index: int
    char_count: int
    token_count: int
    start_char: int
    end_char: int


class ChunkRequest(BaseModel):
    document_id: str
    strategy: str = "fixed"  # "fixed" | "recursive" | "semantic"
    chunk_size: int = 500
    overlap: int = 50
    separators: Optional[List[str]] = None


class ChunkStats(BaseModel):
    count: int
    avg_length: float
    min_length: int
    max_length: int
    overlap_pct: float


class ChunkResponse(BaseModel):
    chunks: List[Chunk]
    stats: ChunkStats
