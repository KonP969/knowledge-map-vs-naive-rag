import pytest
from datetime import datetime
from services.wiki_store import WikiStore
from services.wiki_log import append_log_entry


@pytest.fixture
def store(tmp_path):
    return WikiStore(root=tmp_path)


def test_append_creates_log_if_missing(store):
    append_log_entry(store, op="ingest", source_id="src_001",
                     details="title=test, +3 entities, +5 claims",
                     timestamp=datetime(2026, 4, 28, 11, 30))
    log = (store.root / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "## [2026-04-28 11:30]" in log
    assert "ingest" in log
    assert "src_001" in log


def test_append_multiple_entries_in_order(store):
    append_log_entry(store, op="ingest", source_id="src_001", details="a",
                     timestamp=datetime(2026, 4, 28, 10, 0))
    append_log_entry(store, op="lint", source_id=None, details="run b",
                     timestamp=datetime(2026, 4, 28, 11, 0))
    log = (store.root / "wiki" / "log.md").read_text(encoding="utf-8")
    a_idx = log.find("[2026-04-28 10:00]")
    b_idx = log.find("[2026-04-28 11:00]")
    assert 0 < a_idx < b_idx


def test_log_format_includes_op_type(store):
    append_log_entry(store, op="query", source_id=None,
                     details="q='kolory sypialni'",
                     timestamp=datetime(2026, 4, 28, 12, 0))
    log = (store.root / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "query" in log
    assert "'kolory sypialni'" in log
