import pytest
from services.document_parser import parse_txt, parse_pdf, parse_docx
import tempfile
import os


def test_parse_txt_basic():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Hello world\nSecond line")
        path = f.name
    try:
        result = parse_txt(path)
        assert result["text"] == "Hello world\nSecond line"
        assert result["char_count"] == len("Hello world\nSecond line")
        assert result["page_count"] is None
    finally:
        os.unlink(path)


def test_parse_txt_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        path = f.name
    try:
        result = parse_txt(path)
        assert result["text"] == ""
        assert result["char_count"] == 0
    finally:
        os.unlink(path)
