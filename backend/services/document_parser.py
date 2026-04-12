import os
from typing import Dict, Any
import PyPDF2
from docx import Document


def parse_txt(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return {"text": text, "char_count": len(text), "page_count": None}


def parse_pdf(path: str) -> Dict[str, Any]:
    text_parts = []
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        page_count = len(reader.pages)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)
    text = "\n".join(text_parts)
    return {"text": text, "char_count": len(text), "page_count": page_count}


def parse_docx(path: str) -> Dict[str, Any]:
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)
    return {"text": text, "char_count": len(text), "page_count": None}


def parse_document(path: str, filename: str) -> Dict[str, Any]:
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".txt":
        return parse_txt(path)
    elif ext == ".pdf":
        return parse_pdf(path)
    elif ext == ".docx":
        return parse_docx(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
