import os
import time
import uuid
from datetime import datetime
from typing import List, Generator, Dict, Any
from openai import OpenAI
from models.metrics import QueryMetrics, SessionMetrics

_client: OpenAI = None

# GPT-4o-mini pricing per 1M tokens (USD)
_PRICING = {
    "gpt-4o-mini": {"prompt": 0.150, "completion": 0.600},
    "gpt-4o": {"prompt": 5.0, "completion": 15.0},
}

_session_metrics: SessionMetrics = SessionMetrics(
    total_queries=0, total_tokens=0, total_cost_usd=0.0, queries=[]
)

_last_query_metrics: Dict[str, Any] = {}


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def stream_chat(
    full_prompt: str,
    query: str,
    embedding_ms: float = 0.0,
    retrieval_ms: float = 0.0,
    temperature: float = 0.0,
) -> Generator[str, None, None]:
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    client = _get_client()
    start = time.time()

    prompt_tokens = 0
    completion_tokens = 0
    full_response = ""

    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": full_prompt}],
        stream=True,
        stream_options={"include_usage": True},
        temperature=temperature,
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            token = chunk.choices[0].delta.content
            full_response += token
            yield token

        if chunk.usage:
            prompt_tokens = chunk.usage.prompt_tokens
            completion_tokens = chunk.usage.completion_tokens

    llm_ms = (time.time() - start) * 1000

    # Fallback token count if usage not in stream
    if prompt_tokens == 0:
        from services.token_counter import count_tokens
        prompt_tokens = count_tokens(full_prompt)
        completion_tokens = count_tokens(full_response)

    pricing = _PRICING.get(model, {"prompt": 0.150, "completion": 0.600})
    cost = (prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]) / 1_000_000

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
        estimated_cost_usd=cost,
    )

    global _session_metrics, _last_query_metrics
    _session_metrics.total_queries += 1
    _session_metrics.total_tokens += qm.total_tokens
    _session_metrics.total_cost_usd += cost
    _session_metrics.queries.append(qm)
    _last_query_metrics = qm.model_dump()


def get_session_metrics() -> SessionMetrics:
    return _session_metrics


def reset_session_metrics() -> None:
    global _session_metrics, _last_query_metrics
    _session_metrics = SessionMetrics(
        total_queries=0, total_tokens=0, total_cost_usd=0.0, queries=[]
    )
    _last_query_metrics = {}
