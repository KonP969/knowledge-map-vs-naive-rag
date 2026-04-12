from pydantic import BaseModel
from typing import List


class TokenCounts(BaseModel):
    system: int
    context: int
    query: int
    total: int


class PromptData(BaseModel):
    system_message: str
    context_block: str
    user_query: str
    full_prompt: str
    token_counts: TokenCounts


class QueryMetrics(BaseModel):
    query_id: str
    timestamp: str
    query: str
    chunking_ms: float = 0.0
    embedding_ms: float
    retrieval_ms: float
    llm_ms: float
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class SessionMetrics(BaseModel):
    total_queries: int
    total_tokens: int
    total_cost_usd: float
    queries: List[QueryMetrics]
