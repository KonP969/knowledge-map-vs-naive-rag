import os
import time
from typing import Callable, Optional
from openai import APIConnectionError, OpenAI
from models.ingest_models import SourceClassification
from services.chunking import chunk_text, merge_classifications

_client: OpenAI = None

_SYSTEM_PROMPT = """You are a knowledge extraction engine for a structured wiki.

Write the title, description, tags, questions and key_takeaways in the SAME LANGUAGE as the
document (a Polish document → Polish title/description/questions/etc.). Do not mix languages.

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


_NETWORK_ATTEMPTS = 4


def _call_with_network_retry(fn: Callable[[str], SourceClassification], chunk: str) -> SourceClassification:
    """Retry the same chunk on connection errors with growing backoff (flaky networks).
    Splitting would not help here, so the chunk is retried as-is; after the attempt
    budget the error propagates."""
    for attempt in range(_NETWORK_ATTEMPTS):
        try:
            return fn(chunk)
        except APIConnectionError:
            if attempt == _NETWORK_ATTEMPTS - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def _classify_with_split_retry(
    fn: Callable[[str], SourceClassification],
    chunk: str,
    depth: int = 2,
) -> list:
    """Classify one chunk; on failure split it in half and retry each half.

    Dense chunks (e.g. product/price tables) can blow the model's completion cap
    (LengthFinishReasonError) — halving the input roughly halves the output, which gets
    back under the cap. Connection errors are retried in place (see
    _call_with_network_retry) and re-raised when exhausted — splitting won't fix the
    network. Other persistent failures (bad key, quota) exhaust the depth budget and
    re-raise instead of being silently swallowed."""
    try:
        return [_call_with_network_retry(fn, chunk)]
    except APIConnectionError:
        raise
    except Exception:
        if depth <= 0 or len(chunk) < 1000:
            raise
        mid = len(chunk) // 2
        return (
            _classify_with_split_retry(fn, chunk[:mid], depth - 1)
            + _classify_with_split_retry(fn, chunk[mid:], depth - 1)
        )


def classify_source_chunked(
    text: str,
    *,
    max_chars: int = 5000,
    classify_fn: Optional[Callable[[str], SourceClassification]] = None,
) -> SourceClassification:
    """Classify a source, chunking large documents so extraction stays dense.

    One LLM call over a very large document produces sparse, summary-level extraction;
    splitting into ~max_chars chunks and merging keeps entity/concept/claim density high.
    A chunk that fails (typically the completion-length cap on dense tables) is split in
    half and retried rather than failing the whole document. Returns a single merged
    SourceClassification regardless of how many chunks were used."""
    fn = classify_fn or classify_source
    chunks = chunk_text(text, max_chars=max_chars)
    parts: list = []
    for c in chunks:
        parts.extend(_classify_with_split_retry(fn, c))
    return merge_classifications(parts)
