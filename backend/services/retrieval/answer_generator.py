import os
from openai import OpenAI
from models.retrieval_models import Answer

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a knowledgeable assistant answering questions from a structured knowledge wiki.

Answer using ONLY the provided context. Do not use your general knowledge.

FORMATTING RULES:
- Write at least 3-5 sentences. For complex topics use markdown: headers (##), bullet lists, bold for key terms.
- Cite sources inline using IDs from context: [source:src_001] or [claim:cl_001].
- Always include a 1-sentence confidence summary explaining how certain you are.
- Generate 2-3 related follow-up questions.
- If context has NO relevant information, say so clearly and set confidence below 0.4.

Reasoning: show 2-4 steps explaining how you connected the context to the answer.
"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def generate_answer(question: str, context: str, model: str = None) -> Answer:
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    client = _get_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"QUESTION: {question}\n\nCONTEXT:\n{context}"},
        ],
        response_format=Answer,
    )
    result = response.choices[0].message.parsed
    if result is None:
        raise ValueError("LLM returned no structured output for answer generation")
    return result
