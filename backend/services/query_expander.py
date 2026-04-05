"""Query expansion — generates alternative phrasings for better semantic retrieval."""
import os
from typing import Optional
from openai import OpenAI

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def expand_query(query: str, n: int = 3) -> list[str]:
    """Returns [original_query] + n alternative phrasings."""
    try:
        client = _get_client()
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Jesteś asystentem do wyszukiwania semantycznego. "
                        "Wygeneruj alternatywne sformułowania pytania użytkownika, "
                        "które pomogą znaleźć odpowiednie fragmenty tekstu. "
                        f"Zwróć dokładnie {n} warianty, każdy w osobnej linii, bez numerowania."
                    ),
                },
                {"role": "user", "content": f"Pytanie: {query}"},
            ],
            max_tokens=150,
            temperature=0.4,
        )
        raw = response.choices[0].message.content.strip().split("\n")
        variants = [v.strip().lstrip("•-–").strip() for v in raw if v.strip()][:n]
        return [query] + variants
    except Exception:
        return [query]
