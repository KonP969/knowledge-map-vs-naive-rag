from typing import List, Dict, Any
from models.chunk import Chunk
from services.token_counter import count_tokens

DEFAULT_SYSTEM_PROMPT = """Jesteś precyzyjnym asystentem odpowiadającym WYŁĄCZNIE na podstawie dostarczonego kontekstu.

Zasady:
1. Odpowiadaj tylko na podstawie fragmentów oznaczonych [Źródło N: nazwa].
2. Jeśli informacja NIE jest w kontekście, napisz wprost: "Nie znalazłem tej informacji w dostępnych dokumentach."
3. Nigdy nie uzupełniaj brakujących danych własną wiedzą ani nie zgaduj.
4. Na końcu odpowiedzi wypisz użyte źródła w formacie: Źródła: [Źródło 1], [Źródło 3]
5. Jeśli pytanie wymaga policzenia lub zebrania wszystkich elementów z listy — wymień je wszystkie z kontekstu."""


def build_prompt(
    query: str,
    chunks: List[Chunk],
    system_message: str = DEFAULT_SYSTEM_PROMPT,
    document_names: Dict[str, str] | None = None,
) -> Dict[str, Any]:
    if chunks:
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            doc_name = (document_names or {}).get(chunk.document_id, chunk.document_id[:12])
            context_parts.append(f"[Źródło {i}: {doc_name}]\n{chunk.content}")
        context_block = "\n\n".join(context_parts)
    else:
        context_block = ""

    if context_block:
        full_prompt = f"{system_message}\n\nKontekst:\n{context_block}\n\nPytanie: {query}"
    else:
        full_prompt = f"{system_message}\n\nPytanie: {query}"

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
