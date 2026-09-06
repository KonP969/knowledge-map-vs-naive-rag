import json
from pathlib import Path
from typing import Any, Dict

import PyPDF2
from docx import Document

from services._slug import slugify


def parse_source(file_path: Path, store_root: Path) -> Dict[str, Any]:
    """
    Stage 1 (deterministic). Reads the raw file, extracts text, writes:
      <store_root>/raw/<slug>/parsed.md
      <store_root>/raw/<slug>/manifest.json
    Returns {"slug": str, "text": str, "raw_dir": Path}.
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    if ext in (".txt", ".md"):
        text = _parse_txt(file_path)
    elif ext == ".pdf":
        text = _parse_pdf(file_path)
    elif ext == ".docx":
        text = _parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext!r}. Allowed: .txt, .md, .pdf, .docx")

    slug = slugify(file_path.stem)
    raw_dir = Path(store_root) / "raw" / slug
    raw_dir.mkdir(parents=True, exist_ok=True)

    parsed_md = raw_dir / "parsed.md"
    _atomic_write(parsed_md, text)

    sections = _detect_sections(text)
    language = _detect_language(text)
    manifest = {
        "slug": slug,
        "original_filename": file_path.name,
        "char_count": len(text),
        "language": language,
        "sections": sections,
    }
    manifest_path = raw_dir / "manifest.json"
    _atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))

    return {"slug": slug, "text": text, "raw_dir": raw_dir}


def _parse_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_pdf(path: Path) -> str:
    parts = []
    with path.open("rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                parts.append(extracted)
    return "\n".join(parts)


def _parse_docx(path: Path) -> str:
    """Extract body paragraph text only. Table cells, headers, and text frames are not included."""
    doc = Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _detect_sections(text: str) -> list:
    """Return list of detected section headings (lines starting with # or all-caps short lines)."""
    sections = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            sections.append(stripped.lstrip("#").strip())
        elif stripped.isupper() and 3 <= len(stripped) <= 60:
            sections.append(stripped)
    return sections


def _detect_language(text: str) -> str:
    """Heuristic: if text contains common Polish function words → 'pl', else 'en'."""
    polish_markers = {"jest", "są", "tego", "się", "przez", "oraz", "jako"}
    words = set(text.lower().split())
    if polish_markers & words:
        return "pl"
    return "en"


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.parent / (path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
