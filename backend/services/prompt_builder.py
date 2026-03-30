from typing import List, Dict, Any
from models.chunk import Chunk
from services.token_counter import count_tokens

DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based on the provided context documents.
Always base your answer on the context provided. If the context doesn't contain the answer, say so clearly.
Be concise and accurate."""


def build_prompt(
    query: str,
    chunks: List[Chunk],
    system_message: str = DEFAULT_SYSTEM_PROMPT,
) -> Dict[str, Any]:
    if chunks:
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[{i}] {chunk.content}")
        context_block = "\n\n".join(context_parts)
    else:
        context_block = ""

    if context_block:
        full_prompt = f"{system_message}\n\nContext:\n{context_block}\n\nQuestion: {query}"
    else:
        full_prompt = f"{system_message}\n\nQuestion: {query}"

    token_counts = {
        "system": count_tokens(system_message),
        "context": count_tokens(context_block),
        "query": count_tokens(query),
        "total": count_tokens(full_prompt),
    }

    return {
        "system_message": system_message,
        "context_block": context_block,
        "user_query": query,
        "full_prompt": full_prompt,
        "token_counts": token_counts,
    }
