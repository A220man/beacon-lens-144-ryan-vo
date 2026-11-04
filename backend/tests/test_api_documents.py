"""Tests for document API endpoints."""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import create_app
from app.database import get_db
from app.models import Document, Chunk


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    return create_app()


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def mock_document_service():
    """Create a mock document service."""
    service = AsyncMock()
    service.ingest_document = AsyncMock()
    service.list_documents = AsyncMock()
    service.get_document = AsyncMock()
    service.search = AsyncMock()
    service.delete_document = AsyncMock()
    return service


def override_get_db(mock_db):
    """Create a dependency override for get_db."""
    async def _override():
        yield mock_db
    return _override


class TestUploadDocument:
    """Tests for POST /api/v1/documents/upload."""

    @pytest.mark.asyncio
    async def test_upload_text_file(self, app, mock_db, mock_document_service):
        """Test uploading a text file."""
        doc_id = uuid.uuid4()
        chunk_count = 3

        mock_document = Document(
            id=doc_id,
            filename="test.txt",
            content_type="text/plain",
            content="Test content " * 50,
            created_at=MagicMock(isoformat=lambda: "2024-01-01T00:00:00"),
        )

        mock_chunk_result = MagicMock()
        mock_chunk_result.scalars.return_value.all.return_value = [
            Chunk(id=uuid.uuid4(), document_id=doc_id, content="chunk", chunk_index=i, token_count=10)
            for i in range(chunk_count)
        ]

        # The endpoint calls db.execute once for chunk count after service.ingest_document
        mock_db.execute.return_value = mock_chunk_result
        mock_document_service.ingest_document.return_value = mock_document

        app.dependency_overrides[get_db] = override_get_db(mock_db)
        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("test.txt", b"Test content " * 50, "text/plain")},
                    data={"chunk_size": "500", "chunk_overlap": "50"},
                )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["id"] == str(doc_id)
        assert data["filename"] == "test.txt"
        assert data["content_type"] == "text/plain"
        assert data["chunk_count"] == chunk_count

    @pytest.mark.asyncio
    async def test_upload_markdown_file(self, app, mock_db, mock_document_service):
        """Test uploading a markdown file."""
        doc_id = uuid.uuid4()

        mock_document = Document(
            id=doc_id,
            filename="test.md",
            content_type="text/markdown",
            content="# Header\n\nContent",
            created_at=MagicMock(isoformat=lambda: "2024-01-01T00:00:00"),
        )

        mock_chunk_result = MagicMock()
        mock_chunk_result.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [MagicMock(scalar_one_or_none=lambda: mock_document), mock_chunk_result]
        mock_document_service.ingest_document.return_value = mock_document

        app.dependency_overrides[get_db] = override_get_db(mock_db)
        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("test.md", b"# Header\n\nContent", "text/markdown")},
                )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["filename"] == "test.md"
        assert data["content_type"] == "text/markdown"

    @pytest.mark.asyncio
    async def test_upload_unsupported_type(self, app, mock_db, mock_document_service):
        """Test uploading unsupported file type returns 400."""
        app.dependency_overrides[get_db] = override_get_db(mock_db)
        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("test.pdf", b"PDF content", "application/pdf")},
                )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Unsupported content type" in data["detail"]

    @pytest.mark.asyncio
    async def test_upload_empty_filename(self, app, mock_db, mock_document_service):
        """Test uploading file with no filename - FastAPI returns 422 for empty filename."""
        app.dependency_overrides[get_db] = override_get_db(mock_db)
        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("", b"content", "text/plain")},
                )

        app.dependency_overrides.clear()

        # FastAPI validates UploadFile and returns 422 for empty filename
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestListDocuments:
    """Tests for GET /api/v1/documents."""

    @pytest.mark.asyncio
    async def test_list_documents(self, app, mock_db, mock_document_service):
        """Test listing documents."""
        from datetime import datetime
        now = datetime.utcnow()
        doc1 = Document(id=uuid.uuid4(), filename="a.txt", content_type="text/plain", content="a", created_at=now, updated_at=now)
        doc2 = Document(id=uuid.uuid4(), filename="b.txt", content_type="text/plain", content="b", created_at=now, updated_at=now)

        mock_document_service.list_documents.return_value = [doc1, doc2]

        app.dependency_overrides[get_db] = override_get_db(mock_db)
        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/documents")

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["filename"] == "a.txt"
        assert data[1]["filename"] == "b.txt"


class TestGetDocument:
    """Tests for GET /api/v1/documents/{document_id}."""

    @pytest.mark.asyncio
    async def test_get_document(self, app, mock_db, mock_document_service):
        """Test getting a document by ID."""
        from datetime import datetime
        now = datetime.utcnow()
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            filename="test.txt",
            content_type="text/plain",
            content="Test content",
            created_at=now,
            updated_at=now,
        )

        mock_document_service.get_document.return_value = doc

        app.dependency_overrides[get_db] = override_get_db(mock_db)
        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/documents/{doc_id}")

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(doc_id)
        assert data["filename"] == "test.txt"

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, app, mock_db, mock_document_service):
        """Test getting non-existent document returns 404."""
        doc_id = uuid.uuid4()

        mock_document_service.get_document.return_value = None

        app.dependency_overrides[get_db] = override_get_db(mock_db)
        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/api/v1/documents/{doc_id}")

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSearchDocuments:
    """Tests for POST /api/v1/documents/search."""

    @pytest.mark.asyncio
    async def test_search_documents(self, app, mock_db, mock_document_service):
        """Test semantic search."""
        query = "test query"
        chunk1 = Chunk(id=uuid.uuid4(), document_id=uuid.uuid4(), content="chunk 1", chunk_index=0, token_count=10)
        chunk2 = Chunk(id=uuid.uuid4(), document_id=uuid.uuid4(), content="chunk 2", chunk_index=1, token_count=10)

        mock_document_service.search.return_value = [chunk1, chunk2]

        app.dependency_overrides[get_db] = override_get_db(mock_db)
        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/documents/search",
                    json={"query": query, "limit": 10},
                )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["query"] == query
        assert len(data["results"]) == 2

    @pytest.mark.asyncio
    async def test_search_with_document_filter(self, app, mock_db, mock_document_service):
        """Test search with document ID filter."""
        doc_ids = [uuid.uuid4(), uuid.uuid4()]

        mock_document_service.search.return_value = []

        app.dependency_overrides[get_db] = override_get_db(mock_db)
        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/documents/search",
                    json={"query": "test", "limit": 5, "document_ids": [str(d) for d in doc_ids]},
                )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["query"] == "test"

    @pytest.mark.asyncio
    async def test_search_empty_query(self, app, mock_db, mock_document_service):
        """Test search with empty query returns 422."""
        app.dependency_overrides[get_db] = override_get_db(mock_db)
        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/documents/search",
                    json={"query": "", "limit": 10},
                )

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDeleteDocument:
    """Tests for DELETE /api/v1/documents/{document_id}."""

    @pytest.mark.asyncio
    async def test_delete_document(self, app, mock_db, mock_document_service):
        """Test deleting a document."""
        doc_id = uuid.uuid4()

        mock_document_service.delete_document.return_value = True

        app.dependency_overrides[get_db] = override_get_db(mock_db)
        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/api/v1/documents/{doc_id}")

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, app, mock_db, mock_document_service):
        """Test deleting non-existent document returns 404."""
        doc_id = uuid.uuid4()
        mock_document_service.delete_document.return_value = False

        with patch("app.api.v1.documents.DocumentService", return_value=mock_document_service):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/api/v1/documents/{doc_id}")

        app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_404_NOT_FOUND
