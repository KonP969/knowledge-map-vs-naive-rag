from pydantic import BaseModel
from typing import List


class QueryMetrics(BaseModel):
    query_id: str
    timestamp: str
    query: str
    embedding_ms: float = 0.0
    retrieval_ms: float = 0.0
    llm_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class SessionMetrics(BaseModel):
    total_queries: int
    total_tokens: int
    total_cost_usd: float
    queries: List[QueryMetrics]
