import os
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter
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
            })
    return result


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
