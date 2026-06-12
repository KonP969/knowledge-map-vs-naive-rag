from models.ingest_models import (
    SourceClassification, EntityMention, ConceptMention, ClaimExtraction,
)
from models.wiki_models import Span
from services.chunking import chunk_text, merge_classifications


# ── chunk_text ────────────────────────────────────────────────────────────────

def test_chunk_text_short_returns_single_chunk():
    assert chunk_text("short text", max_chars=5000) == ["short text"]


def test_chunk_text_splits_on_paragraph_boundaries_under_limit():
    paras = ["A" * 3000, "B" * 3000, "C" * 3000]
    chunks = chunk_text("\n\n".join(paras), max_chars=5000)
    assert len(chunks) == 3  # no two 3000-char paras fit together under 5000
    assert all(len(c) <= 5000 for c in chunks)


def test_chunk_text_hard_splits_oversized_paragraph_without_losing_content():
    text = "X" * 12000  # single paragraph, no breaks
    chunks = chunk_text(text, max_chars=5000)
    assert all(len(c) <= 5000 for c in chunks)
    assert "".join(chunks) == text


# ── merge_classifications ─────────────────────────────────────────────────────

def _cls(title, ents, concepts, claims, tags=None):
    return SourceClassification(
        title=title, description="d", tags=tags or [], questions=[], key_takeaways=[],
        entity_mentions=[EntityMention(name=n, type="Product", aliases=[], description="x",
                                       span=Span(start=0, end=1, text="x")) for n in ents],
        concept_mentions=[ConceptMention(name=n, definition="x", span=Span(start=0, end=1, text="x"))
                          for n in concepts],
        claims=[ClaimExtraction(text=t, subject_name="s", subject_type="entity",
                                span=Span(start=0, end=1, text="x"), confidence=0.9, polarity="asserts")
                for t in claims],
    )


def test_merge_concatenates_claims_and_dedups_mentions_preserving_order():
    a = _cls("Doc", ["PORTA HIDE", "PORTA OSLO"], ["akustyka"], ["c1", "c2"], tags=["drzwi"])
    b = _cls("Doc2", ["PORTA OSLO", "PORTA VECTOR"], ["kolory"], ["c3"], tags=["drzwi", "porta"])
    merged = merge_classifications([a, b])
    assert merged.title == "Doc"  # first part wins
    assert [e.name for e in merged.entity_mentions] == ["PORTA HIDE", "PORTA OSLO", "PORTA VECTOR"]
    assert [c.name for c in merged.concept_mentions] == ["akustyka", "kolory"]
    assert [c.text for c in merged.claims] == ["c1", "c2", "c3"]
    assert merged.tags == ["drzwi", "porta"]


def test_merge_single_part_returns_it():
    a = _cls("Doc", ["E1"], ["C1"], ["c1"])
    assert merge_classifications([a]) is a


# ── classify_source_chunked (orchestrator) ────────────────────────────────────

def test_classify_chunked_single_call_for_small_text():
    from services.source_classifier import classify_source_chunked
    calls = []

    def fake(t):
        calls.append(t)
        return _cls("D", ["E1"], [], ["c1"])

    out = classify_source_chunked("small text", max_chars=5000, classify_fn=fake)
    assert calls == ["small text"]
    assert [e.name for e in out.entity_mentions] == ["E1"]


def test_classify_chunked_splits_failing_chunk_and_recovers():
    # A dense chunk can blow the model's completion cap (LengthFinishReasonError).
    # The orchestrator must split that chunk and retry instead of failing the document.
    from services.source_classifier import classify_source_chunked
    calls = []

    def fake(t):
        calls.append(len(t))
        if len(t) > 3000:
            raise ValueError("length limit reached")
        return _cls("D", [f"E{len(calls)}"], [], [f"claim-{len(calls)}"])

    text = "A" * 5000  # one 5000-char chunk -> fails -> split into 2x2500 -> both succeed
    out = classify_source_chunked(text, max_chars=5000, classify_fn=fake)
    assert len(out.claims) == 2
    assert any(c > 3000 for c in calls) and sum(1 for c in calls if c <= 3000) == 2


def test_classify_chunked_persistent_failure_still_raises():
    from services.source_classifier import classify_source_chunked

    def always_fail(t):
        raise ValueError("api key invalid")

    try:
        classify_source_chunked("B" * 5000, max_chars=5000, classify_fn=always_fail)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_classify_chunked_merges_multiple_chunks():
    from services.source_classifier import classify_source_chunked

    def fake(t):
        tag = t.strip()[0]  # first char identifies the chunk
        return _cls("D", [f"E-{tag}"], [], [f"claim-{tag}"])

    text = ("A" * 5000) + "\n\n" + ("B" * 5000)
    out = classify_source_chunked(text, max_chars=5000, classify_fn=fake)
    names = [e.name for e in out.entity_mentions]
    assert "E-A" in names and "E-B" in names
    assert len(out.claims) == 2
