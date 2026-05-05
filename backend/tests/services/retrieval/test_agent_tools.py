import json
import pytest
from datetime import datetime
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from models.wiki_models import Source, Entity, Concept, Claim, Edge, Span


@pytest.fixture
def store(tmp_path):
    s = WikiStore(root=tmp_path)
    src = Source(
        id="src_001", title="Scandinavian Bedroom", type="txt",
        raw_path="raw/x/parsed.md", ingested_at=datetime(2026, 4, 1),
        summary="Article about Scandinavian bedroom design with neutral tones.",
        key_takeaways=["Neutral palette."],
        questions=["What colors are typical in Scandinavian bedrooms?"],
        tags=["bedroom", "scandinavian"],
    )
    s.write_source(src, slug="scandinavian-bedroom")
    entity = Entity(
        id="e_001", type="Place", aliases=["bedroom", "sypialnia"],
        description="A Scandinavian bedroom.", mentions_count=1,
        questions=["What materials are used?"], tags=["bedroom"],
    )
    s.write_entity(entity, slug="sypialnia")
    concept = Concept(
        id="c_001", definition="Whites, beiges, grays.",
        examples=["white walls"], related=[],
        questions=["What is a neutral palette?"], tags=["color"],
    )
    s.write_concept(concept, slug="neutral-palette")
    claim = Claim(
        id="cl_001", text="Bedroom uses neutral colors.",
        subject_id="entity:e_001", source_id="src_001",
        span=Span(start=0, end=30, text="Bedroom uses neutral colors."),
        confidence=0.9, polarity="asserts",
    )
    s.append_claim(claim)
    edge = Edge(
        id="edge_001", **{"from": "entity:e_001"},
        to="concept:c_001", relation="associated_with",
        source_id="src_001",
        span=Span(start=0, end=10, text="bedroom"),
        confidence=0.8,
    )
    s.append_edge(edge)
    # Write a raw parsed file so search_text can find content
    raw_dir = tmp_path / "raw" / "scandinavian-bedroom"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / "parsed.md").write_text("Bedroom uses neutral tones including white and beige.", encoding="utf-8")
    regenerate_index(s)
    return s


# ── read_index ────────────────────────────────────────────────────────────────

def test_read_index_returns_json_string(store):
    from services.retrieval.agent_tools import read_index
    result = read_index(store)
    data = json.loads(result)
    assert "sources" in data
    assert "entities" in data
    assert "concepts" in data


def test_read_index_empty_store(tmp_path):
    from services.retrieval.agent_tools import read_index
    empty = WikiStore(root=tmp_path)
    result = read_index(empty)
    data = json.loads(result)
    assert data["sources"] == []


# ── search_entities ───────────────────────────────────────────────────────────

def test_search_entities_finds_by_alias(store):
    from services.retrieval.agent_tools import search_entities
    result = json.loads(search_entities(store, q="sypialnia"))
    assert len(result) >= 1
    assert result[0]["id"] == "e_001"


def test_search_entities_filters_by_type(store):
    from services.retrieval.agent_tools import search_entities
    result = json.loads(search_entities(store, q="sypialnia", type="Person"))
    assert result == []


def test_search_entities_no_match_returns_empty(store):
    from services.retrieval.agent_tools import search_entities
    result = json.loads(search_entities(store, q="xyznonexistent"))
    assert result == []


# ── search_concepts ───────────────────────────────────────────────────────────

def test_search_concepts_finds_by_slug(store):
    from services.retrieval.agent_tools import search_concepts
    result = json.loads(search_concepts(store, q="neutral"))
    assert len(result) >= 1


def test_search_concepts_no_match(store):
    from services.retrieval.agent_tools import search_concepts
    result = json.loads(search_concepts(store, q="xyz_never"))
    assert result == []


# ── search_wiki_content ───────────────────────────────────────────────────────

def test_search_wiki_content_finds_text(store):
    from services.retrieval.agent_tools import search_wiki_content
    result = json.loads(search_wiki_content(store, q="neutral"))
    assert len(result) >= 1
    assert "file" in result[0]
    assert "excerpt" in result[0]


def test_search_wiki_content_no_match(store):
    from services.retrieval.agent_tools import search_wiki_content
    result = json.loads(search_wiki_content(store, q="zzznomatch"))
    assert result == []


# ── search_text ───────────────────────────────────────────────────────────────

def test_search_text_finds_in_raw(store):
    from services.retrieval.agent_tools import search_text
    result = json.loads(search_text(store, q="beige"))
    assert len(result) >= 1
    assert "file" in result[0]


def test_search_text_no_match(store):
    from services.retrieval.agent_tools import search_text
    result = json.loads(search_text(store, q="nevermatches_xyz"))
    assert result == []


# ── get_node ──────────────────────────────────────────────────────────────────

def test_get_node_source(store):
    from services.retrieval.agent_tools import get_node
    result = json.loads(get_node(store, id="source:src_001"))
    assert result["id"] == "src_001"
    assert "summary" in result


def test_get_node_entity(store):
    from services.retrieval.agent_tools import get_node
    result = json.loads(get_node(store, id="entity:e_001"))
    assert result["id"] == "e_001"
    assert "description" in result


def test_get_node_concept(store):
    from services.retrieval.agent_tools import get_node
    result = json.loads(get_node(store, id="concept:c_001"))
    assert result["id"] == "c_001"
    assert "definition" in result


def test_get_node_unknown_returns_error(store):
    from services.retrieval.agent_tools import get_node
    result = json.loads(get_node(store, id="entity:nonexistent"))
    assert "error" in result


# ── get_claims ────────────────────────────────────────────────────────────────

def test_get_claims_all(store):
    from services.retrieval.agent_tools import get_claims
    result = json.loads(get_claims(store))
    assert len(result) == 1
    assert result[0]["id"] == "cl_001"


def test_get_claims_by_node_id(store):
    from services.retrieval.agent_tools import get_claims
    result = json.loads(get_claims(store, node_id="entity:e_001"))
    assert len(result) == 1


def test_get_claims_by_query(store):
    from services.retrieval.agent_tools import get_claims
    result = json.loads(get_claims(store, query="neutral"))
    assert len(result) == 1


def test_get_claims_by_polarity(store):
    from services.retrieval.agent_tools import get_claims
    result = json.loads(get_claims(store, polarity="denies"))
    assert result == []


# ── get_relations ─────────────────────────────────────────────────────────────

def test_get_relations_returns_edge(store):
    from services.retrieval.agent_tools import get_relations
    result = json.loads(get_relations(store, node_id="entity:e_001"))
    assert len(result) == 1
    assert result[0]["relation"] == "associated_with"


def test_get_relations_direction_out(store):
    from services.retrieval.agent_tools import get_relations
    result = json.loads(get_relations(store, node_id="entity:e_001", direction="out"))
    assert len(result) == 1


def test_get_relations_direction_in(store):
    from services.retrieval.agent_tools import get_relations
    result = json.loads(get_relations(store, node_id="entity:e_001", direction="in"))
    assert result == []


def test_get_relations_type_filter(store):
    from services.retrieval.agent_tools import get_relations
    result = json.loads(get_relations(store, node_id="entity:e_001", type="contradicts"))
    assert result == []


# ── read_source ───────────────────────────────────────────────────────────────

def test_read_source_returns_content(store):
    from services.retrieval.agent_tools import read_source
    result = json.loads(read_source(store, source_id="src_001"))
    assert result["id"] == "src_001"
    assert "content" in result


def test_read_source_unknown_id(store):
    from services.retrieval.agent_tools import read_source
    result = json.loads(read_source(store, source_id="src_999"))
    assert "error" in result


# ── query_log ─────────────────────────────────────────────────────────────────

def test_query_log_empty_log(store):
    from services.retrieval.agent_tools import query_log
    result = json.loads(query_log(store, filter="ingest"))
    assert isinstance(result, list)


def test_query_log_finds_entry(store):
    from services.retrieval.agent_tools import query_log
    from services.wiki_log import append_log_entry
    append_log_entry(store, op="ingest", source_id="src_001", details="test entry")
    result = json.loads(query_log(store, filter="ingest"))
    assert len(result) >= 1
