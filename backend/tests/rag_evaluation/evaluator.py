import json
import os
from typing import Dict, List, Optional

from openai import OpenAI

from .cost_guard import calc_openai_cost, CostGuard

_SYSTEM_PROMPT = """Jestes ekspertem oceniajacym jakosc odpowiedzi systemu RAG.
Oceniaj odpowiedz systemu na pytanie uzytkownika na podstawie dostarczonych fragmentow zrodlowych.

Metryki (skala 0-10):
- correctness: czy odpowiedz jest faktycznie poprawna i odpowiada na pytanie
- helpfulness: czy jest kompletna, zrozumiala i praktycznie uzyteczna
- faithfulness: czy opiera sie wylacznie na zrodlach bez dodawania niepotwierdonych informacji (0=haluycnuje, 10=wierna zrodlom)

Jesli system odpowiedzial "Nie znalazlem tej informacji..." i informacja faktycznie nie jest w zrodlach:
- correctness: 7 (poprawne zachowanie)
- helpfulness: 3 (malo pomocne)
- faithfulness: 10 (nie haluycnuje)

Odpowiedz WYLACZNIE w formacie JSON."""

_USER_TEMPLATE = """## Pytanie
{query}

## Odpowiedz systemu RAG
{answer}

## Pobrane fragmenty zrodlowe ({n_chunks} fragmentow)
{sources_text}

## Oczekiwane tematy w odpowiedzi
{expected_topics}

Ocen odpowiedz. Odpowiedz jako JSON:
{{
  "correctness": <0-10>,
  "helpfulness": <0-10>,
  "faithfulness": <0-10>,
  "explanation": "krotkie uzasadnienie (2-3 zdania po polsku)",
  "issues": ["lista problemow lub []"]
}}"""

MAX_SOURCE_CHARS = 3000


def evaluate(
    query: str,
    answer: str,
    retrieved_chunks: List[Dict],
    expected_topics: List[str],
    cost_guard: Optional[CostGuard] = None,
) -> Dict:
    """
    Ocenia odpowiedz RAG przez LLM-as-Judge.
    Zwraca dict: {correctness, helpfulness, faithfulness, avg_score, explanation, issues, eval_cost_usd}
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    sources_text = _format_sources(retrieved_chunks)
    expected_str = ", ".join(expected_topics) if expected_topics else "brak"

    user_prompt = _USER_TEMPLATE.format(
        query=query,
        answer=answer,
        n_chunks=len(retrieved_chunks),
        sources_text=sources_text,
        expected_topics=expected_str,
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
    except Exception as e:
        return _error_result(f"Blad API oceny: {e}")

    eval_cost = 0.0
    if response.usage:
        eval_cost = calc_openai_cost(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
        if cost_guard is not None:
            warning = cost_guard.add_eval_cost(eval_cost)
            if warning:
                print(f"  {warning}")

    try:
        data = json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, IndexError, AttributeError):
        data = {}

    correctness = _clamp(data.get("correctness", 0))
    helpfulness = _clamp(data.get("helpfulness", 0))
    faithfulness = _clamp(data.get("faithfulness", 0))

    return {
        "correctness": correctness,
        "helpfulness": helpfulness,
        "faithfulness": faithfulness,
        "avg_score": round((correctness + helpfulness + faithfulness) / 3.0, 2),
        "explanation": data.get("explanation", ""),
        "issues": data.get("issues", []),
        "eval_cost_usd": eval_cost,
    }


def _format_sources(chunks: List[Dict]) -> str:
    parts: List[str] = []
    total = 0
    for i, chunk in enumerate(chunks, 1):
        doc_name = chunk.get("document_name", "?")
        content = chunk.get("content", "")
        score = chunk.get("score", 0)
        entry = f"[Zrodlo {i}: {doc_name} | score: {score:.3f}]\n{content}"
        if total + len(entry) > MAX_SOURCE_CHARS:
            remaining = MAX_SOURCE_CHARS - total
            if remaining > 50:
                parts.append(entry[:remaining] + "...")
            break
        parts.append(entry)
        total += len(entry)
    return "\n\n".join(parts) if parts else "(brak pobranych zrodel)"


def _clamp(value) -> int:
    try:
        return max(0, min(10, int(value)))
    except (TypeError, ValueError):
        return 0


def _error_result(msg: str) -> Dict:
    return {
        "correctness": 0, "helpfulness": 0, "faithfulness": 0,
        "avg_score": 0.0, "explanation": msg,
        "issues": [msg], "eval_cost_usd": 0.0,
    }
