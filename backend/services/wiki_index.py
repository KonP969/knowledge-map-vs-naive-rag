import json
from typing import List

from services.wiki_store import WikiStore, ENTITIES_DIR


def regenerate_index(store: WikiStore) -> None:
    sources = _collect_sources(store)
    entities = _collect_entities(store)
    concepts = _collect_concepts(store)

    index_data = {"sources": sources, "entities": entities, "concepts": concepts}
    json_path = store.root / "wiki" / "00-Index" / "index.json"
    md_path = store.root / "wiki" / "00-Index" / "index.md"

    store._atomic_write(json_path, json.dumps(index_data, indent=2, ensure_ascii=False))
    store._atomic_write(md_path, _render_markdown(sources, entities, concepts))


def _collect_sources(store: WikiStore) -> List[dict]:
    out = []
    for slug in sorted(store.list_sources()):
        s = store.read_source(slug)
        out.append({
            "slug": slug, "id": s.id, "title": s.title,
            "tags": s.tags, "questions": s.questions,
            "summary": s.summary[:200],
        })
    return out


def _collect_entities(store: WikiStore) -> List[dict]:
    out = []
    base = store.root / "wiki" / ENTITIES_DIR
    if not base.exists():
        return out
    for type_dir in sorted(base.iterdir()):
        if not type_dir.is_dir():
            continue
        for path in sorted(type_dir.glob("*.md")):
            slug = path.stem
            e = store.read_entity(slug, type_dir.name)
            if e is None:
                continue
            out.append({
                "slug": slug, "id": e.id, "type": e.type,
                "aliases": e.aliases, "tags": e.tags,
                "questions": e.questions,
                "description_preview": e.description[:200],
            })
    return out


def _collect_concepts(store: WikiStore) -> List[dict]:
    out = []
    concepts_dir = store.root / "wiki" / "10-Concepts"
    if not concepts_dir.exists():
        return out
    for slug in sorted(p.stem for p in concepts_dir.glob("*.md")):
        c = store.read_concept(slug)
        out.append({
            "slug": slug, "id": c.id,
            "parent_concept": c.parent_concept,
            "tags": c.tags, "questions": c.questions,
            "definition_preview": c.definition[:200],
        })
    return out


def _render_markdown(sources: List[dict], entities: List[dict], concepts: List[dict]) -> str:
    lines = ["# Wiki Index", ""]
    lines.append(f"**Sources ({len(sources)})**")
    lines.append("")
    for s in sources:
        lines.append(f"- [{s['title']}](../30-Sources/{s['slug']}.md) — {s['summary']}")
    lines.append("")
    lines.append(f"**Entities ({len(entities)})**")
    lines.append("")
    for e in entities:
        lines.append(f"- `{e['type']}` [{e['slug']}](../20-Entities/{e['type']}/{e['slug']}.md) — {e['description_preview']}")
    lines.append("")
    lines.append(f"**Concepts ({len(concepts)})**")
    lines.append("")
    for c in concepts:
        lines.append(f"- [{c['slug']}](../10-Concepts/{c['slug']}.md) — {c['definition_preview']}")
    lines.append("")
    return "\n".join(lines)
