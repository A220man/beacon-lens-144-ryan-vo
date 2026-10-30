
"""Document API routes."""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models import Document, Chunk
from ...services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    chunk_count: int
    created_at: str


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    chunk_index: int
    token_count: int
    similarity: float

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=50)
    document_ids: Optional[List[uuid.UUID]] = None


class SearchResponse(BaseModel):
    results: List[ChunkResponse]
    query: str


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and ingest a document.

    Supported formats: text/plain, application/pdf (PDF text extraction not yet implemented)
    """
    # Read file content
    content_bytes = await file.read()
    
    # For now, only support text files
    if file.content_type not in ("text/plain", "text/markdown"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {file.content_type}. Supported: text/plain, text/markdown",
        )

    content = content_bytes.decode("utf-8")

    # Ingest document
    service = DocumentService(db)
    document = await service.ingest_document(
        filename=file.filename or "unknown",
        content_type=file.content_type,
        content=content,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Count chunks
    chunk_count_result = await db.execute(
        select(Chunk).where(Chunk.document_id == document.id)
    )
    chunk_count = len(chunk_count_result.scalars().all())

    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        content_type=document.content_type,
        chunk_count=chunk_count,
        created_at=document.created_at.isoformat(),
    )


@router.get("", response_model=List[DocumentResponse])
async def list_documents(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List all documents with pagination."""
    service = DocumentService(db)
    documents = await service.list_documents(limit=limit, offset=offset)
    return documents


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a document by ID."""
    service = DocumentService(db)
    document = await service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Semantic search across documents.

    Returns chunks ranked by cosine similarity to the query embedding.
    """
    service = DocumentService(db)
    chunks = await service.search(
        query=request.query,
        limit=request.limit,
        document_ids=request.document_ids,
    )

    results = []
    for chunk in chunks:
        # In a real implementation, we'd use a subquery to get the distance
        similarity = 0.0  # Placeholder

        results.append(ChunkResponse(
            id=chunk.id,
            document_id=chunk.document_id,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            token_count=chunk.token_count,
            similarity=similarity,
        ))

    return SearchResponse(results=results, query=request.query)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document and its chunks."""
    service = DocumentService(db)
    deleted = await service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
