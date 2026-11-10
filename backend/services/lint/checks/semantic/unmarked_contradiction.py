import os
from collections import defaultdict
from typing import List

from openai import OpenAI
from services.openai_client import make_client

from models.lint_models import ContradictionJudgement, LintIssue
from services.wiki_store import WikiStore

_SEMANTIC_CAP = 50


def _get_client() -> OpenAI:
    return make_client()


def check_unmarked_contradiction(
    store: WikiStore, llm_client=None
) -> List[LintIssue]:
    if llm_client is None:
        llm_client = _get_client()

    claims = store.read_all_claims()
    edges = store.read_all_edges()

    contradicts_pairs: set = set()
    for e in edges:
        if e.relation == "contradicts":
            contradicts_pairs.add((e.from_, e.to))
            contradicts_pairs.add((e.to, e.from_))

    by_subject: dict = defaultdict(list)
    for c in claims:
        by_subject[c.subject_id].append(c)

    issues: List[LintIssue] = []
    checked = 0
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    for subject_id, group in by_subject.items():
        if checked >= _SEMANTIC_CAP:
            break
        asserts = [c for c in group if c.polarity == "asserts"]
        denies = [c for c in group if c.polarity == "denies"]
        if not asserts or not denies:
            continue

        for ca in asserts:
            for cd in denies:
                if checked >= _SEMANTIC_CAP:
                    break
                key_ab = (f"claim:{ca.id}", f"claim:{cd.id}")
                key_ba = (f"claim:{cd.id}", f"claim:{ca.id}")
                if key_ab in contradicts_pairs or key_ba in contradicts_pairs:
                    continue

                checked += 1
                resp = llm_client.beta.chat.completions.parse(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Judge whether these two claims are genuinely contradictory. "
                                "Return is_contradiction=True only if they express opposing facts about the same subject."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Claim A (asserts): {ca.text}\nClaim B (denies): {cd.text}",
                        },
                    ],
                    response_format=ContradictionJudgement,
                )
                result = resp.choices[0].message.parsed
                if result and result.is_contradiction:
                    issues.append(LintIssue(
                        id=f"unmarked_contradiction:{ca.id}:{cd.id}",
                        type="unmarked_contradiction",
                        severity="info",
                        location=subject_id,
                        description=(
                            f"Claims {ca.id} and {cd.id} have opposing polarity on "
                            f"{subject_id} without a contradicts edge. {result.explanation}"
                        ),
                        suggested_fix="Add contradicts edge",
                        auto_fixable=True,
                        payload={
                            "claim_a_id": ca.id,
                            "claim_b_id": cd.id,
                            "subject_id": subject_id,
                            "source_id": ca.source_id,
                        },
                    ))
    return issues
