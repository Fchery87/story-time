import re

def load_text_file(path: str) -> list[tuple[str, str]]:
    """
    Loads a .txt or .md file and splits it into chapters.
    Chapters are delimited by lines starting with "Chapter" or "#" or "##".
    """
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()

    chapters = []

    # Regex to find chapter titles. This will be our delimiters.
    delimiters = r'^(Chapter .*|# .*|## .*)$'

    # Find all chapter titles and their positions
    titles = []
    positions = []
    for match in re.finditer(delimiters, text, re.MULTILINE):
        titles.append(match.group(1).strip())
        positions.append(match.start())

    if not titles:
        return [("Chapter 1", text.strip())]

    # Add the text before the first chapter as an introduction
    intro_text = text[:positions[0]].strip()
    if intro_text:
        chapters.append(("Introduction", intro_text))

    # Extract text for each chapter
    for i in range(len(titles)):
        start = positions[i]
        end = positions[i+1] if i + 1 < len(positions) else len(text)

        chapter_text = text[start:end].strip()
        # Remove the title from the chapter text
        chapter_text = chapter_text[len(titles[i]):].strip()

        if chapter_text:
            chapters.append((titles[i], chapter_text))

    return chapters


import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

def load_epub_file(path: str) -> list[tuple[str, str]]:
    """
    Loads an EPUB file and extracts chapters and their text content.
    """
    book = epub.read_epub(path)
    chapters = []

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content()
        soup = BeautifulSoup(content, 'html.parser')

        # Extract title
        title_tag = soup.find('h1') or soup.find('h2') or soup.find('title')
        title = title_tag.get_text().strip() if title_tag else item.get_name()

        # Extract text
        text = ' '.join(p.get_text() for p in soup.find_all('p'))

        if text:
            chapters.append((title, text.strip()))

    return chapters

import pypdf

def load_pdf_file(path: str) -> list[tuple[str, str]]:
    """
    Loads a PDF file, extracts text, and splits it into chapters.
    Chapters are delimited by "Chapter <number>".
    """
    reader = pypdf.PdfReader(path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    chapters = []
    # A simple regex to split by "Chapter <number>"
    chapter_splits = re.split(r'^(Chapter \d+.*)$', full_text, flags=re.MULTILINE)

    if chapter_splits[0].strip():
        chapters.append(("Introduction", chapter_splits[0].strip()))

    for i in range(1, len(chapter_splits), 2):
        title = chapter_splits[i].strip()
        content = chapter_splits[i+1].strip()
        if content:
            chapters.append((title, content))

    return chapters

def load_book(path: str) -> list[tuple[str, str]]:
    """
    Loads a book from a file and dispatches to the correct loader based
    on the file extension.
    """
    ext = path.split('.')[-1].lower()
    if ext in ["txt", "md"]:
        return load_text_file(path)
    elif ext == "epub":
        return load_epub_file(path)
    elif ext == "pdf":
        return load_pdf_file(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
