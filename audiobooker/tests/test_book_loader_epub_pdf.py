import os
import tempfile
import unittest

from ebooklib import epub

from audiobooker.utils.book_loader import load_book


def _make_epub_tmpfile() -> str:
    book = epub.EpubBook()
    book.set_identifier("id123456")
    book.set_title("Sample EPUB")
    book.set_language("en")
    book.add_author("Test Author")

    c1 = epub.EpubHtml(title="Chapter 1", file_name="chap_01.xhtml", lang="en")
    c1.content = "<h1>Chapter 1</h1><p>This is the first chapter.</p>"

    c2 = epub.EpubHtml(title="Chapter 2", file_name="chap_02.xhtml", lang="en")
    c2.content = "<h1>Chapter 2</h1><p>This is the second chapter.</p>"

    book.add_item(c1)
    book.add_item(c2)
    book.toc = (epub.Link("chap_01.xhtml", "Chapter 1", "chap_01"), epub.Link("chap_02.xhtml", "Chapter 2", "chap_02"))
    book.spine = ["nav", c1, c2]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".epub")
    epub.write_epub(tmp.name, book)
    return tmp.name


class TestBookLoadersComplex(unittest.TestCase):
    def test_load_epub(self):
        epub_path = _make_epub_tmpfile()
        try:
            chapters = load_book(epub_path)
            self.assertTrue(len(chapters) >= 2)
            self.assertTrue(all(isinstance(t, str) and isinstance(c, str) for t, c in chapters))
        finally:
            if os.path.exists(epub_path):
                os.remove(epub_path)


if __name__ == "__main__":
    unittest.main()