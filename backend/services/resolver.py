import re
from typing import Any, Dict, List

import frontmatter as fm

from typing import Optional

from models.ingest_models import SourceClassification
from models.wiki_models import Claim, Concept, Edge, Entity, Span
from services._slug import slugify
from services.node_index import NodeIndex, NodeRef
from services.wiki_store import CONCEPTS_DIR, ENTITIES_DIR, WikiStore


def _ground_span(span: Span, source_text: Optional[str]) -> Span:
    """Recompute a span's offsets by locating its verbatim text in the source.

    LLMs reliably copy short substrings but cannot count character offsets, so the
    start/end they return are untrustworthy. When the span's text is found verbatim in
    the source we replace the offsets with the real position; otherwise the span is left
    untouched (no source_text, empty text, or a paraphrase that isn't present verbatim).
    """
    if not source_text or not span.text:
        return span
    idx = source_text.find(span.text)
    if idx < 0:
        return span
    return Span(start=idx, end=idx + len(span.text), text=span.text)


def resolve_classification(
    classification: SourceClassification,
    source_id: str,
    store: WikiStore,
    overwrite_existing: bool = True,
    source_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Stage 3 (deterministic). Maps SourceClassification -> WikiStore objects.

    When source_text is provided, every span's offsets are re-grounded against it
    (see _ground_span) so claim/edge provenance points to the real document position
    instead of the LLM's hallucinated offsets.

    When overwrite_existing is False, entities/concepts that already exist are left
    exactly as they are (no merge of description/aliases/tags) — used by claim backfill
    to enrich claims without clobbering manually edited node content. Missing nodes are
    still created so that claims can link to real graph nodes.

    Returns dict with keys:
        entities_created, entities_merged,
        concepts_created, concepts_merged,
        claims (List[Claim]), edges (List[Edge]),
        entity_map, concept_map.
    """
    entities_created = 0
    entities_merged = 0
    concepts_created = 0
    concepts_merged = 0

    entity_count = _count_existing_entities(store)
    concept_count = _count_existing_concepts(store)
    claim_count = _max_id_number(store.read_all_claims(), "cl_")
    edge_count = _max_id_number(store.read_all_edges(), "ed_")

    # Store-wide name/alias index: links mentions and claim subjects to nodes that
    # earlier documents created, even when the wording or entity type differs.
    node_index = NodeIndex.from_store(store)

    slug_to_entity: Dict[str, Entity] = {}

    for em in classification.entity_mentions:
        slug = slugify(em.name)
        if not store.entity_exists(slug, em.type):
            same = node_index.find(em.name, prefer_kind="entity")
            if same is None:
                for alias in em.aliases:
                    same = node_index.find_entity_by_name(alias)
                    if same:
                        break
            if same is not None and same.kind == "entity":
                # Same node under another name or type: merge, don't duplicate.
                if overwrite_existing:
                    store.merge_entity(Entity(
                        id=same.id,
                        type=same.entity_type,
                        aliases=list(em.aliases) + ([em.name] if slug != same.slug else []),
                        description="",  # keep the core node's own description

                        mentions_count=1,
                        questions=classification.questions,
                        tags=classification.tags,
                    ), same.slug)
                entities_merged += 1
                slug_to_entity[em.name] = store.read_entity(same.slug, same.entity_type)
                continue
        if store.entity_exists(slug, em.type):
            if overwrite_existing:
                existing_entity = store.read_entity(slug, em.type)
                new_entity = Entity(
                    id=existing_entity.id,
                    type=em.type,
                    aliases=em.aliases,
                    description=em.description,
                    mentions_count=1,
                    questions=classification.questions,
                    tags=classification.tags,
                )
                store.merge_entity(new_entity, slug)
            entities_merged += 1
        else:
            entity_count += 1
            eid = f"e_{entity_count:03d}"
            new_entity = Entity(
                id=eid,
                type=em.type,
                aliases=em.aliases,
                description=em.description,
                mentions_count=1,
                questions=classification.questions,
                tags=classification.tags,
            )
            store.write_entity(new_entity, slug)
            node_index.add(NodeRef("entity", eid, slug, em.type), [slug] + list(em.aliases))
            entities_created += 1
        slug_to_entity[em.name] = store.read_entity(slug, em.type)

    slug_to_concept: Dict[str, Concept] = {}

    for cm in classification.concept_mentions:
        slug = slugify(cm.name)
        if store.concept_exists(slug):
            if overwrite_existing:
                existing_concept = store.read_concept(slug)
                new_concept = Concept(
                    id=existing_concept.id,
                    definition=cm.definition,
                    examples=[],
                    related=[],
                    questions=classification.questions,
                    tags=classification.tags,
                )
                store.merge_concept(new_concept, slug)
            concepts_merged += 1
        else:
            concept_count += 1
            cid = f"c_{concept_count:03d}"
            new_concept = Concept(
                id=cid,
                definition=cm.definition,
                examples=[],
                related=[],
                questions=classification.questions,
                tags=classification.tags,
            )
            store.write_concept(new_concept, slug)
            node_index.add(NodeRef("concept", cid, slug), [slug])
            concepts_created += 1
        slug_to_concept[cm.name] = store.read_concept(slug)

    # Build lowercase lookup dicts for case-insensitive subject_name matching
    entity_lookup = {k.lower(): v for k, v in slug_to_entity.items()}
    for em in classification.entity_mentions:
        if em.name in slug_to_entity:
            for alias in em.aliases:
                entity_lookup.setdefault(alias.lower(), slug_to_entity[em.name])
    concept_lookup = {k.lower(): v for k, v in slug_to_concept.items()}

    claims: List[Claim] = []
    stub_edges: List[Any] = []  # (NodeRef, Span) of stub concepts created below
    for ce in classification.claims:
        claim_count += 1
        cid = f"cl_{claim_count:03d}"
        name = ce.subject_name.lower()

        if ce.subject_type == "entity" and name in entity_lookup:
            subject_id = f"entity:{entity_lookup[name].id}"
        elif ce.subject_type == "concept" and name in concept_lookup:
            subject_id = f"concept:{concept_lookup[name].id}"
        elif name in entity_lookup:
            subject_id = f"entity:{entity_lookup[name].id}"
        elif name in concept_lookup:
            subject_id = f"concept:{concept_lookup[name].id}"
        else:
            ref = node_index.find(ce.subject_name, prefer_kind=ce.subject_type)
            if ref is None:
                # A topic the classifier used as a subject but never declared as a
                # mention. Give it a node so its claims join the map (and meet the
                # same topic's claims from other documents) instead of dangling.
                ref = _create_stub_concept(ce, store, classification, concept_count + 1)
                concept_count += 1
                concepts_created += 1
                node_index.add(ref, [ref.slug])
                stub_edges.append((ref, ce.span))
            subject_id = ref.subject_id

        claim = Claim(
            id=cid,
            text=ce.text,
            subject_id=subject_id,
            source_id=source_id,
            span=_ground_span(ce.span, source_text),
            confidence=ce.confidence,
            polarity=ce.polarity,
        )
        claims.append(claim)

    edges: List[Edge] = []

    for em in classification.entity_mentions:
        entity = slug_to_entity.get(em.name)
        if entity is None:
            continue
        edge_count += 1
        edge = Edge(
            id=f"ed_{edge_count:03d}",
            **{"from": f"source:{source_id}"},
            to=f"entity:{entity.id}",
            relation="mentions",
            source_id=source_id,
            span=_ground_span(em.span, source_text),
            confidence=1.0,
        )
        edges.append(edge)

    for cm in classification.concept_mentions:
        concept = slug_to_concept.get(cm.name)
        if concept is None:
            continue
        edge_count += 1
        edge = Edge(
            id=f"ed_{edge_count:03d}",
            **{"from": f"source:{source_id}"},
            to=f"concept:{concept.id}",
            relation="mentions",
            source_id=source_id,
            span=_ground_span(cm.span, source_text),
            confidence=1.0,
        )
        edges.append(edge)

    for ref, span in stub_edges:
        edge_count += 1
        edges.append(Edge(
            id=f"ed_{edge_count:03d}",
            **{"from": f"source:{source_id}"},
            to=ref.subject_id,
            relation="mentions",
            source_id=source_id,
            span=_ground_span(span, source_text),
            confidence=1.0,
        ))

    return {
        "entities_created": entities_created,
        "entities_merged": entities_merged,
        "concepts_created": concepts_created,
        "concepts_merged": concepts_merged,
        "claims": claims,
        "edges": edges,
        "entity_map": slug_to_entity,
        "concept_map": slug_to_concept,
    }


def _create_stub_concept(ce, store: WikiStore, classification, n: int) -> NodeRef:
    """Concept node for an undeclared claim subject; definition seeded from the claim."""
    slug = slugify(ce.subject_name)
    if store.concept_exists(slug):  # defensive: index miss on an existing file
        existing = store.read_concept(slug)
        return NodeRef("concept", existing.id, slug)
    cid = f"c_{n:03d}"
    store.write_concept(Concept(
        id=cid,
        definition=ce.text,
        examples=[],
        related=[],
        questions=classification.questions,
        tags=classification.tags,
    ), slug)
    return NodeRef("concept", cid, slug)


def _max_id_number(items: List[Any], prefix: str) -> int:
    """Highest numeric suffix among ids like '<prefix>NNN' (robust to deletions/gaps)."""
    max_n = 0
    pat = re.compile(rf"{re.escape(prefix)}(\d+)")
    for it in items:
        m = pat.match(it.id)
        if m:
            max_n = max(max_n, int(m.group(1)))
    return max_n


def _count_existing_entities(store: WikiStore) -> int:
    """Return the highest entity numeric ID found in the vault (seeds the counter)."""
    entities_root = store.root / "wiki" / ENTITIES_DIR
    if not entities_root.exists():
        return 0
    max_n = 0
    for type_dir in entities_root.iterdir():
        if not type_dir.is_dir():
            continue
        for md in type_dir.glob("*.md"):
            try:
                post = fm.load(str(md))
                m = re.match(r"e_(\d+)", str(post.get("id", "")))
                if m:
                    max_n = max(max_n, int(m.group(1)))
            except Exception:
                pass
    return max_n


def _count_existing_concepts(store: WikiStore) -> int:
    """Return the highest concept numeric ID found in the vault (seeds the counter)."""
    concepts_root = store.root / "wiki" / CONCEPTS_DIR
    if not concepts_root.exists():
        return 0
    max_n = 0
    for md in concepts_root.glob("*.md"):
        try:
            post = fm.load(str(md))
            m = re.match(r"c_(\d+)", str(post.get("id", "")))
            if m:
                max_n = max(max_n, int(m.group(1)))
        except Exception:
            pass
    return max_n
