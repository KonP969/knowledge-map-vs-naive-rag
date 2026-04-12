import pytest


@pytest.fixture(autouse=True)
def isolated_chroma(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    import services.vector_store as vs
    vs._client = None
    vs._collection = None
    yield
    vs._client = None
    vs._collection = None
