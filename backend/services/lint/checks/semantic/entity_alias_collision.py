import os
from typing import List

from openai import OpenAI

from models.lint_models import AliasMergeJudgement, LintIssue
from services.wiki_store import ENTITIES_DIR, WikiStore

_SEMANTIC_CAP = 50


def _get_client() -> OpenAI:
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _edit_distance(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            dp[j] = prev if a[i - 1] == b[j - 1] else 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]


def _normalize(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").strip().lower()


def check_entity_alias_collision(
    store: WikiStore, llm_client=None
) -> List[LintIssue]:
    if llm_client is None:
        llm_client = _get_client()

    base = store.root / "wiki" / ENTITIES_DIR
    if not base.exists():
        return []

    entities = []
    for type_dir in base.iterdir():
        if not type_dir.is_dir():
            continue
        for path in type_dir.glob("*.md"):
            ent = store.read_entity(path.stem, type_dir.name)
            if ent:
                entities.append((path.stem, type_dir.name, ent, _normalize(path.stem)))

    issues: List[LintIssue] = []
    checked = 0
    model = os.getenv("CHAT_MODEL", "gpt-4o-mini")

    for i in range(len(entities)):
        if checked >= _SEMANTIC_CAP:
            break
        slug_a, type_a, ent_a, norm_a = entities[i]
        for j in range(i + 1, len(entities)):
            if checked >= _SEMANTIC_CAP:
                break
            slug_b, type_b, ent_b, norm_b = entities[j]
            if _edit_distance(norm_a, norm_b) >= 3:
                continue

            checked += 1
            resp = llm_client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Judge whether these two entity names refer to the same real-world entity and should be merged.",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Entity A: {slug_a} (type: {type_a}, id: {ent_a.id})\n"
                            f"Entity B: {slug_b} (type: {type_b}, id: {ent_b.id})"
                        ),
                    },
                ],
                response_format=AliasMergeJudgement,
            )
            result = resp.choices[0].message.parsed
            if result and result.should_merge:
                issues.append(LintIssue(
                    id=f"entity_alias_collision:{ent_a.id}:{ent_b.id}",
                    type="entity_alias_collision",
                    severity="info",
                    location=f"entity:{ent_a.id}",
                    description=(
                        f"Entities '{slug_a}' and '{slug_b}' have similar names. {result.explanation}"
                    ),
                    suggested_fix=f"Merge into '{result.suggested_canonical}'",
                    auto_fixable=False,
                    payload={
                        "entity_a_id": ent_a.id,
                        "entity_b_id": ent_b.id,
                        "slug_a": slug_a,
                        "slug_b": slug_b,
                        "type_a": type_a,
                        "type_b": type_b,
                        "suggested_canonical": result.suggested_canonical,
                    },
                ))
    return issues
