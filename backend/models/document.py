from pydantic import BaseModel
from typing import Optional


class DocumentMeta(BaseModel):
    id: str
    name: str
    size_bytes: int
    page_count: Optional[int] = None
    upload_date: str
    char_count: int


class DocumentDetail(DocumentMeta):
    raw_text: str
