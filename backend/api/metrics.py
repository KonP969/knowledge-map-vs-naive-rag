from fastapi import APIRouter
from services.llm_service import get_session_metrics, reset_session_metrics
from services.vector_store import reset_collection

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics/session")
def session_metrics():
    return get_session_metrics()


@router.delete("/data/reset")
def reset_all():
    reset_collection()
    reset_session_metrics()
    from api.documents import _documents
    from api.chunks import _chunks_store, _parent_store
    from persistence import DOCUMENTS_FILE, CHUNKS_FILE
    _documents.clear()
    _chunks_store.clear()
    _parent_store.clear()
    if DOCUMENTS_FILE.exists():
        DOCUMENTS_FILE.unlink()
    if CHUNKS_FILE.exists():
        CHUNKS_FILE.unlink()
    return {"reset": True}
