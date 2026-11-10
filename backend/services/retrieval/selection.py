import os
from typing import List
from openai import OpenAI
from services.openai_client import make_client
from models.retrieval_models import Candidate, Selection

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a retrieval selection assistant for a structured knowledge wiki.

Given a user question and a list of candidate artifacts (sources, entities, concepts) with metadata,
select the 1-5 most relevant artifacts that would help answer the question.

Rules:
- Use only the provided metadata (title, questions, tags, preview) — not your own knowledge.
- For each selected artifact, give a relevance_score (0.0–1.0) and short reasoning.
- Give an overall confidence score and reasoning for your selection.
- If no candidates are clearly relevant, return an empty selected list with low confidence.
"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = make_client()
    return _client


def select_candidates(
    question: str,
    candidates: List[Candidate],
    model: str = None,
) -> Selection:
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    candidates_text = "\n\n".join(
        f"[{i + 1}] artifact_id={c.artifact_id}\n"
        f"  type={c.artifact_type}, slug={c.slug}\n"
        f"  title={c.title}\n"
        f"  tags={c.tags}\n"
        f"  questions={c.questions[:3]}\n"
        f"  preview={c.description_preview[:120]}"
        for i, c in enumerate(candidates)
    )

    client = _get_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"QUESTION: {question}\n\nCANDIDATES:\n{candidates_text}"},
        ],
        response_format=Selection,
        temperature=0,
    )
    result = response.choices[0].message.parsed
    if result is None:
        raise ValueError("LLM returned no structured output for selection")
    return result
