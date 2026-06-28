import os
import json as _json
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.wiki_store import WikiStore, ENTITIES_DIR, CONCEPTS_DIR

router = APIRouter(prefix="/api/wiki", tags=["wiki"])

_WIKI_DATA_DIR = Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default"))


def _get_store() -> WikiStore:
    return WikiStore(root=_WIKI_DATA_DIR)


@router.get("/sources", response_model=List[Dict[str, Any]])
def list_wiki_sources():
    store = _get_store()
    result = []
    for slug in store.list_sources():
        src = store.read_source(slug)
        if src:
            result.append({
                "slug": slug,
                "id": src.id,
                "title": src.title,
                "type": src.type,
                "ingested_at": src.ingested_at.isoformat(),
                "tags": src.tags,
                "questions": src.questions,
                "summary": src.summary,
                "key_takeaways": src.key_takeaways,
                "source_url": src.source_url,
                "folder": src.folder,
            })
    return result


class SetFolderRequest(BaseModel):
    slugs: List[str]
    folder: Optional[str] = None


@router.post("/sources/folder", response_model=Dict[str, Any])
def set_sources_folder(req: SetFolderRequest):
    """Bulk-assign (or clear, with folder=null) the view-only folder of sources."""
    store = _get_store()
    known = set(store.list_sources())
    missing = [s for s in req.slugs if s not in known]
    if missing:
        raise HTTPException(status_code=404, detail=f"Sources not found: {missing}")
    for slug in req.slugs:
        store.set_source_folder(slug, req.folder)
    return {"updated": len(req.slugs), "folder": req.folder}


@router.get("/entities", response_model=List[Dict[str, Any]])
def list_wiki_entities():
    store = _get_store()
    result = []
    base = store.root / "wiki" / ENTITIES_DIR
    if not base.exists():
        return result
    for type_dir in sorted(base.iterdir()):
        if not type_dir.is_dir():
            continue
        for path in sorted(type_dir.glob("*.md")):
            slug = path.stem
            entity = store.read_entity(slug, type_dir.name)
            if entity:
                result.append({
                    "slug": slug,
                    "id": entity.id,
                    "type": entity.type,
                    "aliases": entity.aliases,
                    "description": entity.description,
                    "mentions_count": entity.mentions_count,
                    "tags": entity.tags,
                    "questions": entity.questions,
                })
    return result


@router.get("/concepts", response_model=List[Dict[str, Any]])
def list_wiki_concepts():
    store = _get_store()
    result = []
    concepts_dir = store.root / "wiki" / CONCEPTS_DIR
    if not concepts_dir.exists():
        return result
    for path in sorted(concepts_dir.glob("*.md")):
        slug = path.stem
        concept = store.read_concept(slug)
        if concept:
            result.append({
                "slug": slug,
                "id": concept.id,
                "parent_concept": concept.parent_concept,
                "definition": concept.definition,
                "examples": concept.examples,
                "related": concept.related,
                "tags": concept.tags,
                "questions": concept.questions,
            })
    return result


@router.get("/edges", response_model=List[Dict[str, Any]])
def list_wiki_edges():
    store = _get_store()
    return [
        {
            "id": e.id,
            "from": e.from_,
            "to": e.to,
            "relation": e.relation,
            "source_id": e.source_id,
            "confidence": e.confidence,
        }
        for e in store.read_all_edges()
    ]


@router.delete("/source/{slug}")
def delete_wiki_source(slug: str):
    store = _get_store()
    source_id = store.delete_source(slug)
    if source_id is None:
        raise HTTPException(status_code=404, detail=f"Source '{slug}' not found")
    return {"slug": slug, "source_id": source_id, "deleted": True}


@router.get("/source-raw", response_model=Dict[str, Any])
def get_source_raw(slug: str):
    """Return the original raw text (parsed.md) for a source."""
    store = _get_store()
    src = store.read_source(slug)
    if src is None:
        raise HTTPException(status_code=404, detail=f"Source '{slug}' not found")
    raw_text = store.read_raw_text(slug)
    if raw_text is None:
        raise HTTPException(status_code=404, detail=f"Raw text for source '{slug}' not found")
    return {"slug": slug, "title": src.title, "raw_text": raw_text}


@router.get("/claims-by-id", response_model=List[Dict[str, Any]])
def get_claims_by_id(ids: str = ""):
    """Return the exact claims for the comma-separated ids (with span), preserving request
    order. Missing ids are skipped. Used by the chat 'Pokaż fragmenty' view so it can show the
    precisely cited claims even when they fall outside a source's first-N node-detail window."""
    store = _get_store()
    wanted = [i.strip() for i in ids.split(",") if i.strip()]
    if not wanted:
        return []
    wanted_set = set(wanted)
    by_id = {c.id: c for c in store.read_all_claims() if c.id in wanted_set}
    result: List[Dict[str, Any]] = []
    for cid in wanted:
        c = by_id.get(cid)
        if c:
            result.append({
                "id": c.id, "text": c.text, "confidence": c.confidence,
                "polarity": c.polarity, "source_id": c.source_id,
                "span": {"start": c.span.start, "end": c.span.end, "text": c.span.text},
            })
    return result


@router.get("/node-detail", response_model=Dict[str, Any])
def get_wiki_node_detail(id: str):
    """
    id format: "entity:e_001", "concept:c_001", "source:src_001"
    Returns node metadata + up to 20 claims + up to 20 edges for the drawer.
    """
    store = _get_store()
    if ":" not in id:
        raise HTTPException(status_code=400, detail="id must be prefixed: entity:, concept:, or source:")

    prefix, inner_id = id.split(":", 1)

    claims = [
        {
            "id": c.id, "text": c.text, "confidence": c.confidence,
            "polarity": c.polarity, "source_id": c.source_id,
            "span": {"start": c.span.start, "end": c.span.end, "text": c.span.text},
        }
        for c in store.read_all_claims()
        if c.subject_id == id or (prefix == "source" and c.source_id == inner_id)
    ][:20]

    edges = [
        {
            "id": e.id, "from": e.from_, "to": e.to,
            "relation": e.relation, "source_id": e.source_id,
        }
        for e in store.read_all_edges()
        if e.from_ == id or e.to == id
    ][:20]

    base: Dict[str, Any] = {"id": id, "node_type": prefix, "claims": claims, "edges": edges}

    index_path = store.root / "wiki" / "00-Index" / "index.json"

    if prefix == "entity" and index_path.exists():
        idx = _json.loads(index_path.read_text(encoding="utf-8"))
        entry = next((e for e in idx.get("entities", []) if e.get("id") == inner_id), None)
        if entry:
            entity = store.read_entity(entry["slug"], entry["type"])
            if entity:
                base.update({
                    "slug": entry["slug"],
                    "title": entry["slug"].replace("-", " ").title(),
                    "entity_type": entity.type,
                    "description": entity.description,
                    "aliases": entity.aliases,
                    "tags": entity.tags,
                    "questions": entity.questions,
                })

    elif prefix == "concept" and index_path.exists():
        idx = _json.loads(index_path.read_text(encoding="utf-8"))
        entry = next((c for c in idx.get("concepts", []) if c.get("id") == inner_id), None)
        if entry:
            concept = store.read_concept(entry["slug"])
            if concept:
                base.update({
                    "slug": entry["slug"],
                    "title": entry["slug"].replace("-", " ").title(),
                    "description": concept.definition,
                    "tags": concept.tags,
                    "questions": concept.questions,
                })

    elif prefix == "source":
        for slug in store.list_sources():
            src = store.read_source(slug)
            if src and src.id == inner_id:
                base.update({
                    "slug": slug,
                    "title": src.title,
                    "description": src.summary,
                    "tags": src.tags,
                    "questions": src.questions,
                })
                break

    return base
