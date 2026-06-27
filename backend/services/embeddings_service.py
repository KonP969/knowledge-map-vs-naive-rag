"""Batch text embedding via OpenAI, with an injectable embed function for tests.

Used to embed claim texts (index build) and the user's question (query time). The network call
is isolated behind `embed_fn` so unit tests run offline."""
import os
from typing import Callable, List, Optional

from openai import OpenAI

EmbedFn = Callable[[List[str]], List[List[float]]]

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def _openai_embed(batch: List[str]) -> List[List[float]]:
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    resp = _get_client().embeddings.create(model=model, input=batch)
    return [d.embedding for d in resp.data]


def embed_texts(
    texts: List[str],
    *,
    embed_fn: Optional[EmbedFn] = None,
    batch_size: int = 256,
) -> List[List[float]]:
    """Embed texts in order, batching the underlying calls. Returns one vector per input."""
    fn = embed_fn or _openai_embed
    if not texts:
        return []
    out: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        out.extend(fn(texts[i:i + batch_size]))
    return out


def embed_query(text: str, *, embed_fn: Optional[EmbedFn] = None) -> List[float]:
    """Embed a single query string."""
    return embed_texts([text], embed_fn=embed_fn)[0]
