from pydantic import BaseModel
from typing import Optional


class DocumentMeta(BaseModel):
    id: str
    name: str
    size_bytes: int
    page_count: Optional[int] = None
    upload_date: str
    char_count: int
    source_type: str = "upload"
    source_url: Optional[str] = None
    folder_id: Optional[str] = None


class DocumentDetail(DocumentMeta):
    raw_text: str
