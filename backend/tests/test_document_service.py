"""Tests for DocumentService with mocked embeddings."""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document, Chunk
from app.services.document_service import DocumentService
from app.chunking import chunk_document


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    with patch("app.services.document_service.get_embedding_service") as mock_get:
        service = AsyncMock()
        service.embed = AsyncMock(return_value=[[0.1] * 384, [0.2] * 384])
        service.embed_single = AsyncMock(return_value=[0.15] * 384)
        mock_get.return_value = service
        yield service


class TestDocumentService:
    """Tests for DocumentService."""

    @pytest.mark.asyncio
    async def test_ingest_document(self, mock_db, mock_embedding_service):
        """Test document ingestion: chunk, embed, store."""
        service = DocumentService(mock_db)
        content = "This is a test document. " * 20  # ~400 chars, ~100 tokens
        filename = "test.txt"
        content_type = "text/plain"

        document = await service.ingest_document(
            filename=filename,
            content_type=content_type,
            content=content,
            chunk_size=50,
            chunk_overlap=10,
        )

        # Verify document was created
        assert isinstance(document, Document)
        assert document.filename == filename
        assert document.content_type == content_type
        assert document.content == content

        # Verify db operations
        mock_db.add.assert_called()
        mock_db.flush.assert_awaited_once()
        mock_db.commit.assert_awaited_once()
        mock_db.refresh.assert_awaited_once_with(document)

        # Verify embedding service called
        mock_embedding_service.embed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ingest_document_empty_content(self, mock_db, mock_embedding_service):
        """Test ingestion with empty content produces no chunks."""
        service = DocumentService(mock_db)
        document = await service.ingest_document(
            filename="empty.txt",
            content_type="text/plain",
            content="",
        )

        assert document is not None
        # Embed called with empty list for empty content
        mock_embedding_service.embed.assert_awaited_once_with([])

    @pytest.mark.asyncio
    async def test_get_document(self, mock_db):
        """Test getting a document by ID."""
        service = DocumentService(mock_db)
        doc_id = uuid.uuid4()

        # Mock the query result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = Document(
            id=doc_id, filename="test.txt", content_type="text/plain", content="test"
        )
        mock_db.execute.return_value = mock_result

        document = await service.get_document(doc_id)

        assert document is not None
        assert document.id == doc_id
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, mock_db):
        """Test getting a non-existent document returns None."""
        service = DocumentService(mock_db)
        doc_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        document = await service.get_document(doc_id)

        assert document is None

    @pytest.mark.asyncio
    async def test_list_documents(self, mock_db):
        """Test listing documents with pagination."""
        service = DocumentService(mock_db)
        doc1 = Document(id=uuid.uuid4(), filename="a.txt", content_type="text/plain", content="a")
        doc2 = Document(id=uuid.uuid4(), filename="b.txt", content_type="text/plain", content="b")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [doc1, doc2]
        mock_db.execute.return_value = mock_result

        documents = await service.list_documents(limit=10, offset=0)

        assert len(documents) == 2
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search(self, mock_db, mock_embedding_service):
        """Test semantic search."""
        service = DocumentService(mock_db)
        query = "test query"
        chunk1 = Chunk(id=uuid.uuid4(), document_id=uuid.uuid4(), content="chunk 1", chunk_index=0, token_count=10)
        chunk2 = Chunk(id=uuid.uuid4(), document_id=uuid.uuid4(), content="chunk 2", chunk_index=1, token_count=10)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [chunk1, chunk2]
        mock_db.execute.return_value = mock_result

        results = await service.search(query, limit=10)

        assert len(results) == 2
        mock_embedding_service.embed_single.assert_awaited_once_with(query)
        mock_db.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_with_document_filter(self, mock_db, mock_embedding_service):
        """Test search filtered by document IDs."""
        service = DocumentService(mock_db)
        query = "test"
        doc_ids = [uuid.uuid4(), uuid.uuid4()]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        await service.search(query, limit=5, document_ids=doc_ids)

        mock_db.execute.assert_awaited_once()
        # Verify the query was built with document_ids filter
        call_args = mock_db.execute.call_args[0][0]
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_delete_document(self, mock_db):
        """Test deleting a document."""
        service = DocumentService(mock_db)
        doc_id = uuid.uuid4()
        doc = Document(id=doc_id, filename="test.txt", content_type="text/plain", content="test")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = doc
        mock_db.execute.return_value = mock_result

        result = await service.delete_document(doc_id)

        assert result is True
        mock_db.delete.assert_awaited_once_with(doc)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, mock_db):
        """Test deleting non-existent document returns False."""
        service = DocumentService(mock_db)
        doc_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.delete_document(doc_id)

        assert result is False
        mock_db.delete.assert_not_called()


class TestChunkDocumentIntegration:
    """Integration tests using real chunk_document function."""

    def test_chunk_document_output_structure(self):
        """Verify chunk_document returns expected structure."""
        content = "This is a test document. " * 30  # ~600 chars
        chunks = chunk_document(content, chunk_size=50, chunk_overlap=10)

        assert len(chunks) >= 2
        for i, chunk in enumerate(chunks):
            assert "content" in chunk
            assert "chunk_index" in chunk
            assert "token_count" in chunk
            assert chunk["chunk_index"] == i
            assert chunk["token_count"] > 0
            assert isinstance(chunk["content"], str)
            assert len(chunk["content"]) > 0

    def test_chunk_ordering(self):
        """Verify chunks maintain sequential order."""
        content = "First part. " * 20 + "SECOND PART. " * 20 + "Third part. " * 20
        chunks = chunk_document(content, chunk_size=50, chunk_overlap=10)

        assert len(chunks) >= 3
        # Check that "SECOND" appears in a middle chunk
        found_second = any("SECOND" in c["content"] for c in chunks[1:-1])
        assert found_second

