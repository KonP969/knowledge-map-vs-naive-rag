import os
from typing import List

from openai import OpenAI
from services.openai_client import make_client

from models.lint_models import LintIssue, StaleSummaryJudgement
from services.wiki_store import WikiStore

_SEMANTIC_CAP = 50


def _get_client() -> OpenAI:
    return make_client()


def check_stale_summary(
    store: WikiStore, llm_client=None
) -> List[LintIssue]:
    if llm_client is None:
        llm_client = _get_client()

    claims = store.read_all_claims()
    issues: List[LintIssue] = []
    checked = 0
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    for slug in store.list_sources():
        if checked >= _SEMANTIC_CAP:
            break
        source = store.read_source(slug)
        if source is None:
            continue
        source_claims = [c for c in claims if c.source_id == source.id]
        if not source_claims:
            continue

        checked += 1
        claim_texts = "\n".join(f"- {c.text}" for c in source_claims[:20])
        resp = llm_client.beta.chat.completions.parse(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Compare a source summary with its extracted claims. "
                        "Determine if the summary is missing important information and needs updating."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Current summary:\n{source.summary}\n\nExtracted claims:\n{claim_texts}"
                    ),
                },
            ],
            response_format=StaleSummaryJudgement,
        )
        result = resp.choices[0].message.parsed
        if result and result.is_stale:
            issues.append(LintIssue(
                id=f"stale_summary:{source.id}",
                type="stale_summary",
                severity="info",
                location=f"source:{source.id}",
                description=(
                    f"Source '{slug}' summary may be incomplete. {result.explanation}"
                ),
                suggested_fix="Update summary (LLM-proposed)",
                auto_fixable=True,
                payload={
                    "slug": slug,
                    "source_id": source.id,
                    "proposed_summary": result.proposed_summary,
                },
            ))
    return issues
