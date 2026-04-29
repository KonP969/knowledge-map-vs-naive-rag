import os
from openai import OpenAI
from models.ingest_models import SourceClassification

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a knowledge extraction engine for a structured wiki.

Given an article or document, extract:
1. A clean title and short description.
2. Tags (3-10 lowercase keywords).
3. 2-5 questions the document answers.
4. 2-5 key takeaways.
5. Named entity mentions (Person, Org, Product, Place, Event) with their span positions in the TEXT.
6. Concept mentions (abstract ideas, design principles, techniques) with their span positions.
7. Factual claims — atomic statements with subject, confidence (0-1), and polarity (asserts/denies).

For spans: start/end are character offsets into the DOCUMENT TEXT. text is the exact substring.
For entities and concepts: canonical name only — no duplicates.
"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def classify_source(text: str, model: str = None) -> SourceClassification:
    """
    Stage 2: LLM structured output call.
    Returns a SourceClassification parsed from the document text.
    """
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    client = _get_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"DOCUMENT TEXT:\n\n{text}"},
        ],
        response_format=SourceClassification,
    )
    result = response.choices[0].message.parsed
    if result is None:
        raise ValueError("LLM returned no structured output (possible refusal or content filter)")
    return result
