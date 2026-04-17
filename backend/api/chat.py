import time
import re as _re
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from models.chunk import Chunk
from services.embeddings_service import embed_query
from services.vector_store import query_chunks
from services.prompt_builder import build_prompt, DEFAULT_SYSTEM_PROMPT
from services.llm_service import stream_chat
from services.query_expander import expand_query
from api.chunks import get_parent_content

router = APIRouter(prefix="/api/chat", tags=["chat"])

_last_retrieval: List[Dict[str, Any]] = []
_last_prompt_data: Dict[str, Any] = {}
_current_system_prompt: str = DEFAULT_SYSTEM_PROMPT
_last_response: str = ""


def _find_citations(response_text: str, source_text: str) -> List[Dict[str, Any]]:
    """Exact substring matching — finds response sentences in source_text.
    Returns sorted, merged list of {start, end, text} ranges."""
    cleaned = _re.sub(r'\[Źródło\s+\d+[^\]]*\]', '', response_text)
    ranges: List[Dict[str, Any]] = []
    for sentence in _re.split(r'(?<=[.!?])\s+', cleaned):
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue
        idx = source_text.find(sentence)
        if idx != -1:
            ranges.append({"start": idx, "end": idx + len(sentence), "text": sentence})
    ranges.sort(key=lambda r: r["start"])
    merged: List[Dict[str, Any]] = []
    for r in ranges:
        if merged and r["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], r["end"])
            merged[-1]["text"] = source_text[merged[-1]["start"]:merged[-1]["end"]]
        else:
            merged.append(dict(r))
    return merged


class ChatRequest(BaseModel):
    query: str
    top_k: int = 8
    system_prompt: Optional[str] = None
    temperature: float = 0.0


class SystemPromptRequest(BaseModel):
    system_prompt: str


@router.post("")
async def chat(req: ChatRequest):
    global _last_retrieval, _last_prompt_data, _current_system_prompt, _last_response
    _last_response = ""

    system_prompt = req.system_prompt or _current_system_prompt

    # 1. Query expansion — generate alternative phrasings
    t_emb_start = time.time()
    queries = expand_query(req.query, n=3)

    # 2. Embed all query variants
    query_embeddings = []
    for q in queries:
        emb, _ = embed_query(q)
        query_embeddings.append(emb)
    embedding_ms = (time.time() - t_emb_start) * 1000

    # 3. Retrieve for each variant, union by best score
    t_ret_start = time.time()
    best: Dict[str, Dict] = {}
    for emb in query_embeddings:
        results = query_chunks(emb, n_results=req.top_k)
        if results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                dist = float(results["distances"][0][i])
                if chunk_id not in best or dist < best[chunk_id]["distance"]:
                    best[chunk_id] = {
                        "distance": dist,
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    }

    sorted_results = sorted(best.items(), key=lambda x: x[1]["distance"])[: req.top_k]
    retrieval_ms = (time.time() - t_ret_start) * 1000

    # 4. Build retrieval list — use parent content for LLM context
    retrieved = []
    document_names: Dict[str, str] = {}
    for rank, (chunk_id, data) in enumerate(sorted_results, 1):
        meta = data["metadata"]
        doc_id = meta.get("document_id", "")
        doc_name = meta.get("document_name", doc_id[:12])
        parent_content = get_parent_content(chunk_id)
        content_for_prompt = parent_content or data["document"]
        document_names[doc_id] = doc_name
        retrieved.append({
            "chunk_id": chunk_id,
            "document_id": doc_id,
            "document_name": doc_name,
            "content": content_for_prompt,
            "score": 1.0 - data["distance"],
            "rank": rank,
        })

    _last_retrieval = retrieved

    # 5. Build prompt with source labels
    chunks_for_prompt = [
        Chunk(
            id=r["chunk_id"],
            document_id=r["document_id"],
            content=r["content"],
            index=r["rank"] - 1,
            char_count=len(r["content"]),
            token_count=0,
            start_char=0,
            end_char=len(r["content"]),
        )
        for r in retrieved
    ]

    prompt_data = build_prompt(req.query, chunks_for_prompt, system_prompt, document_names=document_names)
    _last_prompt_data = prompt_data

    # 6. Stream response
    collected: List[str] = []

    def event_stream():
        global _last_response
        for token in stream_chat(
            prompt_data["full_prompt"],
            req.query,
            embedding_ms=embedding_ms,
            retrieval_ms=retrieval_ms,
            temperature=req.temperature,
        ):
            collected.append(token)
            yield f"data: {token}\n\n"
        _last_response = "".join(collected)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/retrieval")
def get_retrieval():
    global _last_retrieval, _last_response
    enriched = []
    for chunk in _last_retrieval:
        highlights = _find_citations(_last_response, chunk["content"]) if _last_response else []
        enriched.append({**chunk, "highlighted_ranges": highlights})
    return enriched


@router.get("/prompt")
def get_prompt():
    return _last_prompt_data


@router.post("/system-prompt")
def update_system_prompt(req: SystemPromptRequest):
    global _current_system_prompt
    _current_system_prompt = req.system_prompt
    return {"updated": True}
