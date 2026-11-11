import json
import pytest
from pathlib import Path
from services.parser import parse_source


@pytest.fixture
def txt_file(tmp_path):
    p = tmp_path / "article.txt"
    p.write_text(
        "Scandinavian bedroom design relies on neutral colors.\n"
        "Wood is the dominant material — oak or pine.\n"
        "Textiles are natural: linen, cotton, wool.",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def pdf_file(tmp_path):
    """Create a minimal PDF using pypdf internals — no dependency on external tools."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    out = tmp_path / "article.pdf"
    with out.open("wb") as f:
        writer.write(f)
    return out


def test_parse_txt_writes_parsed_md(txt_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    result = parse_source(txt_file, store_root=store_root)
    parsed_md = store_root / "raw" / result["slug"] / "parsed.md"
    assert parsed_md.exists()
    content = parsed_md.read_text(encoding="utf-8")
    assert "Scandinavian" in content


def test_parse_txt_writes_manifest_json(txt_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    result = parse_source(txt_file, store_root=store_root)
    manifest_path = store_root / "raw" / result["slug"] / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "char_count" in manifest
    assert manifest["char_count"] > 0
    assert "language" in manifest
    assert "sections" in manifest


def test_parse_txt_returns_slug_and_text(txt_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    result = parse_source(txt_file, store_root=store_root)
    assert "slug" in result
    assert "text" in result
    assert len(result["text"]) > 0


def test_parse_txt_slug_is_deterministic(txt_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    r1 = parse_source(txt_file, store_root=store_root)
    # Second call on same file should produce the same slug
    store_root2 = tmp_path / "wiki_root2"
    r2 = parse_source(txt_file, store_root=store_root2)
    assert r1["slug"] == r2["slug"]


def test_parse_unsupported_extension_raises(tmp_path):
    bad = tmp_path / "file.odt"
    bad.write_bytes(b"data")
    with pytest.raises(ValueError, match="Unsupported"):
        parse_source(bad, store_root=tmp_path / "root")


def test_parse_pdf_produces_output(pdf_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    # blank PDF — text may be empty but files must be written
    result = parse_source(pdf_file, store_root=store_root)
    parsed_md = store_root / "raw" / result["slug"] / "parsed.md"
    manifest_path = store_root / "raw" / result["slug"] / "manifest.json"
    assert parsed_md.exists()
    assert manifest_path.exists()


def test_manifest_contains_char_count(txt_file, tmp_path):
    store_root = tmp_path / "wiki_root"
    result = parse_source(txt_file, store_root=store_root)
    manifest_path = store_root / "raw" / result["slug"] / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["char_count"] == len(result["text"])


def test_parse_md_is_treated_as_text(tmp_path):
    p = tmp_path / "notes.md"
    p.write_text("# Heading\n\nA markdown paragraph about oak and pine.", encoding="utf-8")
    result = parse_source(p, store_root=tmp_path / "wiki_root")
    assert "markdown paragraph" in result["text"]
