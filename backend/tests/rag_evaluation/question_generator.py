import os
import json
import random
from typing import List, Dict, Optional

from openai import OpenAI

from .rag_client import get_documents, get_chunks
from .cost_guard import calc_openai_cost, CostGuard

_SYSTEM_PROMPT = """Jestes ekspertem tworzacym pytania testowe dla systemu RAG.
Na podstawie podanego fragmentu tekstu wygeneruj pytania, ktore:
1. Maja jednoznaczna odpowiedz w tekscie
2. Sprawdzaja faktyczna wiedze (nie ogolne pytania o temat)
3. Sa zroznicowane pod wzgledem trudnosci
Odpowiedz WYLACZNIE w formacie JSON."""

_USER_TEMPLATE = """Fragment tekstu z dokumentu "{document_name}":

---
{text_sample}
---

Wygeneruj dokladnie {n_questions} pytania testowe.
Odpowiedz jako JSON:
{{
  "questions": [
    {{
      "query": "tresc pytania",
      "expected_topics": ["temat1", "temat2"],
      "difficulty": "easy|medium|hard"
    }}
  ]
}}"""

MAX_SAMPLE_CHARS = 2000
CHUNKS_SAMPLE_SIZE = 5


def generate_questions(
    n_total: int,
    cost_guard: Optional[CostGuard] = None,
) -> List[Dict]:
    """
    Generuje n_total pytan testowych z dokumentow w bazie.
    Zwraca przetasowana liste {id, query, expected_topics, difficulty, document_name, document_id}.
    """
    documents = get_documents()
    if not documents:
        raise RuntimeError(
            "Brak dokumentow w bazie. Wgraj dokumenty i wygeneruj chunki przed ewaluacja."
        )

    docs_with_chunks = _filter_docs_with_chunks(documents)
    if not docs_with_chunks:
        raise RuntimeError(
            "Zaden dokument nie ma wygenerowanych chunkow. "
            "Przejdz do Chunking Lab i wygeneruj chunki przed ewaluacja."
        )

    n_per_doc = max(1, round(n_total / len(docs_with_chunks)))
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    all_questions: List[Dict] = []
    question_id = 1

    for doc in docs_with_chunks:
        doc_id = doc["id"]
        doc_name = doc["name"]
        try:
            chunks = get_chunks(doc_id)
        except Exception as e:
            print(f"  Pominieto '{doc_name}': {e}")
            continue
        if not chunks:
            continue

        text_sample = _build_text_sample(chunks)
        raw_questions = _call_llm(
            client=client,
            document_name=doc_name,
            text_sample=text_sample,
            n_questions=n_per_doc,
            cost_guard=cost_guard,
        )
        for q in raw_questions:
            query_text = q.get("query", "").strip()
            if not query_text:
                continue
            all_questions.append({
                "id": question_id,
                "query": query_text,
                "expected_topics": q.get("expected_topics", []),
                "difficulty": q.get("difficulty", "medium"),
                "document_name": doc_name,
                "document_id": doc_id,
            })
            question_id += 1

    random.shuffle(all_questions)
    result = all_questions[:n_total]
    for i, q in enumerate(result, 1):
        q["id"] = i
    return result


def _filter_docs_with_chunks(documents: List[Dict]) -> List[Dict]:
    """Zwraca tylko dokumenty ktore maja wygenerowane chunki."""
    import httpx
    result = []
    for doc in documents:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(
                    f"http://localhost:8000/api/chunks/{doc['id']}"
                )
                if resp.status_code == 200 and resp.json().get("chunks"):
                    result.append(doc)
        except Exception:
            pass
    return result


def _build_text_sample(chunks: List[Dict]) -> str:
    """Losuje probke chunkow, scala do max MAX_SAMPLE_CHARS znakow."""
    sample = random.sample(chunks, min(CHUNKS_SAMPLE_SIZE, len(chunks)))
    sample.sort(key=lambda c: c.get("index", 0))
    parts: List[str] = []
    total = 0
    for chunk in sample:
        content = chunk.get("content", "")
        if total + len(content) > MAX_SAMPLE_CHARS:
            parts.append(content[:MAX_SAMPLE_CHARS - total])
            break
        parts.append(content)
        total += len(content)
    return "\n\n".join(parts)


def _call_llm(
    client: OpenAI,
    document_name: str,
    text_sample: str,
    n_questions: int,
    cost_guard: Optional[CostGuard],
) -> List[Dict]:
    """Wywoluje gpt-4o-mini do generowania pytan. Zwraca liste dict."""
    user_prompt = _USER_TEMPLATE.format(
        document_name=document_name,
        text_sample=text_sample,
        n_questions=n_questions,
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
    except Exception as e:
        print(f"  Blad LLM (generowanie pytan, '{document_name}'): {e}")
        return []

    if response.usage and cost_guard is not None:
        cost = calc_openai_cost(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
        warning = cost_guard.add_eval_cost(cost)
        if warning:
            print(f"  {warning}")

    try:
        data = json.loads(response.choices[0].message.content)
        return data.get("questions", [])
    except (json.JSONDecodeError, IndexError, AttributeError) as e:
        print(f"  Blad parsowania pytan dla '{document_name}': {e}")
        return []
