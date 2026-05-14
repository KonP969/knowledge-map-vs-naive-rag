from fastapi import APIRouter
from services.llm_service import get_session_metrics, reset_session_metrics

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics/session")
def session_metrics():
    return get_session_metrics()


@router.delete("/data/reset")
def reset_all():
    reset_session_metrics()
    return {"reset": True}
