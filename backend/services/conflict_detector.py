import os
from typing import Dict, List, Optional, Sequence
from pydantic import BaseModel
from openai import OpenAI
from services.openai_client import make_client

from models.wiki_models import Claim
from models.ingest_models import ConflictReport

_client: OpenAI = None

# Upper bound on pairs sent in one LLM call (keeps the prompt and cost bounded).
MAX_PAIRS = 60

_INSTRUCTIONS = """You check pairs of claims from different documents for contradictions.
Most pairs are NOT contradictions: different advice, different details, different
examples, or a broader vs a narrower statement can all be true together.

For EVERY pair answer three questions:
  same_thing: are A and B about the same object or topic?
  same_property: do they state something about the same property of it
    (e.g. its width, its opening direction, which colour is the 2026 colour)?
  incompatible: is it impossible for both to be true at once
    (different values, opposite statements, two different answers to one question)?
Answer false whenever you are unsure. In description, name the conflicting values.
"""


class PairVerdict(BaseModel):
    pair: int              # 1-based number of the pair in the prompt
    same_thing: bool       # both claims are about the same object/topic
    same_property: bool    # ...and about the same property of it (width, year's colour, ...)
    incompatible: bool     # ...and they cannot both be true
    description: str


class _Verdicts(BaseModel):
    verdicts: List[PairVerdict]


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = make_client()
    return _client


def candidate_pairs(
    new_claims: Sequence[Claim],
    existing_claims: Sequence[Claim],
    neighbors: Optional[Dict[str, List[str]]] = None,
    max_pairs: int = MAX_PAIRS,
):
    """Pairs (new, existing) worth asking the LLM about.

    A pair qualifies when the two claims come from DIFFERENT sources and either
      - share a subject node (any polarity: "70 cm" vs "80 cm" are both 'asserts'), or
      - are semantic neighbours (ids supplied by the caller from the claim index) —
        this catches the same fact stated about differently named nodes
        ("Mocha Mousse is the 2026 colour" vs "Cloud Dancer is the 2026 colour").
    Neighbour pairs come first: they are ranked by similarity, subject pairs are not.
    """
    by_id = {c.id: c for c in existing_claims}
    by_subject: Dict[str, List[Claim]] = {}
    for c in existing_claims:
        by_subject.setdefault(c.subject_id, []).append(c)

    pairs, seen = [], set()

    def _add(nc: Claim, ec: Claim):
        key = (nc.id, ec.id)
        if ec.source_id == nc.source_id or key in seen or nc.id == ec.id:
            return
        seen.add(key)
        pairs.append((nc, ec))

    for nc in new_claims:
        for ec_id in (neighbors or {}).get(nc.id, []):
            if ec_id in by_id:
                _add(nc, by_id[ec_id])
    for nc in new_claims:
        for ec in by_subject.get(nc.subject_id, []):
            _add(nc, ec)
    return pairs[:max_pairs]


def detect_conflicts(
    new_claims: List[Claim],
    existing_claims: List[Claim],
    model: str = None,
    neighbors: Optional[Dict[str, List[str]]] = None,
) -> List[ConflictReport]:
    """
    Stage 4 (conditional LLM). Asks the LLM about every candidate pair (see
    candidate_pairs); no call when there are none. A pair is a conflict only when the
    LLM says it is about the same thing, the same property, and incompatible — a plain
    "do these contradict?" question flagged ordinary differing advice as conflicts.
    """
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    pairs = candidate_pairs(new_claims, existing_claims, neighbors)
    if not pairs:
        return []

    pairs_text = "\n\n".join(
        f'PAIR {i}:\n  A (id={nc.id}): "{nc.text}"\n  B (id={ec.id}): "{ec.text}"'
        for i, (nc, ec) in enumerate(pairs, 1)
    )
    prompt = f"{_INSTRUCTIONS}\n{pairs_text}"

    client = _get_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format=_Verdicts,
        temperature=0,
    )
    parsed = response.choices[0].message.parsed
    if parsed is None:
        return []
    out = []
    for v in parsed.verdicts:
        if not (v.same_thing and v.same_property and v.incompatible):
            continue
        if not 1 <= v.pair <= len(pairs):
            continue
        nc, ec = pairs[v.pair - 1]
        out.append(ConflictReport(new_claim_id=nc.id, existing_claim_id=ec.id,
                                  description=v.description))
    return out
