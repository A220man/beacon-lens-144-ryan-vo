"""Tests for wiki API routes."""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import status

from app.main import create_app
from app.database import get_db
from app.models import WikiPage, WikiSection


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    return create_app()


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.delete = AsyncMock()
    return db


def override_get_db(mock_db):
    """Create a dependency override for get_db."""
    async def _override():
        yield mock_db
    return _override


def mock_scalars_all(result_list):
    """Create a mock that returns result_list when scalars().all() is called."""
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = result_list
    mock_result.scalars.return_value = mock_scalars
    return mock_result


class TestWikiAPI:
    """Tests for wiki API endpoints."""

    @pytest.mark.asyncio
    async def test_generate_wiki_requires_documents(self, app):
        """Test that generate wiki requires at least one document ID."""
        app.dependency_overrides[get_db] = override_get_db(AsyncMock())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/wiki/generate",
                json={"document_ids": []},
            )
        app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_list_wiki_pages(self, app, mock_db):
        """Test listing wiki pages."""
        # Mock the execute result for list_wiki_pages
        mock_db.execute.return_value = mock_scalars_all([])
        
        app.dependency_overrides[get_db] = override_get_db(mock_db)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/wiki")
        app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_search_wiki_pages(self, app, mock_db):
        """Test searching wiki pages."""
        # Mock the execute result for search_wiki_pages
        mock_db.execute.return_value = mock_scalars_all([])
        
        app.dependency_overrides[get_db] = override_get_db(mock_db)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/wiki/search?query=test")
        app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_search_wiki_requires_query(self, app):
        """Test that search requires a query parameter."""
        app.dependency_overrides[get_db] = override_get_db(AsyncMock())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/wiki/search")
        app.dependency_overrides.clear()
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestWikiAPIIntegration:
    """Integration tests for wiki API (require database)."""
    pass
