import os
import shutil
from pathlib import Path

from fastapi import APIRouter
from services.llm_service import get_session_metrics, reset_session_metrics
from services.wiki_store import WikiStore

router = APIRouter(prefix="/api", tags=["metrics"])

_WIKI_DATA_DIR = Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default"))


@router.get("/metrics/session")
def session_metrics():
    return get_session_metrics()


@router.delete("/data/reset")
def reset_all():
    reset_session_metrics()

    root = _WIKI_DATA_DIR
    # Remove all wiki content directories
    for subdir in ["wiki", "raw"]:
        target = root / subdir
        if target.exists():
            shutil.rmtree(target)

    # Re-initialise empty store (recreates required directory structure)
    WikiStore(root=root)

    return {"reset": True}
