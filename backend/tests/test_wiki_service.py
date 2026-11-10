"""Tests for wiki generation service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.wiki_service import WikiService
from app.models import Document, WikiPage, WikiSection, MapCache


class TestWikiServiceUnit:
    """Unit tests for WikiService methods that don't require database."""

    def test_normalize_content(self):
        """Test content normalization for consistent hashing."""
        service = WikiService(db=None)
        assert service._normalize_content("  Hello   World  ") == "hello world"
        assert service._normalize_content("Hello\n\tWorld") == "hello world"
        assert service._normalize_content("") == ""

    def test_content_hash(self):
        """Test SHA256 hash generation."""
        service = WikiService(db=None)
        hash1 = service._content_hash("Hello World")
        hash2 = service._content_hash("Hello World")
        hash3 = service._content_hash("Different content")
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 64  # SHA256 hex length

    def test_extract_slug(self):
        """Test slug extraction from content."""
        service = WikiService(db=None)
        slug = service._extract_slug("This is a test document. It has multiple sentences.")
        assert slug == "this-is-a-test-document"
        
        slug = service._extract_slug("API Reference Guide for developers")
        assert slug == "api-reference-guide-for-developers"
        
        slug = service._extract_slug("")
        assert slug == "untitled"

    def test_classify_content(self):
        """Test content classification."""
        service = WikiService(db=None)
        assert service._classify_content("This is an API endpoint for users") == "api-reference"
        assert service._classify_content("Install the package with pip install") == "guide"
        assert service._classify_content("Troubleshoot common errors and issues") == "troubleshooting"
        assert service._classify_content("System architecture and design patterns") == "concept"
        assert service._classify_content("Step by step tutorial for beginners") == "tutorial"
        assert service._classify_content("General reference documentation") == "reference"

    @pytest.mark.asyncio
    async def test_map_document_uses_cache(self):
        """Test that map phase uses cached results."""
        mock_db = AsyncMock()
        service = WikiService(db=mock_db)
        
        # Mock document
        doc = Document(
            id=uuid4(),
            filename="test.txt",
            content_type="text/plain",
            content="This is a test document for classification.",
        )
        
        # Mock cache hit
        cached_result = {
            "content_hash": "abc123",
            "slug": "test-doc",
            "summary": "Cached summary",
            "classification": "reference",
        }
        service._get_cached_map = AsyncMock(return_value=cached_result)
        
        result = await service._map_document(doc)
        
        assert result == cached_result
        service._get_cached_map.assert_called_once()

    @pytest.mark.asyncio
    async def test_map_document_generates_new(self):
        """Test that map phase generates new result when not cached."""
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()
        service = WikiService(db=mock_db)
        
        doc = Document(
            id=uuid4(),
            filename="api-guide.txt",
            content_type="text/plain",
            content="This is an API reference guide. It describes REST endpoints. Use HTTP methods.",
        )
        
        # Mock cache miss
        service._get_cached_map = AsyncMock(return_value=None)
        service._cache_map = AsyncMock()
        
        result = await service._map_document(doc)
        
        assert "content_hash" in result
        assert "slug" in result
        assert "summary" in result
        assert "classification" in result
        assert result["classification"] == "api-reference"
        service._cache_map.assert_called_once()


class TestWikiServiceIntegration:
    """Integration tests for WikiService (require database fixture)."""
    pass


class TestWikiServiceMultiDoc:
    """Tests for multi-document wiki generation behavior."""

    @pytest.mark.asyncio
    async def test_reduce_to_wiki_uses_combined_title(self):
        """Test that wiki title reflects multiple documents, not just the first."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        service = WikiService(db=mock_db)
        
        map_results = [
            {
                "slug": "doc-one",
                "summary": "Summary of document one about concepts.",
                "classification": "concept",
                "title": "Document One",
                "document_id": str(uuid4()),
            },
            {
                "slug": "doc-two",
                "summary": "Summary of document two about guides.",
                "classification": "guide",
                "title": "Document Two",
                "document_id": str(uuid4()),
            },
        ]
        
        source_doc_ids = [mr["document_id"] for mr in map_results]
        
        # Mock _slug_exists to return False
        service._slug_exists = AsyncMock(return_value=False)
        
        wiki_page = await service._reduce_to_wiki(map_results, source_doc_ids)
        
        # Title should reflect multiple documents
        assert "Document One" in wiki_page.title
        assert "Document Two" in wiki_page.title
        # Or should be a combined title
        assert len(wiki_page.title) > len("Document One")

    @pytest.mark.asyncio
    async def test_reduce_to_wiki_handles_slug_collision(self):
        """Test that slug generation handles collisions correctly."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        service = WikiService(db=mock_db)
        
        map_results = [
            {
                "slug": "existing-slug",
                "summary": "Summary of document.",
                "classification": "concept",
                "title": "Test Document",
                "document_id": str(uuid4()),
            },
        ]
        
        source_doc_ids = [mr["document_id"] for mr in map_results]
        
        # Mock _slug_exists to return True first, then False
        call_count = 0
        async def mock_slug_exists(slug):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return True  # First call - slug exists
            return False  # Subsequent calls - slug available
        
        service._slug_exists = mock_slug_exists
        
        wiki_page = await service._reduce_to_wiki(map_results, source_doc_ids)
        
        # Should have generated a unique slug with counter
        assert wiki_page.slug == "existing-slug-1"

    @pytest.mark.asyncio
    async def test_reduce_to_wiki_summary_combines_all(self):
        """Test that wiki summary combines summaries from all documents."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        service = WikiService(db=mock_db)
        
        map_results = [
            {
                "slug": "doc-one",
                "summary": "First document summary about concepts.",
                "classification": "concept",
                "title": "Document One",
                "document_id": str(uuid4()),
            },
            {
                "slug": "doc-two",
                "summary": "Second document summary about guides.",
                "classification": "guide",
                "title": "Document Two",
                "document_id": str(uuid4()),
            },
            {
                "slug": "doc-three",
                "summary": "Third document summary about api-reference.",
                "classification": "api-reference",
                "title": "Document Three",
                "document_id": str(uuid4()),
            },
        ]
        
        source_doc_ids = [mr["document_id"] for mr in map_results]
        
        service._slug_exists = AsyncMock(return_value=False)
        
        wiki_page = await service._reduce_to_wiki(map_results, source_doc_ids)
        
        # Summary should contain content from multiple documents
        assert "concepts" in wiki_page.summary.lower()
        assert "guides" in wiki_page.summary.lower()
        assert "api" in wiki_page.summary.lower()

