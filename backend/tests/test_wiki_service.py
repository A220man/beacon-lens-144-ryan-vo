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
