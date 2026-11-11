import os
import time
from dataclasses import dataclass
from openai import OpenAI
from services.openai_client import make_client
from models.retrieval_models import Answer

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a knowledgeable assistant answering questions from a structured knowledge wiki.

Answer using ONLY the provided context. Do not use your general knowledge.
This outranks every formatting rule below. A short answer grounded in the context
is always better than a longer one padded from what you already know.

GROUNDING RULES:
- Every factual statement must trace to the context and carry its citation:
  [source:src_001] or [claim:cl_001]. A sentence you cannot cite does not belong.
- Length follows the context, not a quota. One supported fact means one sentence.
- The flip side: use everything the context DOES support. Do not be terse with rich
  context — state every relevant fact you can cite, and connect them for the reader.
- Never explain, define or elaborate on a term the context does not explain itself,
  even when you know what it means and the answer would read better with it.
- If the context is thin, say what it does and does not cover, and lower confidence
  accordingly. If it holds NO relevant information, say so clearly and set confidence
  below 0.4.

FORMATTING RULES (apply only to what the context supports):
- For complex topics use markdown: headers (##), bullet lists, bold for key terms.
- Always include a 1-sentence confidence summary explaining how certain you are.
- Generate 2-3 related follow-up questions.

Reasoning: show 2-4 steps explaining how you connected the context to the answer.
"""


@dataclass
class AnswerWithUsage:
    answer: Answer
    prompt_tokens: int
    completion_tokens: int
    llm_ms: float


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = make_client()
    return _client


def generate_answer(question: str, context: str, model: str = None) -> AnswerWithUsage:
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    client = _get_client()
    t = time.time()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"QUESTION: {question}\n\nCONTEXT:\n{context}"},
        ],
        response_format=Answer,
        temperature=0,
    )
    llm_ms = (time.time() - t) * 1000
    result = response.choices[0].message.parsed
    if result is None:
        raise ValueError("LLM returned no structured output for answer generation")
    usage = response.usage
    return AnswerWithUsage(
        answer=result,
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
        llm_ms=llm_ms,
    )
