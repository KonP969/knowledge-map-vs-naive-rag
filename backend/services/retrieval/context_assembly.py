from typing import Dict, List, Tuple
from models.retrieval_models import Candidate, Selection
from services.wiki_store import WikiStore

DEFAULT_MAX_CLAIMS = 8


def _source_titles(store: WikiStore) -> Dict[str, str]:
    titles: Dict[str, str] = {}
    for slug in store.list_sources():
        src = store.read_source(slug)
        if src:
            titles[src.id] = src.title
    return titles


def _contradictions(edges, claim_ids):
    """(shown_claim_id, other_claim_id) for every `contradicts` edge touching shown claims."""
    out = []
    for e in edges:
        if e.relation != "contradicts":
            continue
        a, b = e.from_.split(":", 1)[-1], e.to.split(":", 1)[-1]
        if a in claim_ids:
            out.append((a, b))
        elif b in claim_ids:
            out.append((b, a))
    return out


def assemble_context(
    question: str,
    selection: Selection,
    candidates: List[Candidate],
    store: WikiStore,
    max_claims: int = DEFAULT_MAX_CLAIMS,
) -> Tuple[str, int]:
    """
    Stage 4 (deterministic). Builds markdown context with citation anchors.
    Returns (context_markdown, char_count).

    Every claim line names the article it comes from — the answer model can't
    tell "recommended for a white room" from "recommended for a grey salon"
    otherwise. Per node, the semantically matched claims lead, followed by the
    node's other claims, up to `max_claims` (raised for list/comparison questions).
    """
    selected_ids = {sa.artifact_id for sa in selection.selected}
    selected_candidates = [c for c in candidates if c.artifact_id in selected_ids]

    all_claims = store.read_all_claims()
    all_edges = store.read_all_edges()
    claims_by_id = {cl.id: cl for cl in all_claims}
    titles = _source_titles(store)
    names = {f"source:{sid}": t for sid, t in titles.items()}
    names.update({c.artifact_id: c.title for c in candidates})

    sections = [f"# Context for: {question}\n"]

    for cand in selected_candidates:
        parts = [f"## {cand.artifact_type.capitalize()}: {cand.title} [{cand.artifact_id}]"]

        # Lead with the semantically-relevant claims (verbatim), then the rest of the
        # node's claims (by subject, or by source for a source node). The generic node
        # description is demoted below the facts so the LLM answers from real claim text.
        source_key = cand.artifact_id.split(":", 1)[-1]
        relevant_claims = [claims_by_id[cid] for cid in cand.claim_ids if cid in claims_by_id]
        seen = {cl.id for cl in relevant_claims}
        for cl in all_claims:
            if cl.id in seen:
                continue
            if cl.subject_id == cand.artifact_id or (
                cand.artifact_type == "source" and cl.source_id == source_key
            ):
                relevant_claims.append(cl)
                seen.add(cl.id)
        if relevant_claims:
            parts.append("### Facts (claims):")
            shown = relevant_claims[:max_claims]
            for cl in shown:
                origin = titles.get(cl.source_id, cl.source_id)
                parts.append(
                    f"- [claim:{cl.id}] ({cl.polarity}) {cl.text} "
                    f"— from \"{origin}\" [source:{cl.source_id}] "
                    f"(confidence: {cl.confidence:.2f})"
                )
            # Contradictions recorded at ingest: bring the other side in even when its
            # node/source wasn't selected — otherwise the answer silently picks one.
            shown_ids = {cl.id for cl in shown}
            for this_id, other_id in _contradictions(all_edges, shown_ids):
                other = claims_by_id.get(other_id)
                if other is None or other_id in shown_ids:
                    continue
                origin = titles.get(other.source_id, other.source_id)
                parts.append(
                    f"- ⚠ CONTRADICTS [claim:{this_id}]: [claim:{other.id}] {other.text} "
                    f"— from \"{origin}\" [source:{other.source_id}]"
                )
                shown_ids.add(other_id)

        related_edges = [
            e for e in all_edges
            if e.from_ == cand.artifact_id or e.to == cand.artifact_id
        ]
        if related_edges:
            parts.append("\n### Relations:")
            for e in related_edges[:max(5, max_claims // 2)]:
                other = e.to if e.from_ == cand.artifact_id else e.from_
                label = names.get(other)
                shown = f"{label} ({other})" if label else other
                parts.append(f"- [{e.relation}] → {shown} [source:{e.source_id}]")

        if cand.questions:
            parts.append(f"\n### Answers questions: {', '.join(cand.questions[:3])}")

        if cand.description_preview:
            parts.append(f"\n(node summary: {cand.description_preview})")

        sections.append("\n".join(parts))

    context = "\n\n---\n\n".join(sections)
    return context, len(context)
