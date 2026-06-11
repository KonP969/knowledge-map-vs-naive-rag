import os
from typing import Callable, Optional
from openai import OpenAI
from models.ingest_models import SourceClassification
from services.chunking import chunk_text, merge_classifications

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a knowledge extraction engine for a structured wiki.

Given an article or document, extract:
1. A clean title and short description.
2. Tags (3-10 lowercase keywords).
3. 2-5 questions the document answers.
4. 2-5 key takeaways.
5. Named entity mentions (Person, Org, Product, Place, Event) with their span positions in the TEXT.
6. Concept mentions (abstract ideas, design principles, techniques) with their span positions.
7. Factual claims — be EXHAUSTIVE. Extract every distinct factual statement the document
   makes, not just the highlights. Each claim is ONE atomic fact (a single subject + a single
   assertion); split compound sentences into separate claims. Aim for roughly one claim per
   1-2 sentences of substantive content — a typical article yields about 8-25 claims; a short
   note may yield only a few. Cover facts about every entity and concept you identified.
   Each claim has a subject, confidence (0-1), and polarity (asserts/denies), and must be
   grounded in a span of the source text.

For spans: `text` MUST be copied VERBATIM from the document — character-for-character,
same casing, accents and punctuation, no paraphrasing, summarizing, or re-capitalizing.
For a claim, prefer the FULL sentence (or minimal clause) that actually states the fact, so
the quote stands on its own as evidence — not just an entity name. start/end are character
offsets but may be approximate; the exact `text` is what matters and will be re-located in the
source automatically.
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


def classify_source_chunked(
    text: str,
    *,
    max_chars: int = 5000,
    classify_fn: Optional[Callable[[str], SourceClassification]] = None,
) -> SourceClassification:
    """Classify a source, chunking large documents so extraction stays dense.

    One LLM call over a very large document produces sparse, summary-level extraction;
    splitting into ~max_chars chunks and merging keeps entity/concept/claim density high.
    Returns a single merged SourceClassification regardless of how many chunks were used.
    """
    fn = classify_fn or classify_source
    chunks = chunk_text(text, max_chars=max_chars)
    if len(chunks) == 1:
        return fn(text)
    return merge_classifications([fn(c) for c in chunks])
