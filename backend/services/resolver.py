from typing import Any, Dict, List

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

    claims: List[Claim] = []
    for ce in classification.claims:
        claim_count += 1
        cid = f"cl_{claim_count:03d}"

        if ce.subject_type == "entity" and ce.subject_name in slug_to_entity:
            entity = slug_to_entity[ce.subject_name]
            subject_id = f"entity:{entity.id}"
        elif ce.subject_type == "concept" and ce.subject_name in slug_to_concept:
            concept = slug_to_concept[ce.subject_name]
            subject_id = f"concept:{concept.id}"
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
    """Count existing entity .md files to seed the ID counter.

    Entities are stored under <store.root>/wiki/20-Entities/<Type>/<slug>.md
    """
    entities_root = store.root / "wiki" / ENTITIES_DIR
    if not entities_root.exists():
        return 0
    return sum(1 for _ in entities_root.rglob("*.md"))


def _count_existing_concepts(store: WikiStore) -> int:
    """Count existing concept .md files to seed the ID counter.

    Concepts are stored under <store.root>/wiki/10-Concepts/<slug>.md
    """
    concepts_root = store.root / "wiki" / CONCEPTS_DIR
    if not concepts_root.exists():
        return 0
    return sum(1 for _ in concepts_root.glob("*.md"))
