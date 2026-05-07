import json
from typing import List, Set

from models.lint_models import LintIssue
from services.wiki_store import WikiStore


REQUIRED_CLAIM_FIELDS = {"id", "text", "subject_id", "source_id", "span", "confidence", "polarity"}
REQUIRED_EDGE_FIELDS = {"id", "from", "to", "relation", "source_id", "span", "confidence"}


def _read_jsonl_dicts(path) -> List[tuple]:
    """Yield (line_no, parsed_dict_or_None_on_error, raw_line) per non-blank line."""
    if not path.exists():
        return []
    out = []
    for i, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            out.append((i, json.loads(raw), raw))
        except json.JSONDecodeError:
            out.append((i, None, raw))
    return out


def check_provenance_missing(store: WikiStore) -> List[LintIssue]:
    issues: List[LintIssue] = []

    claims_path = store.root / "wiki" / "claims.jsonl"
    for line_no, parsed, _raw in _read_jsonl_dicts(claims_path):
        if parsed is None:
            continue  # corrupted lines handled in check_corrupted_jsonl
        missing = REQUIRED_CLAIM_FIELDS - set(parsed.keys())
        cid = parsed.get("id", f"line:{line_no}")
        if missing:
            issues.append(LintIssue(
                id=f"provenance_missing:claim:{cid}",
                type="provenance_missing",
                severity="error",
                location=f"claims.jsonl:{cid}",
                description=f"Claim {cid} is missing required fields: {sorted(missing)}",
                suggested_fix=None,
                auto_fixable=False,
                payload={"kind": "claim", "claim_id": cid, "missing": sorted(missing)},
            ))

    edges_path = store.root / "wiki" / "edges.jsonl"
    for line_no, parsed, _raw in _read_jsonl_dicts(edges_path):
        if parsed is None:
            continue
        missing = REQUIRED_EDGE_FIELDS - set(parsed.keys())
        eid = parsed.get("id", f"line:{line_no}")
        if missing:
            issues.append(LintIssue(
                id=f"provenance_missing:edge:{eid}",
                type="provenance_missing",
                severity="error",
                location=f"edges.jsonl:{eid}",
                description=f"Edge {eid} is missing required fields: {sorted(missing)}",
                suggested_fix=None,
                auto_fixable=False,
                payload={"kind": "edge", "edge_id": eid, "missing": sorted(missing)},
            ))

    return issues


def _collect_source_ids(store: WikiStore) -> Set[str]:
    ids: Set[str] = set()
    for slug in store.list_sources():
        s = store.read_source(slug)
        if s:
            ids.add(s.id)
    return ids


def _collect_node_ids(store: WikiStore) -> Set[str]:
    """Returns prefixed node IDs ('entity:e_001', 'concept:c_001')."""
    from services.wiki_store import ENTITIES_DIR, CONCEPTS_DIR
    ids: Set[str] = set()

    entities_dir = store.root / "wiki" / ENTITIES_DIR
    if entities_dir.exists():
        for type_dir in entities_dir.iterdir():
            if not type_dir.is_dir():
                continue
            for path in type_dir.glob("*.md"):
                ent = store.read_entity(path.stem, type_dir.name)
                if ent:
                    ids.add(f"entity:{ent.id}")

    concepts_dir = store.root / "wiki" / CONCEPTS_DIR
    if concepts_dir.exists():
        for path in concepts_dir.glob("*.md"):
            c = store.read_concept(path.stem)
            if c:
                ids.add(f"concept:{c.id}")

    return ids


def check_dangling_source_ref(store: WikiStore) -> List[LintIssue]:
    valid_sources = _collect_source_ids(store)
    issues: List[LintIssue] = []

    for c in store.read_all_claims():
        if c.source_id not in valid_sources:
            issues.append(LintIssue(
                id=f"dangling_source_ref:claim:{c.id}",
                type="dangling_source_ref",
                severity="error",
                location=f"claims.jsonl:{c.id}",
                description=f"Claim {c.id} references missing source {c.source_id}",
                suggested_fix="Delete claim",
                auto_fixable=True,
                payload={"kind": "claim", "claim_id": c.id, "source_id": c.source_id},
            ))

    for e in store.read_all_edges():
        if e.source_id not in valid_sources:
            issues.append(LintIssue(
                id=f"dangling_source_ref:edge:{e.id}",
                type="dangling_source_ref",
                severity="error",
                location=f"edges.jsonl:{e.id}",
                description=f"Edge {e.id} references missing source {e.source_id}",
                suggested_fix="Delete edge",
                auto_fixable=True,
                payload={"kind": "edge", "edge_id": e.id, "source_id": e.source_id},
            ))

    return issues


def check_dangling_node_ref(store: WikiStore) -> List[LintIssue]:
    valid_nodes = _collect_node_ids(store)
    issues: List[LintIssue] = []

    for e in store.read_all_edges():
        for endpoint, value in (("from", e.from_), ("to", e.to)):
            if value not in valid_nodes:
                issues.append(LintIssue(
                    id=f"dangling_node_ref:edge:{e.id}:{endpoint}",
                    type="dangling_node_ref",
                    severity="error",
                    location=f"edges.jsonl:{e.id}",
                    description=f"Edge {e.id} {endpoint}={value} points to missing node",
                    suggested_fix="Delete edge",
                    auto_fixable=True,
                    payload={"edge_id": e.id, "endpoint": endpoint, "missing_id": value},
                ))

    return issues


def check_corrupted_jsonl(store: WikiStore) -> List[LintIssue]:
    issues: List[LintIssue] = []
    for filename in ("claims.jsonl", "edges.jsonl"):
        path = store.root / "wiki" / filename
        if not path.exists():
            continue
        for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw.strip():
                continue
            try:
                json.loads(raw)
            except json.JSONDecodeError as exc:
                issues.append(LintIssue(
                    id=f"corrupted_jsonl:{filename}:{line_no}",
                    type="corrupted_jsonl",
                    severity="error",
                    location=f"{filename}:{line_no}",
                    description=f"Line {line_no} of {filename} is not valid JSON: {exc.msg}",
                    suggested_fix="Delete corrupt line (with .bak backup)",
                    auto_fixable=True,
                    payload={"file": filename, "line_no": line_no},
                ))
    return issues
