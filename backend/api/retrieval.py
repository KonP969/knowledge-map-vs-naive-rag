import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.wiki_store import WikiStore
from services.retrieval.retrieval_pipeline import run_retrieval
from models.retrieval_models import QueryTrace

router = APIRouter(prefix="/api/retrieval", tags=["retrieval"])

_WIKI_DATA_DIR = Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default"))


def _get_store() -> WikiStore:
    return WikiStore(root=_WIKI_DATA_DIR)


class QueryRequest(BaseModel):
    question: str


@router.post("/query", response_model=QueryTrace)
def query_wiki(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    try:
        store = _get_store()
        return run_retrieval(request.question.strip(), store)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
