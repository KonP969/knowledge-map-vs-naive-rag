import os
from openai import OpenAI
from models.retrieval_models import Answer

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a precise knowledge retrieval assistant.

Answer the user's question using ONLY the provided context.
Do not use your own general knowledge.
Cite specific sources using their IDs from the context (e.g. [source:src_001] or [claim:cl_001]).
Provide reasoning steps showing how you arrived at the answer.
Be honest about confidence — lower it if context is incomplete or ambiguous.
Generate 2–3 related questions the user might want to ask next.
If the context contains no relevant information, say so clearly and set confidence below 0.4.
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
