import time
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from models.chunk import Chunk
from services.embeddings_service import embed_query
from services.vector_store import query_chunks
from services.prompt_builder import build_prompt, DEFAULT_SYSTEM_PROMPT
from services.llm_service import stream_chat

router = APIRouter(prefix="/api/chat", tags=["chat"])

_last_retrieval: List[Dict[str, Any]] = []
_last_prompt_data: Dict[str, Any] = {}
_current_system_prompt: str = DEFAULT_SYSTEM_PROMPT


class ChatRequest(BaseModel):
    query: str
    top_k: int = 5
    system_prompt: Optional[str] = None


class SystemPromptRequest(BaseModel):
    system_prompt: str


@router.post("")
async def chat(req: ChatRequest):
    global _last_retrieval, _last_prompt_data, _current_system_prompt

    system_prompt = req.system_prompt or _current_system_prompt

    # 1. Embed query
    t_emb_start = time.time()
    query_embedding, _ = embed_query(req.query)
    embedding_ms = (time.time() - t_emb_start) * 1000

    # 2. Retrieve chunks
    t_ret_start = time.time()
    results = query_chunks(query_embedding, n_results=req.top_k)
    retrieval_ms = (time.time() - t_ret_start) * 1000

    retrieved = []
    if results["ids"] and results["ids"][0]:
        for i, chunk_id in enumerate(results["ids"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            retrieved.append({
                "chunk_id": chunk_id,
                "document_id": meta.get("document_id", ""),
                "document_name": meta.get("document_id", "")[:12],
                "content": results["documents"][0][i] if results["documents"] else "",
                "score": 1.0 - float(results["distances"][0][i]),
                "rank": i + 1,
            })

    _last_retrieval = retrieved

    # 3. Build chunks for prompt
    chunks_for_prompt = [
        Chunk(
            id=r["chunk_id"], document_id=r["document_id"], content=r["content"],
            index=r["rank"] - 1, char_count=len(r["content"]),
            token_count=0, start_char=0, end_char=len(r["content"]),
        )
        for r in retrieved
    ]

    prompt_data = build_prompt(req.query, chunks_for_prompt, system_prompt)
    _last_prompt_data = prompt_data

    # 4. Stream response
    def event_stream():
        for token in stream_chat(
            prompt_data["full_prompt"],
            req.query,
            embedding_ms=embedding_ms,
            retrieval_ms=retrieval_ms,
        ):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/retrieval")
def get_retrieval():
    return _last_retrieval


@router.get("/prompt")
def get_prompt():
    return _last_prompt_data


@router.post("/system-prompt")
def update_system_prompt(req: SystemPromptRequest):
    global _current_system_prompt
    _current_system_prompt = req.system_prompt
    return {"updated": True}
