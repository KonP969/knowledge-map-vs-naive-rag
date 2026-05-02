import json
import pytest
from pathlib import Path
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from models.wiki_models import Source, Entity, Concept
from models.retrieval_models import ParsedIntent
from datetime import datetime


@pytest.fixture
def store(tmp_path):
    s = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="Scandinavian Bedroom Design",
        type="txt", raw_path="raw/scandinavian-bedroom/parsed.md",
        ingested_at=datetime(2026, 4, 1),
        summary="Article about Scandinavian bedroom design.",
        key_takeaways=["Neutral palette."],
        questions=["What colors are typical in Scandinavian bedrooms?"],
        tags=["bedroom", "scandinavian", "design"],
    )
    s.write_source(src, slug="scandinavian-bedroom")

    entity = Entity(
        id="e_001", type="Place", aliases=["bedroom"],
        description="A Scandinavian bedroom.",
        mentions_count=1,
        questions=["What materials are used in Scandinavian bedrooms?"],
        tags=["bedroom", "place"],
    )
    s.write_entity(entity, slug="sypialnia")

    concept = Concept(
        id="c_001", definition="A color scheme using whites, beiges, and grays.",
        examples=["white walls"], related=[],
        questions=["What is a neutral palette?"],
        tags=["color", "design"],
    )
    s.write_concept(concept, slug="neutral-palette")

    regenerate_index(s)
    return s


@pytest.fixture
def fact_lookup_intent():
    return ParsedIntent(
        original_question="What colors are used in Scandinavian bedrooms?",
        entity_mentions=["sypialnia"],
        concept_mentions=["neutral palette"],
        intent_type="fact_lookup",
        expected_answer_form="short",
    )


@pytest.fixture
def empty_intent():
    return ParsedIntent(
        original_question="Unrelated question about aviation history.",
        entity_mentions=[],
        concept_mentions=[],
        intent_type="fact_lookup",
        expected_answer_form="short",
    )


def test_filter_candidates_returns_list(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    assert isinstance(result, list)


def test_filter_candidates_entity_match_scores_highest(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    entity_cands = [c for c in result if c.artifact_type == "entity"]
    assert len(entity_cands) >= 1
    assert entity_cands[0].score_breakdown.get("entity_match", 0) == 3


def test_filter_candidates_concept_match_scores(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    concept_cands = [c for c in result if c.artifact_type == "concept"]
    assert len(concept_cands) >= 1
    assert concept_cands[0].score_breakdown.get("concept_match", 0) == 2


def test_filter_candidates_question_overlap_scores(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    source_cands = [c for c in result if c.artifact_type == "source"]
    assert len(source_cands) >= 1
    assert source_cands[0].score_breakdown.get("question_overlap", 0) > 0


def test_filter_candidates_sorted_by_score(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    scores = [c.score for c in result]
    assert scores == sorted(scores, reverse=True)


def test_filter_candidates_empty_intent_no_entity_match(store, empty_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(empty_intent, store)
    entity_cands = [c for c in result if c.artifact_type == "entity" and c.score_breakdown.get("entity_match", 0) > 0]
    assert len(entity_cands) == 0


def test_filter_candidates_no_index_returns_empty(tmp_path):
    from services.retrieval.candidate_filter import filter_candidates
    empty_store = WikiStore(root=tmp_path)
    intent = ParsedIntent(
        original_question="Q", entity_mentions=[], concept_mentions=[],
        intent_type="fact_lookup", expected_answer_form="short",
    )
    result = filter_candidates(intent, empty_store)
    assert result == []


def test_filter_candidates_respects_top_n(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store, top_n=1)
    assert len(result) <= 1


def test_filter_candidates_artifact_id_format(store, fact_lookup_intent):
    from services.retrieval.candidate_filter import filter_candidates
    result = filter_candidates(fact_lookup_intent, store)
    for c in result:
        assert c.artifact_id.startswith(c.artifact_type + ":")
