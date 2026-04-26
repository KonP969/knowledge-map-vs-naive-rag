from pydantic import BaseModel


class Folder(BaseModel):
    id: str
    name: str
    created_at: str


class FolderCreate(BaseModel):
    name: str


class FolderRename(BaseModel):
    name: str
