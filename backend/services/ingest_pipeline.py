import logging
import shutil
import time
from datetime import datetime
from pathlib import Path

from models.ingest_models import IngestResult
from models.wiki_models import Edge, Source
from services._slug import slugify, ensure_unique
from services.parser import parse_source
from services.source_classifier import classify_source_chunked
from services.chunking import chunk_text
from services.resolver import resolve_classification
from services.conflict_detector import detect_conflicts
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from services.wiki_log import append_log_entry
from services.semantic_index import add_claims_to_index, semantic_neighbors
from services.resolver import _max_id_number


def _contradiction_edges(conflicts, new_claims, source_id, store: WikiStore, pending_edges=()):
    """One `contradicts` edge (new claim -> existing claim) per detected conflict, so the
    contradiction lives in the graph and retrieval can surface both sides."""
    if not conflicts:
        return []
    spans = {c.id: c.span for c in new_claims}
    # number after both stored edges and this source's not-yet-appended resolver edges
    n = max(_max_id_number(store.read_all_edges(), "ed_"), _max_id_number(list(pending_edges), "ed_"))
    edges = []
    for i, cf in enumerate(conflicts, 1):
        span = spans.get(cf.new_claim_id)
        if span is None:
            continue
        edges.append(Edge(
            id=f"ed_{n + i:03d}",
            **{"from": f"claim:{cf.new_claim_id}"},
            to=f"claim:{cf.existing_claim_id}",
            relation="contradicts",
            source_id=source_id,
            span=span,
            confidence=1.0,
        ))
    return edges


def ingest_source(file_path: Path, store: WikiStore) -> IngestResult:
    """
    Orchestrates the 5-stage ingest pipeline:
    Stage 1: Parse (deterministic)
    Stage 2: Classify (LLM)
    Stage 3: Resolve (deterministic)
    Stage 4: Conflict Detection (conditional LLM)
    Stage 5: Save + Log + Reindex (deterministic)
    Returns IngestResult with status "ok", "partial", or "error".
    """
    t_start = time.time()
    llm_calls = 0
    file_path = Path(file_path)
    # raw/<slug>/ this run created — removed again if ingest fails before the source page
    # is written, so a failed upload leaves nothing behind.
    new_raw_dir = None

    try:
        # Stage 1: Parse. The slug is made unique *before* parsing writes raw/<slug>/.
        slug = ensure_unique(slugify(file_path.stem), set(store.list_sources()))
        raw_dir = store.root / "raw" / slug
        if not raw_dir.exists():
            new_raw_dir = raw_dir
        parsed = parse_source(file_path, store_root=store.root, slug=slug)
        text = parsed["text"]

        # Generate source ID (never recycle ids of deleted sources — see next_source_id)
        source_id = store.next_source_id()

        # Stage 2: Classify (LLM). Large documents are chunked so extraction stays dense;
        # one LLM call per chunk.
        n_chunks = len(chunk_text(text))
        classification = classify_source_chunked(text)
        llm_calls += n_chunks

        # Stage 3: Resolve (deterministic)
        resolved = resolve_classification(
            classification=classification,
            source_id=source_id,
            store=store,
            source_text=text,
        )

        # Stage 4: Conflict Detection (conditional LLM)
        existing_claims = store.read_all_claims()
        try:
            neighbors = semantic_neighbors(store, resolved["claims"])
        except Exception as exc:  # no embeddings -> subject-only candidates
            logging.getLogger(__name__).warning("conflict neighbour lookup failed: %s", exc)
            neighbors = {}
        conflicts = detect_conflicts(resolved["claims"], existing_claims, neighbors=neighbors)
        # NOTE: increments llm_calls only when conflicts are returned. If the LLM runs
        # but finds no genuine contradictions, that call is not counted here. This is a
        # known limitation — an accurate cost counter would require detect_conflicts to
        # return a richer signal.
        if conflicts:
            llm_calls += 1

        # Stage 5: Save + Log + Reindex
        source = Source(
            id=source_id,
            title=classification.title,
            type=file_path.suffix.lstrip(".").lower(),
            raw_path=str(store.root / "raw" / slug / "parsed.md"),
            ingested_at=datetime.utcnow(),
            source_url=None,
            summary=classification.description,
            key_takeaways=classification.key_takeaways,
            questions=classification.questions,
            tags=classification.tags,
        )
        store.write_source(source, slug=slug)
        new_raw_dir = None  # the source exists now; its raw copy must stay

        claims_added = 0
        for claim in resolved["claims"]:
            if store.append_claim(claim):
                claims_added += 1

        edges_added = 0
        for edge in resolved["edges"] + _contradiction_edges(
            conflicts, resolved["claims"], source_id, store, resolved["edges"]):
            if store.append_edge(edge):
                edges_added += 1

        duration_ms = (time.time() - t_start) * 1000

        append_log_entry(
            store=store,
            op="ingest",
            source_id=source_id,
            details=(
                f"title={classification.title!r}, "
                f"+{resolved['entities_created']} entities, "
                f"+{resolved['concepts_created']} concepts, "
                f"+{claims_added} claims, "
                f"+{edges_added} edges, "
                f"{len(conflicts)} conflicts"
            ),
        )

        regenerate_index(store)

        # Keep the semantic index in sync with this source's new claims (non-fatal:
        # ingest must still succeed if embedding is unavailable).
        try:
            add_claims_to_index(store, resolved["claims"])
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "semantic index update failed for %s — index is now stale, "
                "run scripts/rebuild_embeddings.py (%s)", source_id, exc
            )

        return IngestResult(
            source_id=source_id,
            slug=slug,
            status="ok",
            entities_created=resolved["entities_created"],
            entities_merged=resolved["entities_merged"],
            concepts_created=resolved["concepts_created"],
            concepts_merged=resolved["concepts_merged"],
            claims_added=claims_added,
            edges_added=edges_added,
            conflicts=conflicts,
            duration_ms=duration_ms,
            llm_calls=llm_calls,
        )

    except Exception as exc:
        if new_raw_dir is not None:
            shutil.rmtree(new_raw_dir, ignore_errors=True)
        duration_ms = (time.time() - t_start) * 1000
        error_msg = str(exc)
        if "context_length_exceeded" in error_msg or "maximum context length" in error_msg:
            error_msg = (
                "The file is too large: its text exceeds the model's context limit (~100k tokens). "
                "Split the document into smaller parts and add each one separately."
            )
        return IngestResult(
            source_id="",
            slug="",
            status="error",
            entities_created=0, entities_merged=0,
            concepts_created=0, concepts_merged=0,
            claims_added=0, edges_added=0,
            conflicts=[], duration_ms=duration_ms,
            llm_calls=llm_calls, error=error_msg,
        )
