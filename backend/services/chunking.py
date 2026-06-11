"""Split large source documents into chunks for dense extraction, and merge the
per-chunk classifications back into one.

A single LLM extraction call over a very large document yields sparse, summary-level
output (the model summarises instead of exhaustively extracting). Chunking the text into
~max_chars pieces, classifying each, and merging keeps entity/concept/claim density high.
Span offsets stay chunk-local but are re-grounded against the full source text later in
resolve_classification, so the merge does not need to fix them.
"""
from typing import List

from models.ingest_models import (
    ClaimExtraction, ConceptMention, EntityMention, SourceClassification,
)


def chunk_text(text: str, max_chars: int = 5000) -> List[str]:
    """Split text into chunks of at most max_chars, preferring paragraph boundaries.

    A paragraph larger than max_chars on its own is hard-split so no chunk exceeds the
    limit. Content is preserved exactly (joining the chunks reproduces the input modulo
    the paragraph separators reintroduced between accumulated paragraphs)."""
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    cur = ""
    for para in text.split("\n\n"):
        if cur and len(cur) + len(para) + 2 > max_chars:
            chunks.append(cur)
            cur = para
        else:
            cur = f"{cur}\n\n{para}" if cur else para
    if cur:
        chunks.append(cur)

    final: List[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            final.append(c)
        else:
            for i in range(0, len(c), max_chars):
                final.append(c[i:i + max_chars])
    return final


def _union(parts: List[SourceClassification], field: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for p in parts:
        for v in getattr(p, field):
            if v not in seen:
                seen.add(v)
                out.append(v)
    return out


def merge_classifications(parts: List[SourceClassification]) -> SourceClassification:
    """Merge per-chunk classifications. Title/description come from the first part;
    tags/questions/key_takeaways are unioned; entity/concept mentions are deduped by name
    (first occurrence wins — the store merges aliases later); claims are concatenated."""
    if len(parts) == 1:
        return parts[0]

    base = parts[0]

    entities: List[EntityMention] = []
    seen_e = set()
    for p in parts:
        for em in p.entity_mentions:
            key = em.name.strip().lower()
            if key not in seen_e:
                seen_e.add(key)
                entities.append(em)

    concepts: List[ConceptMention] = []
    seen_c = set()
    for p in parts:
        for cm in p.concept_mentions:
            key = cm.name.strip().lower()
            if key not in seen_c:
                seen_c.add(key)
                concepts.append(cm)

    claims: List[ClaimExtraction] = []
    for p in parts:
        claims.extend(p.claims)

    return SourceClassification(
        title=base.title,
        description=base.description,
        tags=_union(parts, "tags"),
        questions=_union(parts, "questions"),
        key_takeaways=_union(parts, "key_takeaways"),
        entity_mentions=entities,
        concept_mentions=concepts,
        claims=claims,
    )
