import os
from openai import OpenAI
from models.retrieval_models import ParsedIntent

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a query understanding engine for a structured knowledge wiki.

Analyze the user's question and extract:
1. entity_mentions: Named entities (persons, orgs, products, places, events) explicitly mentioned or strongly implied.
   If none explicitly mentioned, return all relevant by category — never exclude candidates.
2. concept_mentions: Abstract concepts, design principles, techniques, or topics.
3. time_period: start/end ISO dates if temporal filters apply; null otherwise.
   Convert relative dates ("last year") to absolute ISO dates using today's date.
4. intent_type: One of: fact_lookup, comparison, synthesis, definition, how_to, temporal_trend.
   Use "comparison" when the question compares multiple entities (list all in entity_mentions).
5. expected_answer_form: One of: short, list, table, analysis, citation.
"""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def parse_intent(question: str, model: str = None) -> ParsedIntent:
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
    client = _get_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        response_format=ParsedIntent,
        temperature=0,
    )
    result = response.choices[0].message.parsed
    if result is None:
        raise ValueError("LLM returned no structured output for intent parsing")
    return result
