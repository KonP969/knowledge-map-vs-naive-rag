import json
from typing import Dict, List, Tuple
from models.retrieval_models import Candidate, ParsedIntent
from services.wiki_store import WikiStore


def filter_candidates(
    intent: ParsedIntent,
    store: WikiStore,
    top_n: int = 20,
) -> List[Candidate]:
    """
    Stage 2 (deterministic). Reads index.json and scores all artifacts.
    Scoring rules:
      +3 entity exact slug/alias match
      +2 concept exact slug match
      +2 question overlap (artifact question contains query word >=4 chars)
      +1 per matching tag word
    Returns top_n by score (score > 0 only).
    """
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return []

    index = json.loads(index_path.read_text(encoding="utf-8"))
    query_lower = intent.original_question.lower()
    query_words = {w for w in query_lower.split() if len(w) >= 4}

    entity_slugs = {e.lower().replace(" ", "-") for e in intent.entity_mentions}
    entity_names = {e.lower() for e in intent.entity_mentions}
    concept_slugs = {c.lower().replace(" ", "-") for c in intent.concept_mentions}
    concept_names = {c.lower() for c in intent.concept_mentions}

    candidates: List[Candidate] = []

    for s in index.get("sources", []):
        score, breakdown = _score(
            slug=s["slug"], questions=s.get("questions", []), tags=s.get("tags", []),
            entity_slugs=entity_slugs, entity_names=entity_names,
            concept_slugs=concept_slugs, concept_names=concept_names,
            query_words=query_words, is_entity=False, is_concept=False,
        )
        if score > 0:
            candidates.append(Candidate(
                artifact_id=f"source:{s['id']}",
                artifact_type="source",
                slug=s["slug"],
                title=s["title"],
                score=score,
                score_breakdown=breakdown,
                questions=s.get("questions", []),
                tags=s.get("tags", []),
                description_preview=s.get("summary", "")[:200],
            ))

    for e in index.get("entities", []):
        aliases = [a.lower() for a in e.get("aliases", [])]
        score, breakdown = _score(
            slug=e["slug"], questions=e.get("questions", []), tags=e.get("tags", []),
            entity_slugs=entity_slugs, entity_names=entity_names,
            concept_slugs=concept_slugs, concept_names=concept_names,
            query_words=query_words, is_entity=True, is_concept=False,
            aliases=aliases,
        )
        if score > 0:
            candidates.append(Candidate(
                artifact_id=f"entity:{e['id']}",
                artifact_type="entity",
                slug=e["slug"],
                title=f"{e['type']}: {e['slug']}",
                score=score,
                score_breakdown=breakdown,
                questions=e.get("questions", []),
                tags=e.get("tags", []),
                description_preview=e.get("description_preview", "")[:200],
            ))

    for c in index.get("concepts", []):
        score, breakdown = _score(
            slug=c["slug"], questions=c.get("questions", []), tags=c.get("tags", []),
            entity_slugs=entity_slugs, entity_names=entity_names,
            concept_slugs=concept_slugs, concept_names=concept_names,
            query_words=query_words, is_entity=False, is_concept=True,
        )
        if score > 0:
            candidates.append(Candidate(
                artifact_id=f"concept:{c['id']}",
                artifact_type="concept",
                slug=c["slug"],
                title=c["slug"],
                score=score,
                score_breakdown=breakdown,
                questions=c.get("questions", []),
                tags=c.get("tags", []),
                description_preview=c.get("definition_preview", "")[:200],
            ))

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:top_n]


def _score(
    slug: str,
    questions: list,
    tags: list,
    entity_slugs: set,
    entity_names: set,
    concept_slugs: set,
    concept_names: set,
    query_words: set,
    is_entity: bool,
    is_concept: bool,
    aliases: list = None,
) -> Tuple[int, Dict[str, int]]:
    score = 0
    breakdown: Dict[str, int] = {}

    if is_entity:
        slug_match = slug in entity_slugs
        name_match = slug.replace("-", " ") in entity_names
        alias_match = bool(aliases and any(
            a in entity_names or a.replace(" ", "-") in entity_slugs
            for a in (aliases or [])
        ))
        if slug_match or name_match or alias_match:
            score += 3
            breakdown["entity_match"] = 3

    if is_concept:
        if slug in concept_slugs or slug.replace("-", " ") in concept_names:
            score += 2
            breakdown["concept_match"] = 2

    q_hits = sum(
        1 for q in questions
        if any(word in q.lower() for word in query_words)
    )
    if q_hits:
        pts = min(q_hits * 2, 2)
        score += pts
        breakdown["question_overlap"] = pts

    tag_words = {t.lower() for t in tags}
    tag_overlap = len(tag_words & query_words)
    if tag_overlap:
        score += tag_overlap
        breakdown["tag_match"] = tag_overlap

    return score, breakdown
