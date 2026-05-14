import uuid
from datetime import datetime
from models.metrics import QueryMetrics, SessionMetrics

_session_metrics: SessionMetrics = SessionMetrics(
    total_queries=0, total_tokens=0, total_cost_usd=0.0, queries=[]
)


def get_session_metrics() -> SessionMetrics:
    return _session_metrics


def reset_session_metrics() -> None:
    global _session_metrics
    _session_metrics = SessionMetrics(
        total_queries=0, total_tokens=0, total_cost_usd=0.0, queries=[]
    )


def record_query(
    query: str,
    embedding_ms: float = 0.0,
    retrieval_ms: float = 0.0,
    llm_ms: float = 0.0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    estimated_cost_usd: float = 0.0,
) -> None:
    """Record a completed query into session metrics."""
    global _session_metrics
    qm = QueryMetrics(
        query_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        query=query,
        embedding_ms=embedding_ms,
        retrieval_ms=retrieval_ms,
        llm_ms=llm_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        estimated_cost_usd=estimated_cost_usd,
    )
    _session_metrics.total_queries += 1
    _session_metrics.total_tokens += qm.total_tokens
    _session_metrics.total_cost_usd += estimated_cost_usd
    _session_metrics.queries.append(qm)
