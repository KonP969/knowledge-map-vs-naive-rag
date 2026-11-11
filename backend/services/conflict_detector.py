import os
from typing import List
from pydantic import BaseModel
from openai import OpenAI
from services.openai_client import make_client

from models.wiki_models import Claim
from models.ingest_models import ConflictReport

_client: OpenAI = None


class _ConflictList(BaseModel):
    conflicts: List[ConflictReport]


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = make_client()
    return _client


def detect_conflicts(
    new_claims: List[Claim],
    existing_claims: List[Claim],
    model: str = None,
) -> List[ConflictReport]:
    """
    Stage 4 (conditional LLM). Only calls the LLM if:
      - At least one new_claim has polarity == "denies"
      - At least one existing_claim with same subject_id has polarity == "asserts"
    Returns list of ConflictReport (empty if no LLM call needed or LLM finds none).
    """
    if model is None:
        model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    denying = [c for c in new_claims if c.polarity == "denies"]
    if not denying:
        return []

    candidate_pairs = []
    for new_cl in denying:
        matching = [
            ec for ec in existing_claims
            if ec.subject_id == new_cl.subject_id and ec.polarity == "asserts"
        ]
        for ex_cl in matching:
            candidate_pairs.append((new_cl, ex_cl))

    if not candidate_pairs:
        return []

    pairs_text = "\n\n".join(
        f"NEW (id={nc.id}): \"{nc.text}\"\n"
        f"EXISTING (id={ec.id}): \"{ec.text}\""
        for nc, ec in candidate_pairs
    )
    prompt = (
        "You are a conflict detection assistant. "
        "For each pair of claims below, determine if they contradict each other. "
        "Return only genuine contradictions.\n\n"
        f"CLAIM PAIRS:\n{pairs_text}"
    )

    client = _get_client()
    response = client.beta.chat.completions.parse(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format=_ConflictList,
    )
    parsed = response.choices[0].message.parsed
    return parsed.conflicts if parsed is not None else []
