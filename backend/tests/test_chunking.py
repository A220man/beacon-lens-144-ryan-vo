"""Tests for text chunking utilities."""
import pytest
from app.chunking import count_tokens, chunk_text, chunk_document


class TestCountTokens:
    """Tests for token counting."""

    def test_empty_string(self):
        assert count_tokens("") == 1  # Minimum 1 token
    def test_short_text(self):
        # 5 chars // 4 = 1, max(1, 1) = 1
        assert count_tokens("hello") == 1

    def test_longer_text(self):
        # ~4 chars per token
        text = "a" * 100
        assert count_tokens(text) == 25


class TestChunkText:
    """Tests for text chunking."""

    def test_empty_text(self):
        assert chunk_text("") == []

    def test_whitespace_only(self):
        assert chunk_text("   \n\t  ") == []

    def test_single_chunk(self):
        text = "This is a short text."
        chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_multiple_chunks(self):
        text = " ".join(["word"] * 200)  # ~800 chars, ~200 tokens
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) >= 2

    def test_overlap(self):
        text = " ".join(["word"] * 100)  # ~500 chars
        chunks = chunk_text(text, chunk_size=50, chunk_overlap=20)
        assert len(chunks) >= 2
        # Check overlap exists - last words of chunk 0 should appear in chunk 1
        chunk0_words = set(chunks[0].split())
        chunk1_words = set(chunks[1].split())
        overlap_words = chunk0_words & chunk1_words
        assert len(overlap_words) > 0

    def test_sentence_boundary(self):
        # Text with clear sentence boundaries
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        chunks = chunk_text(text, chunk_size=10, chunk_overlap=5)
        # Should produce multiple chunks
        assert len(chunks) >= 2
        # Each chunk should end at a sentence boundary (., !, or ?)
        for chunk in chunks:
            stripped = chunk.strip()
            assert stripped.endswith((".", "!", "?")), f"Chunk does not end at sentence boundary: {repr(chunk)}"
    def test_custom_sizes(self):
        text = "a" * 1000
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
        # 1000 chars / (100*4) = 2.5, but overlap adds more -> at least 3
        assert len(chunks) >= 3

class TestChunkDocument:
    """Tests for document chunking with metadata."""

    def test_empty_content(self):
        result = chunk_document("")
        assert result == []

    def test_single_chunk_metadata(self):
        text = "Short document."
        result = chunk_document(text, chunk_size=500, chunk_overlap=50)
        assert len(result) == 1
        chunk = result[0]
        assert chunk["content"] == text
        assert chunk["chunk_index"] == 0
        assert chunk["token_count"] > 0

    def test_multiple_chunks_metadata(self):
        text = " ".join(["word"] * 200)
        result = chunk_document(text, chunk_size=50, chunk_overlap=10)
        assert len(result) >= 2
        for i, chunk in enumerate(result):
            assert chunk["chunk_index"] == i
            assert chunk["token_count"] > 0
            assert chunk["content"]

    def test_chunk_size_override(self):
        text = "a" * 1000
        result = chunk_document(text, chunk_size=50, chunk_overlap=10)
        # 1000 chars / (50*4) = 5 chunks, overlap adds a couple more
        assert len(result) >= 5
        # All chunks should have token_count roughly around chunk_size
        for chunk in result:
            assert chunk["token_count"] <= 80  # Some variance due to char estimation

