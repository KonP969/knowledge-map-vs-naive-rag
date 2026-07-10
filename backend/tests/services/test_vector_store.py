import pytest
from services.vector_store import VectorStore


def test_search_returns_nearest_first():
    vs = VectorStore()
    vs.add(["a", "b", "c"], [[1, 0, 0], [0, 1, 0], [0.9, 0.1, 0.0]])
    res = vs.search([1, 0, 0], top_k=2)
    assert [r[0] for r in res] == ["a", "c"]  # a identical, c close, b orthogonal
    assert res[0][1] > 0.99


def test_identical_vector_scores_near_one():
    vs = VectorStore()
    vs.add(["x"], [[0.2, 0.4, 0.4]])
    res = vs.search([0.2, 0.4, 0.4], top_k=1)
    assert res[0][0] == "x"
    assert res[0][1] == pytest.approx(1.0, abs=1e-5)


def test_empty_store_search_returns_empty():
    assert VectorStore().search([1, 0, 0], top_k=5) == []


def test_top_k_caps_results():
    vs = VectorStore()
    vs.add(["a", "b", "c"], [[1, 0], [0.5, 0.5], [0, 1]])
    assert len(vs.search([1, 0], top_k=2)) == 2


def test_save_load_roundtrip(tmp_path):
    vs = VectorStore()
    vs.add(["a", "b"], [[1, 0], [0, 1]])
    p = tmp_path / "idx.npz"
    vs.save(p)
    loaded = VectorStore.load(p)
    assert loaded.ids == ["a", "b"]
    assert len(loaded) == 2
    assert loaded.search([1, 0], top_k=1)[0][0] == "a"


def test_len_and_ids_track_additions():
    vs = VectorStore()
    vs.add(["a"], [[1, 0]])
    vs.add(["b"], [[0, 1]])
    assert len(vs) == 2
    assert vs.ids == ["a", "b"]


def test_remove_drops_rows_by_id():
    vs = VectorStore()
    vs.add(["a", "b", "c"], [[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    removed = vs.remove(["b"])
    assert removed == 1
    assert vs.ids == ["a", "c"]
    # surviving vectors still search correctly
    assert vs.search([0, 0, 1], top_k=1)[0][0] == "c"
    # removed id is gone
    assert "b" not in vs


def test_remove_ignores_unknown_ids():
    vs = VectorStore()
    vs.add(["a"], [[1, 0]])
    assert vs.remove(["nope"]) == 0
    assert vs.ids == ["a"]


def test_remove_all_leaves_empty_store():
    vs = VectorStore()
    vs.add(["a", "b"], [[1, 0], [0, 1]])
    assert vs.remove(["a", "b"]) == 2
    assert vs.ids == []
    assert vs.search([1, 0], top_k=1) == []
