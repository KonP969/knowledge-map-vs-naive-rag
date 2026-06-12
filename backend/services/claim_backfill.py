"""Re-extract claims for already-ingested sources, without clobbering manual edits.

The original raw text of every source is preserved on disk (Source.raw_path). This module
re-runs claim extraction over that raw text and replaces only the CLAIMS (and the source's
mention edges) for each source. Entities and concepts that already exist keep their content
(descriptions, aliases, tags) untouched; missing entities/concepts are created so that the
new claims link to real graph nodes. This enriches a thin knowledge graph without a
destructive full re-ingest.
"""
from dataclasses import dataclass
from typing import Callable, List, Optional

from models.ingest_models import SourceClassification
from services.resolver import resolve_classification
from services.source_classifier import classify_source_chunked
from services.wiki_store import WikiStore


@dataclass
class BackfillResult:
    slug: str
    source_id: Optional[str]
    old_count: int
    new_count: int
    applied: bool
    skipped_reason: Optional[str] = None


def reextract_claims_for_source(
    slug: str,
    store: WikiStore,
    *,
    apply: bool = False,
    classify_fn: Callable[[str], SourceClassification] = classify_source_chunked,
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
    new_count = len(classification.claims)

    if not apply:
        return BackfillResult(slug, source_id, old_count, new_count, applied=False)

    # Replace this source's claims and mention edges, then re-resolve. Deleting first keeps
    # id numbering clean; overwrite_existing=False protects manually edited node content.
    store.delete_claims_by_source(source_id)
    store.delete_edges_by_source(source_id)
    resolved = resolve_classification(
        classification, source_id, store, overwrite_existing=False, source_text=raw,
    )
    for claim in resolved["claims"]:
        store.append_claim(claim)
    for edge in resolved["edges"]:
        store.append_edge(edge)

    return BackfillResult(slug, source_id, old_count, len(resolved["claims"]), applied=True)


def reextract_claims_all(
    store: WikiStore,
    *,
    apply: bool = False,
    classify_fn: Callable[[str], SourceClassification] = classify_source_chunked,
) -> List[BackfillResult]:
    results: List[BackfillResult] = []
    for slug in store.list_sources():
        try:
            results.append(
                reextract_claims_for_source(slug, store, apply=apply, classify_fn=classify_fn)
            )
        except Exception as exc:  # one source failing must not kill the whole run
            results.append(BackfillResult(slug, None, 0, 0, applied=False,
                                          skipped_reason=f"error: {exc}"))
    if apply:
        from services.wiki_index import regenerate_index
        regenerate_index(store)
    return results
