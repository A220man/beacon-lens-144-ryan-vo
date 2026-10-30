
"""Document service for RAG operations."""
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Document, Chunk
from ..chunking import chunk_document
from ..embeddings import get_embedding_service


class DocumentService:
    """Service for document ingestion and retrieval."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = get_embedding_service()

    async def ingest_document(
        self,
        filename: str,
        content_type: str,
        content: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> Document:
        """
        Ingest a document: chunk, embed, and store.

        Args:
            filename: Original filename
            content_type: MIME type
            content: Document text content
            chunk_size: Token size per chunk
            chunk_overlap: Token overlap between chunks

        Returns:
            Created Document with chunks
        """
        # Create document
        document = Document(
            filename=filename,
            content_type=content_type,
            content=content,
        )
        self.db.add(document)
        await self.db.flush()

        # Chunk the document
        chunks_data = chunk_document(content, chunk_size, chunk_overlap)

        # Generate embeddings for all chunks
        chunk_texts = [c["content"] for c in chunks_data]
        embeddings = await self.embedding_service.embed(chunk_texts)

        # Create chunk records
        for i, (chunk_data, embedding) in enumerate(zip(chunks_data, embeddings)):
            chunk = Chunk(
                document_id=document.id,
                content=chunk_data["content"],
                chunk_index=chunk_data["chunk_index"],
                token_count=chunk_data["token_count"],
                embedding=embedding,
            )
            self.db.add(chunk)

        await self.db.commit()
        await self.db.refresh(document)
        return document

    async def get_document(self, document_id: uuid.UUID) -> Optional[Document]:
        """Get document by ID."""
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()

    async def list_documents(self, limit: int = 50, offset: int = 0) -> List[Document]:
        """List documents with pagination."""
        result = await self.db.execute(
            select(Document)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def search(
        self,
        query: str,
        limit: int = 10,
        document_ids: Optional[List[uuid.UUID]] = None,
    ) -> List[Chunk]:
        """
        Semantic search for relevant chunks.

        Args:
            query: Search query text
            limit: Maximum number of results
            document_ids: Optional filter by document IDs

        Returns:
            List of matching chunks with similarity scores
        """
        # Generate query embedding
        query_embedding = await self.embedding_service.embed_single(query)

        # Build query
        stmt = select(Chunk).where(Chunk.embedding.is_not(None))

        if document_ids:
            stmt = stmt.where(Chunk.document_id.in_(document_ids))

        # Use cosine similarity (pgvector uses <=> operator)
        stmt = stmt.order_by(Chunk.embedding.cosine_distance(query_embedding)).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_document(self, document_id: uuid.UUID) -> bool:
        """Delete a document and its chunks."""
        document = await self.get_document(document_id)
        if not document:
            return False

        await self.db.delete(document)
        await self.db.commit()
        return True
