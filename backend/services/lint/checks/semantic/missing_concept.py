import os
from collections import defaultdict
from typing import List

from openai import OpenAI
from services.openai_client import make_client

from models.lint_models import LintIssue, MissingConceptJudgement
from services.wiki_store import WikiStore

_SEMANTIC_CAP = 50
_CLAIM_THRESHOLD = 5


def _get_client() -> OpenAI:
    return make_client()


def check_missing_concept(
    store: WikiStore, llm_client=None
) -> List[LintIssue]:
    if llm_client is None:
        llm_client = _get_client()

    claims = store.read_all_claims()
    by_subject: dict = defaultdict(list)
    for c in claims:
        if c.subject_id.startswith("entity:"):
            by_subject[c.subject_id].append(c)

    issues: List[LintIssue] = []
    checked = 0
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    for subject_id, group in by_subject.items():
        if checked >= _SEMANTIC_CAP:
            break
        if len(group) < _CLAIM_THRESHOLD:
            continue

        checked += 1
        claim_texts = "\n".join(f"- {c.text}" for c in group[:20])
        resp = llm_client.beta.chat.completions.parse(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Given claims about an entity, determine if there is a recurring "
                        "topic/theme that warrants its own Concept node in the knowledge graph."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Entity: {subject_id}\nClaims:\n{claim_texts}",
                },
            ],
            response_format=MissingConceptJudgement,
        )
        result = resp.choices[0].message.parsed
        if result and result.has_missing_concept:
            entity_id = subject_id.split(":", 1)[1]
            issues.append(LintIssue(
                id=f"missing_concept:{entity_id}:{result.concept_name}",
                type="missing_concept",
                severity="info",
                location=subject_id,
                description=(
                    f"{subject_id} has {len(group)} claims about '{result.concept_name}' "
                    f"without a Concept node. {result.explanation}"
                ),
                suggested_fix=f"Create concept '{result.concept_name}'",
                auto_fixable=False,
                payload={
                    "entity_id": entity_id,
                    "concept_name": result.concept_name,
                },
            ))
    return issues
