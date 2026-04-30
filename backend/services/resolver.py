import re
from typing import Any, Dict, List

import frontmatter as fm

from models.ingest_models import SourceClassification
from models.wiki_models import Claim, Concept, Edge, Entity
from services._slug import slugify
from services.wiki_store import CONCEPTS_DIR, ENTITIES_DIR, WikiStore


def resolve_classification(
    classification: SourceClassification,
    source_id: str,
    store: WikiStore,
) -> Dict[str, Any]:
    """
    Stage 3 (deterministic). Maps SourceClassification -> WikiStore objects.

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
    claim_count = len(store.read_all_claims())
    edge_count = len(store.read_all_edges())

    slug_to_entity: Dict[str, Entity] = {}

    for em in classification.entity_mentions:
        slug = slugify(em.name)
        if store.entity_exists(slug, em.type):
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
            entities_created += 1
        slug_to_entity[em.name] = store.read_entity(slug, em.type)

    slug_to_concept: Dict[str, Concept] = {}

    for cm in classification.concept_mentions:
        slug = slugify(cm.name)
        if store.concept_exists(slug):
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
            concepts_created += 1
        slug_to_concept[cm.name] = store.read_concept(slug)

    # Build lowercase lookup dicts for case-insensitive subject_name matching
    entity_lookup = {k.lower(): v for k, v in slug_to_entity.items()}
    concept_lookup = {k.lower(): v for k, v in slug_to_concept.items()}

    claims: List[Claim] = []
    for ce in classification.claims:
        claim_count += 1
        cid = f"cl_{claim_count:03d}"

        if ce.subject_type == "entity" and ce.subject_name.lower() in entity_lookup:
            subject_id = f"entity:{entity_lookup[ce.subject_name.lower()].id}"
        elif ce.subject_type == "concept" and ce.subject_name.lower() in concept_lookup:
            subject_id = f"concept:{concept_lookup[ce.subject_name.lower()].id}"
        else:
            subject_id = f"{ce.subject_type}:{slugify(ce.subject_name)}"

        claim = Claim(
            id=cid,
            text=ce.text,
            subject_id=subject_id,
            source_id=source_id,
            span=ce.span,
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
            span=em.span,
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
            span=cm.span,
            confidence=1.0,
        )
        edges.append(edge)

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
