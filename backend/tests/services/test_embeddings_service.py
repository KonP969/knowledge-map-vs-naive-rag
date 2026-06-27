from services.embeddings_service import embed_texts, embed_query


def test_embed_texts_empty_returns_empty():
    assert embed_texts([], embed_fn=lambda batch: [[1.0] for _ in batch]) == []


def test_embed_texts_preserves_order_and_count():
    def fake(batch):
        # vector encodes the input so we can assert ordering
        return [[float(len(t))] for t in batch]

    out = embed_texts(["a", "bb", "ccc"], embed_fn=fake)
    assert out == [[1.0], [2.0], [3.0]]


def test_embed_texts_batches_cover_all_inputs():
    seen = []

    def fake(batch):
        seen.append(list(batch))
        return [[0.0] for _ in batch]

    texts = [f"t{i}" for i in range(5)]
    out = embed_texts(texts, embed_fn=fake, batch_size=2)
    # batched 2+2+1, every input embedded exactly once, order intact
    assert [len(b) for b in seen] == [2, 2, 1]
    assert [t for b in seen for t in b] == texts
    assert len(out) == 5


def test_embed_query_returns_single_vector():
    out = embed_query("hello", embed_fn=lambda batch: [[7.0] for _ in batch])
    assert out == [7.0]
