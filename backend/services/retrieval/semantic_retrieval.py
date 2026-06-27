"""Semantic recall over the knowledge graph.

Embeds the question, finds the most similar CLAIMS, then anchors each hit back into the graph:
the claim's subject entity/concept (when it resolves to a real node) or, failing that, its
source. Each resulting Candidate carries the claim ids that made it relevant, so context
assembly can lead with the exact, verbatim facts instead of a generic node description."""
import json
from collections import OrderedDict
from typing import List, Optional

from models.retrieval_models import Candidate
from services.embeddings_service import EmbedFn, embed_query
from services.vector_store import VectorStore
from services.wiki_store import WikiStore


def _load_index(store: WikiStore) -> dict:
    path = store.root / "wiki" / "00-Index" / "index.json"
    if not path.exists():
        return {"sources": [], "entities": [], "concepts": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate_from(kind: str, node: dict, claim_ids: List[str], score: int) -> Candidate:
    if kind == "entity":
        return Candidate(
            artifact_id=f"entity:{node['id']}", artifact_type="entity",
            slug=node["slug"], title=f"{node.get('type', 'Entity')}: {node['slug']}",
            score=score, score_breakdown={"semantic": score},
            questions=node.get("questions", []), tags=node.get("tags", []),
            description_preview=(node.get("description_preview") or "")[:200],
            claim_ids=claim_ids,
        )
    if kind == "concept":
        return Candidate(
            artifact_id=f"concept:{node['id']}", artifact_type="concept",
            slug=node["slug"], title=node["slug"],
            score=score, score_breakdown={"semantic": score},
            questions=node.get("questions", []), tags=node.get("tags", []),
            description_preview=(node.get("definition_preview") or "")[:200],
            claim_ids=claim_ids,
        )
    return Candidate(
        artifact_id=f"source:{node['id']}", artifact_type="source",
        slug=node["slug"], title=node.get("title", node["slug"]),
        score=score, score_breakdown={"semantic": score},
        questions=node.get("questions", []), tags=node.get("tags", []),
        description_preview=(node.get("summary") or "")[:200],
        claim_ids=claim_ids,
    )


def semantic_candidates(
    question: str,
    store: WikiStore,
    *,
    vector_store: Optional[VectorStore],
    embed_fn: Optional[EmbedFn] = None,
    top_k_claims: int = 20,
) -> List[Candidate]:
    """Return graph candidates ranked by the semantic similarity of their claims."""
    if vector_store is None or len(vector_store) == 0 or top_k_claims <= 0:
        return []
    qvec = embed_query(question, embed_fn=embed_fn)
    hits = vector_store.search(qvec, top_k_claims)
    if not hits:
        return []

    claims_by_id = {c.id: c for c in store.read_all_claims()}
    index = _load_index(store)
    ent_by_id = {e["id"]: e for e in index.get("entities", [])}
    con_by_id = {c["id"]: c for c in index.get("concepts", [])}
    con_by_slug = {c["slug"]: c for c in index.get("concepts", [])}
    src_by_id = {s["id"]: s for s in index.get("sources", [])}

    # group hits by anchor node, preserving rank order, summing similarity
    anchors: "OrderedDict[str, dict]" = OrderedDict()
    for claim_id, sim in hits:
        claim = claims_by_id.get(claim_id)
        if claim is None:
            continue
        subj = claim.subject_id
        kind, node = None, None
        if subj.startswith("entity:"):
            inner = subj.split(":", 1)[1]
            if inner in ent_by_id:
                kind, node = "entity", ent_by_id[inner]
        elif subj.startswith("concept:"):
            inner = subj.split(":", 1)[1]
            node = con_by_id.get(inner) or con_by_slug.get(inner)
            if node:
                kind = "concept"
        if node is None:  # dangling subject -> anchor on the claim's source
            s = src_by_id.get(claim.source_id)
            if s is None:
                continue
            kind, node = "source", s

        art_id = f"{kind}:{node['id']}"
        a = anchors.get(art_id)
        if a is None:
            anchors[art_id] = {"kind": kind, "node": node, "claim_ids": [claim_id], "sim": sim}
        else:
            a["claim_ids"].append(claim_id)
            a["sim"] += sim

    candidates = [
        _candidate_from(a["kind"], a["node"], a["claim_ids"], max(1, int(round(a["sim"] * 10))))
        for a in anchors.values()
    ]
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def merge_candidates(lexical: List[Candidate], semantic: List[Candidate]) -> List[Candidate]:
    """Hybrid merge: union by artifact_id, summing scores. Semantic hits seed the entry so
    their claim_ids (and description) win; the lexical score is added on top."""
    by_id: "OrderedDict[str, Candidate]" = OrderedDict()
    for c in list(semantic) + list(lexical):
        existing = by_id.get(c.artifact_id)
        if existing is None:
            by_id[c.artifact_id] = c.model_copy(deep=True)
        else:
            existing.score += c.score
            if not existing.claim_ids and c.claim_ids:
                existing.claim_ids = list(c.claim_ids)
    out = list(by_id.values())
    out.sort(key=lambda c: c.score, reverse=True)
    return out
