import json
import pytest
from datetime import datetime
from services.wiki_store import WikiStore
from services.wiki_index import regenerate_index
from services.wiki_log import append_log_entry
from models.wiki_models import Source, Entity, Concept, Claim, Edge, Span


def test_full_round_trip_writes_reads_indexes_and_logs(tmp_path):
    store = WikiStore(root=tmp_path)

    src = Source(
        id="src_001", title="Sypialnia skandynawska", type="article",
        raw_path="raw/sypialnia/parsed.md",
        ingested_at=datetime(2026, 4, 28, 10, 0, 0),
        summary="Streszczenie sypialni.", key_takeaways=["minimalizm"],
        questions=["jakie kolory?"], tags=["sypialnia"],
    )
    store.write_source(src, slug="sypialnia-skandynawska")

    bedroom = Entity(
        id="e_001", type="Place", aliases=["bedroom"],
        description="Sypialnia.", mentions_count=1,
        questions=["jakie kolory?"], tags=["pomieszczenie"],
    )
    store.write_entity(bedroom, slug="sypialnia")

    bathroom = Entity(
        id="e_002", type="Place", aliases=["bathroom"],
        description="Łazienka.", mentions_count=1,
        questions=["jakie kolory?"], tags=["pomieszczenie"],
    )
    store.write_entity(bathroom, slug="lazienka")

    neutral_colors = Concept(
        id="c_001", definition="Neutralne kolory.",
        examples=["biel", "beż", "szary"], related=[],
        questions=["jakie odcienie?"], tags=["kolory"],
    )
    store.write_concept(neutral_colors, slug="kolory-neutralne")

    span = Span(start=0, end=20, text="excerpt")
    store.append_claim(Claim(
        id="cl_001", text="Sypialnia używa kolorów neutralnych.",
        subject_id="entity:e_001", source_id="src_001",
        span=span, confidence=0.92, polarity="asserts",
    ))
    store.append_claim(Claim(
        id="cl_002", text="Łazienka używa kolorów neutralnych.",
        subject_id="entity:e_002", source_id="src_001",
        span=span, confidence=0.88, polarity="asserts",
    ))

    store.append_edge(Edge(
        id="ed_001", **{"from": "entity:e_001"}, to="concept:c_001",
        relation="associated_with", source_id="src_001",
        span=span, confidence=0.9,
    ))
    store.append_edge(Edge(
        id="ed_002", **{"from": "entity:e_002"}, to="concept:c_001",
        relation="associated_with", source_id="src_001",
        span=span, confidence=0.9,
    ))

    regenerate_index(store)
    append_log_entry(store, op="ingest", source_id="src_001",
                     details="+2 entities, +1 concept, +2 claims, +2 edges",
                     timestamp=datetime(2026, 4, 28, 10, 5))

    # Read back
    assert store.read_source("sypialnia-skandynawska").title == "Sypialnia skandynawska"
    assert store.read_entity("sypialnia", "Place").id == "e_001"
    assert store.read_entity("lazienka", "Place").id == "e_002"
    assert store.read_concept("kolory-neutralne").id == "c_001"
    assert len(store.read_all_claims()) == 2
    assert len(store.read_all_edges()) == 2

    idx = json.loads((tmp_path / "wiki" / "00-Index" / "index.json").read_text(encoding="utf-8"))
    assert len(idx["sources"]) == 1
    assert len(idx["entities"]) == 2
    assert len(idx["concepts"]) == 1

    log = (tmp_path / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "src_001" in log
    assert "ingest" in log

    # Verify cross-document synthesis is structurally enabled:
    # both bedroom and bathroom edges point to neutral_colors concept.
    edges = store.read_all_edges()
    targets_to_concept = [e for e in edges if e.to == "concept:c_001"]
    sources_of_those = {e.from_ for e in targets_to_concept}
    assert sources_of_those == {"entity:e_001", "entity:e_002"}
