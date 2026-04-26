import uuid
from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from models.folder import Folder, FolderCreate, FolderRename
from persistence import save_json, load_json, FOLDERS_FILE

router = APIRouter(prefix="/api/folders", tags=["folders"])

_folders: Dict[str, Folder] = {}


def _persist() -> None:
    save_json(FOLDERS_FILE, {fid: f.model_dump() for fid, f in _folders.items()})


def load_folders() -> None:
    data = load_json(FOLDERS_FILE)
    for fid, entry in data.items():
        _folders[fid] = Folder(**entry)


@router.get("/", response_model=List[Folder])
def list_folders():
    return list(_folders.values())


@router.post("/", response_model=Folder)
def create_folder(body: FolderCreate):
    fid = str(uuid.uuid4())
    folder = Folder(id=fid, name=body.name, created_at=datetime.utcnow().isoformat())
    _folders[fid] = folder
    _persist()
    return folder


@router.delete("/{folder_id}")
def delete_folder(folder_id: str):
    if folder_id not in _folders:
        raise HTTPException(404, "Folder not found")
    from api.documents import _documents
    if any(entry["meta"].folder_id == folder_id for entry in _documents.values()):
        raise HTTPException(400, "Folder is not empty")
    del _folders[folder_id]
    _persist()
    return {"deleted": folder_id}


@router.patch("/{folder_id}", response_model=Folder)
def rename_folder(folder_id: str, body: FolderRename):
    if folder_id not in _folders:
        raise HTTPException(404, "Folder not found")
    f = _folders[folder_id]
    _folders[folder_id] = Folder(id=f.id, name=body.name, created_at=f.created_at)
    _persist()
    return _folders[folder_id]
