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


# ── context the answer model can actually use (source titles, whole node) ─────

def _entity_selection():
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
    return sel, [cand]


def _add_claims(store, n, start=2):
    for i in range(start, start + n):
        store.append_claim(Claim(
            id=f"cl_{i:03d}", text=f"Bedroom fact number {i}.",
            subject_id="entity:e_001", source_id="src_001",
            span=Span(start=0, end=5, text="x"), confidence=0.8, polarity="asserts",
        ))


def test_claim_line_names_its_source_article(store):
    from services.retrieval.context_assembly import assemble_context
    sel, cands = _entity_selection()
    context, _ = assemble_context("colors?", sel, cands, store)
    claim_line = next(l for l in context.splitlines() if "cl_001" in l)
    assert "Scandinavian Bedroom" in claim_line


def test_node_claims_beyond_semantic_hits_are_included(store):
    from services.retrieval.context_assembly import assemble_context
    _add_claims(store, 3)
    sel, cands = _entity_selection()
    context, _ = assemble_context("colors?", sel, cands, store)
    assert "cl_001" in context and "cl_004" in context
    assert context.index("cl_001") < context.index("cl_002")  # semantic hit still leads


def test_claim_cap_is_configurable_for_list_questions(store):
    from services.retrieval.context_assembly import assemble_context
    _add_claims(store, 15)
    sel, cands = _entity_selection()
    short, _ = assemble_context("colors?", sel, cands, store)
    wide, _ = assemble_context("colors?", sel, cands, store, max_claims=25)
    assert "cl_016" not in short
    assert "cl_016" in wide


def test_relations_show_readable_names_not_only_ids(store):
    from services.retrieval.context_assembly import assemble_context
    sel, cands = _entity_selection()
    context, _ = assemble_context("colors?", sel, cands, store)
    relations = context.split("### Relations:")[1]
    assert "Scandinavian Bedroom" in relations


def test_contradicting_claim_is_pulled_in_with_a_warning(store):
    from services.retrieval.context_assembly import assemble_context
    # cl_050 lives on another node and another source: selection would never see it.
    store.append_claim(Claim(
        id="cl_050", text="Bedroom must avoid neutral colors.",
        subject_id="concept:c_099", source_id="src_002",
        span=Span(start=0, end=5, text="x"), confidence=0.8, polarity="asserts",
    ))
    store.append_edge(Edge(
        id="ed_050", **{"from": "claim:cl_050"}, to="claim:cl_001",
        relation="contradicts", source_id="src_002",
        span=Span(start=0, end=5, text="x"), confidence=1.0,
    ))
    sel, cands = _entity_selection()
    context, _ = assemble_context("colors?", sel, cands, store)
    assert "cl_050" in context and "avoid neutral colors" in context
    warning_line = next(l for l in context.splitlines() if "cl_050" in l)
    assert "CONTRADICT" in warning_line.upper()
    assert "cl_001" in warning_line
