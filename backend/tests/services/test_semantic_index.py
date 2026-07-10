from models.wiki_models import Claim, Span
from services.wiki_store import WikiStore
from services.semantic_index import (
    build_claim_index, load_claim_index, claim_index_path, add_claims_to_index,
)


def _claim(cid, text):
    return Claim(id=cid, text=text, subject_id="entity:e_001", source_id="src_001",
                 span=Span(start=0, end=1, text="x"), confidence=0.9, polarity="asserts")


def _fake_embed(batch):
    # deterministic 2-d vector from text so search is predictable, no network
    return [[float(len(t)), float(ord(t[0]))] for t in batch]


def test_build_claim_index_one_vector_per_claim(tmp_path):
    store = WikiStore(root=tmp_path)
    store.append_claim(_claim("cl_001", "alpha"))
    store.append_claim(_claim("cl_002", "beta gamma"))
    vs = build_claim_index(store, embed_fn=_fake_embed)
    assert sorted(vs.ids) == ["cl_001", "cl_002"]
    assert len(vs) == 2


def test_build_persists_and_loads(tmp_path):
    store = WikiStore(root=tmp_path)
    store.append_claim(_claim("cl_001", "alpha"))
    build_claim_index(store, embed_fn=_fake_embed)
    assert claim_index_path(store).exists()
    loaded = load_claim_index(store)
    assert loaded is not None
    assert loaded.ids == ["cl_001"]


def test_load_missing_returns_none(tmp_path):
    assert load_claim_index(WikiStore(root=tmp_path)) is None


def test_index_search_finds_matching_claim(tmp_path):
    store = WikiStore(root=tmp_path)
    store.append_claim(_claim("cl_001", "alpha"))
    store.append_claim(_claim("cl_002", "zzzzzzzz"))
    vs = build_claim_index(store, embed_fn=_fake_embed)
    q = _fake_embed(["alpha"])[0]
    assert vs.search(q, top_k=1)[0][0] == "cl_001"


def test_build_empty_graph_is_safe(tmp_path):
    vs = build_claim_index(WikiStore(root=tmp_path), embed_fn=_fake_embed)
    assert len(vs) == 0
    assert load_claim_index(WikiStore(root=tmp_path)).ids == []


def test_add_claims_appends_to_existing_index(tmp_path):
    store = WikiStore(root=tmp_path)
    store.append_claim(_claim("cl_001", "alpha"))
    build_claim_index(store, embed_fn=_fake_embed)
    new = _claim("cl_002", "beta")
    store.append_claim(new)
    add_claims_to_index(store, [new], embed_fn=_fake_embed)
    assert sorted(load_claim_index(store).ids) == ["cl_001", "cl_002"]


def test_add_claims_creates_index_when_absent(tmp_path):
    store = WikiStore(root=tmp_path)
    add_claims_to_index(store, [_claim("cl_001", "alpha")], embed_fn=_fake_embed)
    assert load_claim_index(store).ids == ["cl_001"]


def test_add_claims_skips_already_indexed(tmp_path):
    store = WikiStore(root=tmp_path)
    c = _claim("cl_001", "alpha")
    add_claims_to_index(store, [c], embed_fn=_fake_embed)
    add_claims_to_index(store, [c], embed_fn=_fake_embed)
    assert load_claim_index(store).ids == ["cl_001"]  # no duplicate


def test_remove_claims_from_index_prunes_and_persists(tmp_path):
    from services.semantic_index import (
        add_claims_to_index, remove_claims_from_index, load_claim_index,
    )
    store = WikiStore(root=tmp_path)
    add_claims_to_index(
        store,
        [_claim("cl_001", "alpha"), _claim("cl_002", "beta"), _claim("cl_003", "gamma")],
        embed_fn=_fake_embed,
    )
    vs = remove_claims_from_index(store, ["cl_002"])
    assert set(vs.ids) == {"cl_001", "cl_003"}
    # persisted to disk, not just in memory
    assert set(load_claim_index(store).ids) == {"cl_001", "cl_003"}
