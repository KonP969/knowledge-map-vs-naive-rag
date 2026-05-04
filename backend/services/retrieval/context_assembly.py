from typing import List, Tuple
from models.retrieval_models import Candidate, Selection
from services.wiki_store import WikiStore


def assemble_context(
    question: str,
    selection: Selection,
    candidates: List[Candidate],
    store: WikiStore,
) -> Tuple[str, int]:
    """
    Stage 4 (deterministic). Builds markdown context with citation anchors.
    Returns (context_markdown, char_count).
    """
    selected_ids = {sa.artifact_id for sa in selection.selected}
    selected_candidates = [c for c in candidates if c.artifact_id in selected_ids]

    all_claims = store.read_all_claims()
    all_edges = store.read_all_edges()

    sections = [f"# Context for: {question}\n"]

    for cand in selected_candidates:
        parts = [
            f"## {cand.artifact_type.capitalize()}: {cand.title} [{cand.artifact_id}]",
            cand.description_preview,
        ]

        relevant_claims = [
            cl for cl in all_claims
            if cl.subject_id == cand.artifact_id
            or cl.source_id == cand.artifact_id.split(":", 1)[-1]
        ]
        if relevant_claims:
            parts.append("\n### Claims:")
            for cl in relevant_claims[:5]:
                parts.append(
                    f"- [claim:{cl.id}] ({cl.polarity}) {cl.text} "
                    f"(confidence: {cl.confidence:.2f})"
                )

        related_edges = [
            e for e in all_edges
            if e.from_ == cand.artifact_id or e.to == cand.artifact_id
        ]
        if related_edges:
            parts.append("\n### Relations:")
            for e in related_edges[:5]:
                other = e.to if e.from_ == cand.artifact_id else e.from_
                parts.append(f"- [{e.relation}] → {other} [source:{e.source_id}]")

        if cand.questions:
            parts.append(f"\n### Answers questions: {', '.join(cand.questions[:3])}")

        sections.append("\n".join(parts))

    context = "\n\n---\n\n".join(sections)
    return context, len(context)
