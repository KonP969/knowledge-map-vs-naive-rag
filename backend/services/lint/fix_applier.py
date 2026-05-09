from typing import Any, Dict, Optional

from models.lint_models import LintIssue
from services.wiki_store import WikiStore


class FixError(Exception):
    """Raised when a fix cannot be applied (not auto-fixable, missing payload, etc.)."""


def apply_fix(
    store: WikiStore,
    issue: LintIssue,
    edit_payload: Optional[Dict[str, Any]] = None,
) -> None:
    if not issue.auto_fixable:
        raise FixError(f"Issue {issue.id} ({issue.type}) is not auto-fixable")

    t = issue.type
    p = issue.payload

    if t == "dangling_source_ref":
        if p.get("kind") == "claim":
            store.delete_claim(p["claim_id"])
        elif p.get("kind") == "edge":
            store.delete_edge(p["edge_id"])
        else:
            raise FixError(f"Unknown payload.kind for dangling_source_ref: {p.get('kind')}")
        return

    if t == "dangling_node_ref":
        store.delete_edge(p["edge_id"])
        return

    if t == "corrupted_jsonl":
        path = store.root / "wiki" / p["file"]
        store.delete_jsonl_line(path, p["line_no"])
        return

    if t == "orphan_entity":
        store.delete_entity(p["slug"], p["entity_type"])
        return

    if t == "orphan_concept":
        store.delete_concept(p["slug"])
        return

    if t == "empty_description":
        if not edit_payload or "description" not in edit_payload:
            raise FixError("empty_description fix requires edit_payload['description']")
        new_text = edit_payload["description"]
        if p.get("kind") == "entity":
            store.update_entity_description(p["slug"], p["entity_type"], new_text)
        elif p.get("kind") == "concept":
            store.update_concept_description(p["slug"], new_text)
        else:
            raise FixError(f"empty_description fix not implemented for kind={p.get('kind')}")
        return

    raise FixError(f"No deterministic fix for type {t} (Phase 6)")
