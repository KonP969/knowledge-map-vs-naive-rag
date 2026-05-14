from typing import List, Set

from models.lint_models import LintIssue
from services.wiki_store import CONCEPTS_DIR, ENTITIES_DIR, WikiStore


MIN_DESCRIPTION_CHARS = 30


def _all_entities(store: WikiStore):
    base = store.root / "wiki" / ENTITIES_DIR
    if not base.exists():
        return
    for type_dir in base.iterdir():
        if not type_dir.is_dir():
            continue
        for path in type_dir.glob("*.md"):
            ent = store.read_entity(path.stem, type_dir.name)
            if ent:
                yield path.stem, ent


def _all_concepts(store: WikiStore):
    base = store.root / "wiki" / CONCEPTS_DIR
    if not base.exists():
        return
    for path in base.glob("*.md"):
        c = store.read_concept(path.stem)
        if c:
            yield path.stem, c


def _all_sources(store: WikiStore):
    for slug in store.list_sources():
        s = store.read_source(slug)
        if s:
            yield slug, s


def check_orphan_entity(store: WikiStore) -> List[LintIssue]:
    edges = store.read_all_edges()
    referenced: Set[str] = set()
    for e in edges:
        referenced.add(e.from_)
        referenced.add(e.to)

    claims_subjects = {c.subject_id for c in store.read_all_claims()}

    issues: List[LintIssue] = []
    for slug, ent in _all_entities(store):
        node_id = f"entity:{ent.id}"
        if node_id in referenced or node_id in claims_subjects:
            continue
        issues.append(LintIssue(
            id=f"orphan_entity:{ent.id}",
            type="orphan_entity",
            severity="warning",
            location=node_id,
            description=f"Entity {ent.id} ({ent.type}/{slug}) has no edges and no claims",
            suggested_fix="Delete entity",
            auto_fixable=True,
            payload={"entity_id": ent.id, "slug": slug, "entity_type": ent.type},
        ))
    return issues


def check_orphan_concept(store: WikiStore) -> List[LintIssue]:
    incoming: Set[str] = {e.to for e in store.read_all_edges()}
    issues: List[LintIssue] = []
    for slug, c in _all_concepts(store):
        node_id = f"concept:{c.id}"
        if node_id in incoming:
            continue
        issues.append(LintIssue(
            id=f"orphan_concept:{c.id}",
            type="orphan_concept",
            severity="warning",
            location=node_id,
            description=f"Concept {c.id} ({slug}) has no incoming edges (no bridge role)",
            suggested_fix="Delete concept",
            auto_fixable=True,
            payload={"concept_id": c.id, "slug": slug},
        ))
    return issues


def check_empty_questions(store: WikiStore) -> List[LintIssue]:
    issues: List[LintIssue] = []

    for slug, ent in _all_entities(store):
        if not ent.questions:
            node_id = f"entity:{ent.id}"
            issues.append(LintIssue(
                id=f"empty_questions:entity:{ent.id}",
                type="empty_questions",
                severity="warning",
                location=node_id,
                description=f"Entity {ent.id} has empty questions[]",
                suggested_fix="Generate analytical questions (LLM)",
                auto_fixable=True,
                payload={"node_id": node_id, "slug": slug, "entity_type": ent.type},
            ))

    for slug, c in _all_concepts(store):
        if not c.questions:
            node_id = f"concept:{c.id}"
            issues.append(LintIssue(
                id=f"empty_questions:concept:{c.id}",
                type="empty_questions",
                severity="warning",
                location=node_id,
                description=f"Concept {c.id} has empty questions[]",
                suggested_fix="Generate analytical questions (LLM)",
                auto_fixable=True,
                payload={"node_id": node_id, "slug": slug},
            ))

    for slug, s in _all_sources(store):
        if not s.questions:
            node_id = f"source:{s.id}"
            issues.append(LintIssue(
                id=f"empty_questions:source:{s.id}",
                type="empty_questions",
                severity="warning",
                location=node_id,
                description=f"Source {s.id} has empty questions[]",
                suggested_fix="Generate analytical questions (LLM)",
                auto_fixable=True,
                payload={"node_id": node_id, "slug": slug},
            ))

    return issues


def check_empty_description(store: WikiStore) -> List[LintIssue]:
    issues: List[LintIssue] = []

    for slug, ent in _all_entities(store):
        if len(ent.description.strip()) < MIN_DESCRIPTION_CHARS:
            node_id = f"entity:{ent.id}"
            issues.append(LintIssue(
                id=f"empty_description:entity:{ent.id}",
                type="empty_description",
                severity="warning",
                location=node_id,
                description=f"Entity {ent.id} description is shorter than {MIN_DESCRIPTION_CHARS} chars",
                suggested_fix="Edit description inline",
                auto_fixable=True,
                payload={"node_id": node_id, "kind": "entity", "slug": slug, "entity_type": ent.type},
            ))

    for slug, c in _all_concepts(store):
        if len(c.definition.strip()) < MIN_DESCRIPTION_CHARS:
            node_id = f"concept:{c.id}"
            issues.append(LintIssue(
                id=f"empty_description:concept:{c.id}",
                type="empty_description",
                severity="warning",
                location=node_id,
                description=f"Concept {c.id} definition is shorter than {MIN_DESCRIPTION_CHARS} chars",
                suggested_fix="Edit definition inline",
                auto_fixable=True,
                payload={"node_id": node_id, "kind": "concept", "slug": slug},
            ))

    for slug, s in _all_sources(store):
        if len(s.summary.strip()) < MIN_DESCRIPTION_CHARS:
            node_id = f"source:{s.id}"
            issues.append(LintIssue(
                id=f"empty_description:source:{s.id}",
                type="empty_description",
                severity="warning",
                location=node_id,
                description=f"Source {s.id} summary is shorter than {MIN_DESCRIPTION_CHARS} chars",
                suggested_fix=None,
                auto_fixable=False,
                payload={"node_id": node_id, "kind": "source", "slug": slug},
            ))

    return issues
