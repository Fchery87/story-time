import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from audiobooker.utils.book_loader import load_book


class FakePage:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self):
        return self._text


class FakePdfReader:
    def __init__(self, path):
        text = (
            "Introduction content.\n"
            "More intro.\n"
            "Chapter 1 Getting Started\n"
            "Content for chapter one.\n"
            "Chapter 2 Advanced Topics\n"
            "Content for chapter two.\n"
        )
        self.pages = [FakePage(text)]


def test_load_pdf_file_with_mock():
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_pdf:
        with patch("audiobooker.utils.book_loader.pypdf.PdfReader", new=FakePdfReader):
            chapters = load_book(tmp_pdf.name)

    # Expect 3 chapters: Introduction, Chapter 1..., Chapter 2...
    assert len(chapters) >= 3
    titles = [t for t, _ in chapters]
    assert "Introduction" in titles
    assert any(t.startswith("Chapter 1") for t in titles)
    assert any(t.startswith("Chapter 2") for t in titles)