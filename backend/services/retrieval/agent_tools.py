import json
from typing import Optional

from services.wiki_store import WikiStore


def read_index(store: WikiStore) -> str:
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return json.dumps({"sources": [], "entities": [], "concepts": []})
    return index_path.read_text(encoding="utf-8")


def search_entities(store: WikiStore, q: str, entity_type: Optional[str] = None) -> str:
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return "[]"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    q_lower = q.lower()
    results = []
    for e in data.get("entities", []):
        if entity_type and e.get("type", "").lower() != entity_type.lower():
            continue
        if (
            q_lower in e.get("slug", "").lower()
            or q_lower in e.get("id", "").lower()
            or any(q_lower in a.lower() for a in e.get("aliases", []))
        ):
            results.append(e)
    return json.dumps(results[:10], ensure_ascii=False)


def search_concepts(store: WikiStore, q: str) -> str:
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return "[]"
    data = json.loads(index_path.read_text(encoding="utf-8"))
    q_lower = q.lower()
    results = [
        c for c in data.get("concepts", [])
        if q_lower in c.get("slug", "").lower()
        or q_lower in c.get("definition_preview", "").lower()
    ]
    return json.dumps(results[:10], ensure_ascii=False)


def search_wiki_content(store: WikiStore, q: str) -> str:
    wiki_dir = store.root / "wiki"
    q_lower = q.lower()
    results = []
    for md_file in sorted(wiki_dir.rglob("*.md")):
        if "00-Index" in md_file.parts:
            continue
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue
        if q_lower in text.lower():
            idx = text.lower().find(q_lower)
            excerpt = text[max(0, idx - 50): idx + 150].replace("\n", " ")
            results.append({
                "file": str(md_file.relative_to(store.root)),
                "excerpt": excerpt,
            })
            if len(results) >= 5:
                break
    return json.dumps(results, ensure_ascii=False)


def search_text(store: WikiStore, q: str, scope: str = "raw") -> str:
    search_dir = store.root / scope
    if not search_dir.exists():
        return "[]"
    q_lower = q.lower()
    results = []
    for text_file in sorted(search_dir.rglob("*.md")):
        try:
            text = text_file.read_text(encoding="utf-8")
        except Exception:
            continue
        if q_lower in text.lower():
            idx = text.lower().find(q_lower)
            excerpt = text[max(0, idx - 50): idx + 150].replace("\n", " ")
            results.append({
                "file": str(text_file.relative_to(store.root)),
                "excerpt": excerpt,
            })
            if len(results) >= 5:
                break
    return json.dumps(results, ensure_ascii=False)


def get_node(store: WikiStore, id: str) -> str:
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return json.dumps({"error": "index not found"})
    data = json.loads(index_path.read_text(encoding="utf-8"))

    if ":" not in id:
        return json.dumps({"error": f"invalid id format: {id}"})
    prefix, node_id = id.split(":", 1)

    if prefix == "source":
        for s in data.get("sources", []):
            if s.get("id") == node_id:
                source = store.read_source(s["slug"])
                if source:
                    return json.dumps({
                        "id": source.id, "title": source.title,
                        "summary": source.summary, "questions": source.questions,
                        "key_takeaways": source.key_takeaways,
                    }, ensure_ascii=False)
    elif prefix == "entity":
        for e in data.get("entities", []):
            if e.get("id") == node_id:
                entity = store.read_entity(e["slug"], e["type"])
                if entity:
                    return json.dumps({
                        "id": entity.id, "type": entity.type,
                        "description": entity.description,
                        "questions": entity.questions, "aliases": entity.aliases,
                    }, ensure_ascii=False)
    elif prefix == "concept":
        for c in data.get("concepts", []):
            if c.get("id") == node_id:
                concept = store.read_concept(c["slug"])
                if concept:
                    return json.dumps({
                        "id": concept.id, "definition": concept.definition,
                        "examples": concept.examples, "questions": concept.questions,
                    }, ensure_ascii=False)

    return json.dumps({"error": f"node {id} not found"})


def get_claims(
    store: WikiStore,
    node_id: Optional[str] = None,
    query: Optional[str] = None,
    polarity: Optional[str] = None,
) -> str:
    claims = store.read_all_claims()
    if node_id:
        claims = [c for c in claims if c.subject_id == node_id or c.source_id == node_id]
    if polarity:
        claims = [c for c in claims if c.polarity == polarity]
    if query:
        q_lower = query.lower()
        claims = [c for c in claims if q_lower in c.text.lower()]
    result = [
        {
            "id": c.id, "text": c.text, "subject_id": c.subject_id,
            "source_id": c.source_id, "confidence": c.confidence, "polarity": c.polarity,
        }
        for c in claims[:20]
    ]
    return json.dumps(result, ensure_ascii=False)


def get_relations(
    store: WikiStore,
    node_id: str,
    direction: Optional[str] = None,
    relation_type: Optional[str] = None,
) -> str:
    edges = store.read_all_edges()
    result = []
    for e in edges:
        from_match = e.from_ == node_id
        to_match = e.to == node_id
        if direction == "out" and not from_match:
            continue
        if direction == "in" and not to_match:
            continue
        if direction is None and not (from_match or to_match):
            continue
        if relation_type and e.relation != relation_type:
            continue
        result.append({
            "id": e.id, "from": e.from_, "to": e.to,
            "relation": e.relation, "source_id": e.source_id,
        })
    return json.dumps(result[:20], ensure_ascii=False)


def read_source(store: WikiStore, source_id: str, section: Optional[str] = None) -> str:
    index_path = store.root / "wiki" / "00-Index" / "index.json"
    if not index_path.exists():
        return json.dumps({"error": "index not found"})
    data = json.loads(index_path.read_text(encoding="utf-8"))
    slug = next((s["slug"] for s in data.get("sources", []) if s.get("id") == source_id), None)
    if not slug:
        return json.dumps({"error": f"source {source_id} not found"})
    source = store.read_source(slug)
    if not source:
        return json.dumps({"error": f"slug {slug} not readable"})
    content = source.summary
    if section:
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if section.lower() in line.lower():
                excerpt = "\n".join(lines[i: i + 20])
                return json.dumps({"section": section, "content": excerpt}, ensure_ascii=False)
    return json.dumps({"id": source.id, "title": source.title, "content": content[:1000]}, ensure_ascii=False)


def query_log(store: WikiStore, filter: str) -> str:
    log_path = store.root / "wiki" / "log.md"
    if not log_path.exists():
        return "[]"
    f_lower = filter.lower()
    lines = log_path.read_text(encoding="utf-8").splitlines()
    matches = [line for line in lines if line.startswith("##") and f_lower in line.lower()]
    return json.dumps(matches[:20], ensure_ascii=False)
