import httpx
from typing import Tuple, List, Dict, Optional

BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 90.0


def ask(query: str, top_k: int = 8) -> Tuple[str, List[Dict]]:
    """Wysyła pytanie do RAG. Zwraca (pelna_odpowiedz, retrieved_chunks)."""
    full_answer = _stream_chat(query, top_k)
    retrieved_chunks = _get_retrieval()
    return full_answer, retrieved_chunks


def _stream_chat(query: str, top_k: int) -> str:
    """Pobiera SSE stream z POST /api/chat. Parsuje przez buffering na double-newline."""
    tokens: List[str] = []
    url = f"{BASE_URL}/api/chat"
    body = {"query": query, "top_k": top_k}

    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        with client.stream("POST", url, json=body) as response:
            response.raise_for_status()
            buffer = ""
            done = False
            for raw_bytes in response.iter_bytes():
                if done:
                    break
                buffer += raw_bytes.decode("utf-8", errors="replace")
                while "\n\n" in buffer:
                    event_str, buffer = buffer.split("\n\n", 1)
                    for line in event_str.split("\n"):
                        if line.startswith("data: "):
                            payload = line[6:]
                        elif line.startswith("data:"):
                            payload = line[5:]
                        else:
                            continue
                        if payload == "[DONE]":
                            done = True
                            break
                        if payload:
                            tokens.append(payload)

    return "".join(tokens)


def _get_retrieval() -> List[Dict]:
    """Pobiera chunki retrieval z ostatniego query."""
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{BASE_URL}/api/chat/retrieval")
        response.raise_for_status()
        return response.json()


def get_documents() -> List[Dict]:
    """Pobiera liste dokumentow. Zwraca List[DocumentMeta dict]."""
    with httpx.Client(timeout=10.0) as client:
        # Trailing slash wymagany przez FastAPI router prefix /api/documents
        response = client.get(f"{BASE_URL}/api/documents/")
        response.raise_for_status()
        return response.json()


def get_chunks(document_id: str) -> List[Dict]:
    """Pobiera chunki dla dokumentu. Zwraca liste Chunk dict."""
    with httpx.Client(timeout=15.0) as client:
        response = client.get(f"{BASE_URL}/api/chunks/{document_id}")
        response.raise_for_status()
        data = response.json()
        return data.get("chunks", [])


def get_last_query_metrics() -> Optional[Dict]:
    """Pobiera metryki ostatniego query z /api/metrics/session."""
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{BASE_URL}/api/metrics/session")
        response.raise_for_status()
        data = response.json()
        queries = data.get("queries", [])
        return queries[-1] if queries else None


def health_check() -> bool:
    """Sprawdza czy backend dziala."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{BASE_URL}/health")
            return response.status_code == 200
    except Exception:
        return False
