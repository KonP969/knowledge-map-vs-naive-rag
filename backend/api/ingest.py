import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile
from services._slug import slugify
from services.ingest_pipeline import ingest_source
from services.wiki_store import WikiStore
from models.ingest_models import IngestResult

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
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

    # The filename drives the source slug and is recorded in raw/<slug>/manifest.json,
    # so keep the user's name (a UUID temp name gave slugs like '6a0f70fa…'). A private
    # temp dir per request keeps concurrent uploads of the same name apart.
    filename = Path(file.filename).name
    try:
        slugify(Path(filename).stem)
    except ValueError:
        filename = f"upload{ext}"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / filename
        tmp_path.write_bytes(contents)
        result = ingest_source(file_path=tmp_path, store=_get_store())

    if result.status == "error":
        raise HTTPException(status_code=500, detail=result.error)

    return result
