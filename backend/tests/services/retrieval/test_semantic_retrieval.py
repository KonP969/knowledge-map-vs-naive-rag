from datetime import datetime

from models.wiki_models import Claim, Entity, Source, Span
from models.retrieval_models import Candidate
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from services.semantic_index import build_claim_index
from services.retrieval.semantic_retrieval import semantic_candidates, merge_candidates


def _cand(art_id, score, claim_ids=None):
    return Candidate(artifact_id=art_id, artifact_type="entity", slug="s", title="t",
                     score=score, score_breakdown={}, questions=[], tags=[],
                     description_preview="", claim_ids=claim_ids or [])


def test_merge_unions_sums_scores_and_keeps_semantic_claim_ids():
    lexical = [_cand("entity:e_001", 3), _cand("source:src_001", 1)]
    semantic = [_cand("entity:e_001", 10, ["cl_1"]), _cand("concept:c_002", 8, ["cl_2"])]
    merged = merge_candidates(lexical, semantic)
    by_id = {c.artifact_id: c for c in merged}
    assert by_id["entity:e_001"].score == 13            # summed across both paths
    assert by_id["entity:e_001"].claim_ids == ["cl_1"]  # semantic claim_ids preserved
    assert "concept:c_002" in by_id and "source:src_001" in by_id
    assert merged[0].artifact_id == "entity:e_001"      # sorted by score desc


def test_merge_with_empty_semantic_is_lexical():
    lexical = [_cand("entity:e_001", 3)]
    assert [c.artifact_id for c in merge_candidates(lexical, [])] == ["entity:e_001"]


def _embed(batch):
    # "frame" questions/claims -> one axis; everything else -> the other. No network.
    return [[1.0, 0.0] if "frame" in t.lower() else [0.0, 1.0] for t in batch]


def _seed(tmp_path):
    store = WikiStore(root=tmp_path)
    store.write_source(Source(
        id="src_001", title="Catalog", type="pdf", raw_path="raw/c/parsed.md",
        ingested_at=datetime(2026, 6, 1), summary="S", key_takeaways=[], questions=[], tags=[],
    ), slug="catalog")
    store.write_entity(Entity(
        id="e_001", type="Product", aliases=[], description="A Porta door model.",
        mentions_count=1, questions=[], tags=[],
    ), slug="porta-vector-premium")
    store.append_claim(Claim(
        id="cl_001", text="Porta Vector Premium has an aluminum frame.",
        subject_id="entity:e_001", source_id="src_001",
        span=Span(start=0, end=5, text="Porta"), confidence=0.9, polarity="asserts",
    ))
    store.append_claim(Claim(
        id="cl_002", text="The bedroom uses neutral colours.",
        subject_id="entity:e_002", source_id="src_001",
        span=Span(start=0, end=5, text="The b"), confidence=0.9, polarity="asserts",
    ))
    regenerate_index(store)
    return store


def test_semantic_recall_returns_subject_entity_with_claim_ids(tmp_path):
    store = _seed(tmp_path)
    vs = build_claim_index(store, embed_fn=_embed)
    cands = semantic_candidates("what frame does it have", store,
                                vector_store=vs, embed_fn=_embed, top_k_claims=1)
    assert cands, "expected at least one candidate"
    top = cands[0]
    assert top.artifact_id == "entity:e_001"
    assert "cl_001" in top.claim_ids
    # the unrelated bedroom claim's subject is not surfaced for a frame question
    assert all("e_002" not in c.artifact_id for c in cands)


def test_dangling_subject_falls_back_to_source(tmp_path):
    store = WikiStore(root=tmp_path)
    store.write_source(Source(
        id="src_001", title="Catalog", type="pdf", raw_path="raw/c/parsed.md",
        ingested_at=datetime(2026, 6, 1), summary="S", key_takeaways=[], questions=[], tags=[],
    ), slug="catalog")
    store.append_claim(Claim(
        id="cl_001", text="The frame is steel.", subject_id="entity:ghost-not-in-index",
        source_id="src_001", span=Span(start=0, end=3, text="The"), confidence=0.9, polarity="asserts",
    ))
    regenerate_index(store)
    vs = build_claim_index(store, embed_fn=_embed)
    cands = semantic_candidates("frame", store, vector_store=vs, embed_fn=_embed, top_k_claims=1)
    assert cands[0].artifact_id == "source:src_001"
    assert "cl_001" in cands[0].claim_ids


def test_no_index_or_no_hits_returns_empty(tmp_path):
    store = _seed(tmp_path)
    vs = build_claim_index(store, embed_fn=_embed)
    # query orthogonal to everything (empty hits possible) still must not crash
    out = semantic_candidates("zzz", store, vector_store=vs, embed_fn=_embed, top_k_claims=0)
    assert out == []
