import os
import uuid
import tempfile
from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, UploadFile, File, HTTPException
from models.document import DocumentMeta, DocumentDetail
from services.document_parser import parse_document

router = APIRouter(prefix="/api/documents", tags=["documents"])

# In-memory store: id -> {meta: DocumentMeta, text: str}
_documents: Dict[str, Dict] = {}


@router.post("/upload", response_model=DocumentMeta)
async def upload_document(file: UploadFile = File(...)):
    allowed = {".pdf", ".docx", ".txt"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(allowed)}")

    contents = await file.read()
    size_bytes = len(contents)

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        parsed = parse_document(tmp_path, file.filename)
    finally:
        os.unlink(tmp_path)

    doc_id = str(uuid.uuid4())
    meta = DocumentMeta(
        id=doc_id,
        name=file.filename,
        size_bytes=size_bytes,
        page_count=parsed.get("page_count"),
        upload_date=datetime.utcnow().isoformat(),
        char_count=parsed["char_count"],
    )
    _documents[doc_id] = {"meta": meta, "text": parsed["text"]}
    return meta


@router.get("/", response_model=List[DocumentMeta])
def list_documents():
    return [v["meta"] for v in _documents.values()]


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: str):
    if doc_id not in _documents:
        raise HTTPException(404, "Document not found")
    entry = _documents[doc_id]
    return DocumentDetail(**entry["meta"].model_dump(), raw_text=entry["text"])


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    if doc_id not in _documents:
        raise HTTPException(404, "Document not found")
    del _documents[doc_id]
    return {"deleted": doc_id}


def get_document_text(doc_id: str) -> str:
    """Helper for other services to fetch raw document text."""
    if doc_id not in _documents:
        raise HTTPException(404, "Document not found")
    return _documents[doc_id]["text"]
