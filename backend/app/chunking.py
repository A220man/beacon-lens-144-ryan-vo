
"""Text chunking utilities for RAG pipeline."""
import re
from typing import List


def count_tokens(text: str) -> int:
    """Rough token count estimation (1 token ~ 4 chars for English)."""
    return max(1, len(text) // 4)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Input text to chunk
        chunk_size: Target token count per chunk
        chunk_overlap: Token overlap between chunks

    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []

    # Convert token sizes to character approximations
    char_size = chunk_size * 4
    char_overlap = chunk_overlap * 4

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + char_size, text_len)

        # Try to break at sentence boundary
        if end < text_len:
            # Look for sentence ending within the last 20% of the chunk
            search_start = max(start, end - char_size // 5)
            sentence_end = -1
            for m in re.finditer(r"[.!?]\s+", text[search_start:end]):
                sentence_end = m.end() + search_start
            if sentence_end > start:
                end = sentence_end

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        start = end - char_overlap
        if start < 0:
            start = 0

    return chunks


def chunk_document(
    content: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> List[dict]:
    """
    Chunk a document and return chunks with metadata.

    Returns:
        List of dicts with keys: content, chunk_index, token_count
    """
    chunks = chunk_text(content, chunk_size, chunk_overlap)
    return [
        {
            "content": chunk,
            "chunk_index": i,
            "token_count": count_tokens(chunk),
        }
        for i, chunk in enumerate(chunks)
    ]
