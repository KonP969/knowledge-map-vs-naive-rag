from services.chunkers.fixed_size import chunk_fixed_size
from services.chunkers.recursive import chunk_recursive


def test_fixed_size_basic():
    text = "A" * 100
    chunks = chunk_fixed_size(text, chunk_size=30, overlap=10)
    assert len(chunks) > 1
    for c in chunks:
        assert c["content"]
        assert c["start_char"] >= 0
        assert c["end_char"] <= len(text)


def test_fixed_size_no_overlap():
    text = "Hello World " * 20
    chunks = chunk_fixed_size(text, chunk_size=50, overlap=0)
    total_chars = sum(len(c["content"]) for c in chunks)
    assert total_chars >= len(text) - 10  # allow minor trim


def test_fixed_size_overlap_boundaries():
    text = "X" * 200
    chunks = chunk_fixed_size(text, chunk_size=50, overlap=20)
    # Second chunk should start before end of first
    assert chunks[1]["start_char"] < chunks[0]["end_char"]


def test_recursive_basic():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_recursive(text, separators=["\n\n", "\n", " "], chunk_size=30)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c["content"]) <= 60  # allow some flex


def test_recursive_single_chunk():
    text = "Short text."
    chunks = chunk_recursive(text, separators=["\n\n"], chunk_size=500)
    assert len(chunks) == 1
    assert chunks[0]["content"] == "Short text."
