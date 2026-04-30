import time
from datetime import datetime
from pathlib import Path

from models.ingest_models import IngestResult
from models.wiki_models import Source
from services._slug import slugify, ensure_unique
from services.parser import parse_source
from services.source_classifier import classify_source
from services.resolver import resolve_classification
from services.conflict_detector import detect_conflicts
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from services.wiki_log import append_log_entry


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

    try:
        # Stage 1: Parse
        parsed = parse_source(file_path, store_root=store.root)
        slug = parsed["slug"]
        text = parsed["text"]

        # Ensure unique slug among existing sources
        existing_slugs = set(store.list_sources())
        slug = ensure_unique(slug, existing_slugs)

        # Generate source ID
        source_count = len(existing_slugs) + 1
        source_id = f"src_{source_count:03d}"

        # Stage 2: Classify (LLM)
        classification = classify_source(text)
        llm_calls += 1

        # Stage 3: Resolve (deterministic)
        resolved = resolve_classification(
            classification=classification,
            source_id=source_id,
            store=store,
        )

        # Stage 4: Conflict Detection (conditional LLM)
        existing_claims = store.read_all_claims()
        conflicts = detect_conflicts(resolved["claims"], existing_claims)
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

        claims_added = 0
        for claim in resolved["claims"]:
            if store.append_claim(claim):
                claims_added += 1

        edges_added = 0
        for edge in resolved["edges"]:
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
        duration_ms = (time.time() - t_start) * 1000
        return IngestResult(
            source_id="",
            slug="",
            status="error",
            entities_created=0, entities_merged=0,
            concepts_created=0, concepts_merged=0,
            claims_added=0, edges_added=0,
            conflicts=[], duration_ms=duration_ms,
            llm_calls=llm_calls, error=str(exc),
        )
