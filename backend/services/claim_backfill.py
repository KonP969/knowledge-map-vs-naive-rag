"""Re-extract claims for already-ingested sources, without touching entities/concepts.

The original raw text of every source is preserved on disk (Source.raw_path). This module
re-runs claim extraction over that raw text and replaces only the CLAIMS for each source,
leaving entities, concepts, their descriptions, edges, and summaries untouched. This lets us
enrich a thin knowledge graph (more/atomic claims) without a destructive full re-ingest.
"""
import re
from dataclasses import dataclass
from typing import Callable, List, Optional

from models.ingest_models import ClaimExtraction, SourceClassification
from models.wiki_models import Claim
from services._slug import slugify
from services.source_classifier import classify_source
from services.wiki_store import WikiStore


@dataclass
class BackfillResult:
    slug: str
    source_id: Optional[str]
    old_count: int
    new_count: int
    applied: bool
    skipped_reason: Optional[str] = None


def _next_claim_number(store: WikiStore) -> int:
    max_n = 0
    for c in store.read_all_claims():
        m = re.match(r"cl_(\d+)", c.id)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n + 1


def _resolve_subject_id(
    ce: ClaimExtraction, classification: SourceClassification, store: WikiStore
) -> str:
    """Map a claim's subject to an EXISTING graph node. Never creates or merges nodes.

    Falls back to a slug-based ref (e.g. 'entity:azura') when the subject is not yet
    in the graph — lint can surface such dangling references afterwards.
    """
    name = ce.subject_name
    if ce.subject_type == "entity":
        for em in classification.entity_mentions:
            if em.name.lower() == name.lower():
                slug = slugify(em.name)
                if store.entity_exists(slug, em.type):
                    return f"entity:{store.read_entity(slug, em.type).id}"
                break
    elif ce.subject_type == "concept":
        for cm in classification.concept_mentions:
            if cm.name.lower() == name.lower():
                slug = slugify(cm.name)
                if store.concept_exists(slug):
                    return f"concept:{store.read_concept(slug).id}"
                break
    return f"{ce.subject_type}:{slugify(name)}"


def reextract_claims_for_source(
    slug: str,
    store: WikiStore,
    *,
    apply: bool = False,
    classify_fn: Callable[[str], SourceClassification] = classify_source,
) -> BackfillResult:
    src = store.read_source(slug)
    if src is None:
        return BackfillResult(slug, None, 0, 0, applied=False, skipped_reason="source not found")

    source_id = src.id
    old_count = sum(1 for c in store.read_all_claims() if c.source_id == source_id)

    raw = store.read_raw_text(slug)
    if not raw or not raw.strip():
        return BackfillResult(slug, source_id, old_count, old_count, applied=False,
                              skipped_reason="no raw text")

    classification = classify_fn(raw)

    start = _next_claim_number(store)
    new_claims: List[Claim] = []
    for i, ce in enumerate(classification.claims):
        new_claims.append(Claim(
            id=f"cl_{start + i:03d}",
            text=ce.text,
            subject_id=_resolve_subject_id(ce, classification, store),
            source_id=source_id,
            span=ce.span,
            confidence=ce.confidence,
            polarity=ce.polarity,
        ))
    new_count = len(new_claims)

    if not apply:
        return BackfillResult(slug, source_id, old_count, new_count, applied=False)

    store.delete_claims_by_source(source_id)
    for c in new_claims:
        store.append_claim(c)
    return BackfillResult(slug, source_id, old_count, new_count, applied=True)


def reextract_claims_all(
    store: WikiStore,
    *,
    apply: bool = False,
    classify_fn: Callable[[str], SourceClassification] = classify_source,
) -> List[BackfillResult]:
    results = [
        reextract_claims_for_source(slug, store, apply=apply, classify_fn=classify_fn)
        for slug in store.list_sources()
    ]
    if apply:
        from services.wiki_index import regenerate_index
        regenerate_index(store)
    return results
