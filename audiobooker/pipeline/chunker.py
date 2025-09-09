import re
import nltk

def sent_tokenize_fallback(text: str) -> list[str]:
    """A simple regex-based sentence tokenizer."""
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    return [s.strip() for s in sentences if s.strip()]

def chunk(text: str, max_chars: int = 1200) -> list[str]:
    """
    Splits a long text into smaller chunks of a specified maximum size,
    without splitting sentences.
    """
    try:
        # Ensure the punkt tokenizer is available
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')
        sentences = nltk.sent_tokenize(text)
    except Exception:
        # Fallback if nltk fails for any reason
        sentences = sent_tokenize_fallback(text)

    if not sentences:
        return []

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # If a sentence itself is longer than max_chars, it becomes its own chunk
        if len(sentence) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            chunks.append(sentence)
            current_chunk = ""
            continue

        # If adding the new sentence exceeds the limit, finalize the current chunk
        if len(current_chunk) + len(sentence) + 1 > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence

    # Add the last remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks
