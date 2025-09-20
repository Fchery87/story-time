import os
import tempfile

from ebooklib import epub

from audiobooker.utils.book_loader import load_book


def _create_epub(tmp_path: str) -> str:
    book = epub.EpubBook()
    book.set_identifier("id123456")
    book.set_title("Sample EPUB")
    book.set_language("en")

    c1 = epub.EpubHtml(title="Chapter 1", file_name="chap_01.xhtml", lang="en")
    c1.set_content("<h1>Chapter 1</h1><p>Hello world.</p>")

    book.add_item(c1)

    book.spine = ["nav", c1]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub_path = os.path.join(tmp_path, "sample.epub")
    epub.write_epub(epub_path, book)
    return epub_path


def test_load_epub_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        epub_path = _create_epub(tmpdir)
        chapters = load_book(epub_path)
        assert len(chapters) >= 1
        titles = [t for t, _ in chapters]
        assert any("Chapter 1" in t for t in titles)
        assert any("Hello world" in text for _, text in chapters)