import os
import time
from typing import List, Tuple
from openai import OpenAI

_client: OpenAI = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def embed_texts(texts: List[str]) -> Tuple[List[List[float]], float]:
    """Returns (embeddings, elapsed_ms)."""
    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    start = time.time()
    client = _get_client()
    response = client.embeddings.create(model=model, input=texts)
    elapsed_ms = (time.time() - start) * 1000
    embeddings = [item.embedding for item in response.data]
    return embeddings, elapsed_ms


def embed_query(query: str) -> Tuple[List[float], float]:
    embeddings, ms = embed_texts([query])
    return embeddings[0], ms
