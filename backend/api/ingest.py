import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile
from services.ingest_pipeline import ingest_source
from services.wiki_store import WikiStore
from models.ingest_models import IngestResult

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
_WIKI_DATA_DIR = Path(os.getenv("WIKI_DATA_DIR", "wiki_data/default"))


def _get_store() -> WikiStore:
    return WikiStore(root=_WIKI_DATA_DIR)


@router.post("/source", response_model=IngestResult)
async def ingest_source_endpoint(file: UploadFile = File(...)):
    ext = Path(file.filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type {ext!r}. Allowed: {', '.join(_ALLOWED_EXTENSIONS)}",
        )

    contents = await file.read()

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)

    named_tmp = tmp_path.parent / file.filename
    try:
        tmp_path.rename(named_tmp)
        store = _get_store()
        result = ingest_source(file_path=named_tmp, store=store)
    finally:
        if named_tmp.exists():
            named_tmp.unlink()

    if result.status == "error":
        raise HTTPException(status_code=500, detail=result.error)

    return result
