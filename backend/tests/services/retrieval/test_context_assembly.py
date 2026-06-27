import pytest
from datetime import datetime
from services.wiki_store import WikiStore
from models.wiki_models import Source, Entity, Claim, Edge, Span
from models.retrieval_models import Candidate, Selection, SelectedArtifact


@pytest.fixture
def store(tmp_path):
    s = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="Scandinavian Bedroom", type="txt",
        raw_path="raw/x/parsed.md", ingested_at=datetime(2026, 4, 1),
        summary="Article about Scandinavian bedroom design.",
        key_takeaways=["Neutral palette."], questions=["What colors?"], tags=["bedroom"],
    )
    s.write_source(src, slug="scandinavian-bedroom")

    entity = Entity(
        id="e_001", type="Place", aliases=["bedroom"],
        description="A Scandinavian bedroom.", mentions_count=1,
        questions=["What materials?"], tags=["bedroom"],
    )
    s.write_entity(entity, slug="sypialnia")

    claim = Claim(
        id="cl_001", text="Bedroom uses neutral colors.",
        subject_id="entity:e_001", source_id="src_001",
        span=Span(start=0, end=30, text="Bedroom uses neutral colors."),
        confidence=0.9, polarity="asserts",
    )
    s.append_claim(claim)

    edge = Edge(
        id="ed_001", **{"from": "source:src_001"},
        to="entity:e_001", relation="mentions",
        source_id="src_001",
        span=Span(start=0, end=5, text="Scand"),
        confidence=1.0,
    )
    s.append_edge(edge)
    return s


@pytest.fixture
def selection_with_source():
    return Selection(
        selected=[
            SelectedArtifact(
                artifact_id="source:src_001",
                relevance_score=0.9,
                reasoning="Primary source.",
            )
        ],
        confidence=0.85,
        reasoning="Best match.",
    )


@pytest.fixture
def candidates():
    return [
        Candidate(
            artifact_id="source:src_001",
            artifact_type="source",
            slug="scandinavian-bedroom",
            title="Scandinavian Bedroom",
            score=7,
            score_breakdown={"question_overlap": 2},
            questions=["What colors?"],
            tags=["bedroom"],
            description_preview="Article about Scandinavian bedroom design.",
        )
    ]


def test_assemble_context_returns_string_and_int(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, char_count = assemble_context("What colors?", selection_with_source, candidates, store)
    assert isinstance(context, str)
    assert isinstance(char_count, int)
    assert char_count == len(context)


def test_assemble_context_contains_artifact_id(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, _ = assemble_context("What colors?", selection_with_source, candidates, store)
    assert "source:src_001" in context


def test_assemble_context_contains_claim(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, _ = assemble_context("What colors?", selection_with_source, candidates, store)
    assert "cl_001" in context
    assert "neutral colors" in context


def test_assemble_context_contains_edge(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, _ = assemble_context("What colors?", selection_with_source, candidates, store)
    assert "mentions" in context


def test_assemble_context_contains_question(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, _ = assemble_context("What colors?", selection_with_source, candidates, store)
    assert "What colors?" in context


def test_assemble_context_empty_selection_returns_header_only(store, candidates):
    from services.retrieval.context_assembly import assemble_context
    empty_selection = Selection(selected=[], confidence=0.0, reasoning="No match.")
    context, char_count = assemble_context("Q", empty_selection, candidates, store)
    assert "Q" in context
    assert char_count > 0


def test_assemble_context_char_count_matches_len(store, selection_with_source, candidates):
    from services.retrieval.context_assembly import assemble_context
    context, char_count = assemble_context("Q", selection_with_source, candidates, store)
    assert char_count == len(context)


def test_assemble_context_leads_with_semantic_claim_ids(store):
    from services.retrieval.context_assembly import assemble_context
    cand = Candidate(
        artifact_id="entity:e_001", artifact_type="entity", slug="sypialnia",
        title="Place: sypialnia", score=10, score_breakdown={"semantic": 10},
        questions=[], tags=[], description_preview="A Scandinavian bedroom.",
        claim_ids=["cl_001"],
    )
    sel = Selection(
        selected=[SelectedArtifact(artifact_id="entity:e_001", relevance_score=0.9, reasoning="x")],
        confidence=0.9, reasoning="x",
    )
    context, _ = assemble_context("colors?", sel, [cand], store)
    assert "cl_001" in context and "neutral colors" in context
    # the verbatim claim leads; the generic node description is demoted below it
    assert context.index("neutral colors") < context.index("A Scandinavian bedroom")
