"""Wiki API routes."""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...database import get_db
from ...models import WikiPage, WikiSection
from ...services.wiki_service import WikiService

router = APIRouter(prefix="/wiki", tags=["wiki"])


class WikiSectionResponse(BaseModel):
    id: uuid.UUID
    wiki_page_id: uuid.UUID
    heading: str
    content: str
    order_index: int
    created_at: datetime

    class Config:
        from_attributes = True


class WikiPageResponse(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    content: str
    summary: Optional[str]
    source_document_ids: List[str]
    created_at: datetime
    updated_at: datetime
    sections: List[WikiSectionResponse] = []

    class Config:
        from_attributes = True


class WikiPageListResponse(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    summary: Optional[str]
    source_document_ids: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GenerateWikiRequest(BaseModel):
    document_ids: List[uuid.UUID] = Field(..., min_length=1)


@router.post("/generate", response_model=WikiPageResponse, status_code=status.HTTP_201_CREATED)
async def generate_wiki(
    request: GenerateWikiRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a wiki page from a list of document IDs."""
    wiki_service = WikiService(db)
    try:
        doc_ids = [str(d) for d in request.document_ids]
        wiki_page = await wiki_service.generate_wiki(doc_ids)
        # Load sections
        sections_result = await db.execute(
            select(WikiSection).where(WikiSection.wiki_page_id == wiki_page.id).order_by(WikiSection.order_index)
        )
        wiki_page.sections = list(sections_result.scalars().all())
        return wiki_page
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Wiki generation failed: {str(e)}")


@router.get("", response_model=List[WikiPageListResponse])
async def list_wiki_pages(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List all wiki pages with pagination."""
    wiki_service = WikiService(db)
    pages = await wiki_service.list_wiki_pages(limit=limit, offset=offset)
    return pages


@router.get("/search", response_model=List[WikiPageListResponse])
async def search_wiki_pages(
    query: str = Query(..., min_length=1, max_length=1000),
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Search wiki pages by query string."""
    wiki_service = WikiService(db)
    pages = await wiki_service.search_wiki_pages(query, limit=limit)
    return pages


@router.get("/{wiki_id}", response_model=WikiPageResponse)
async def get_wiki_page(
    wiki_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a wiki page by ID with sections."""
    wiki_service = WikiService(db)
    wiki_page = await wiki_service.get_wiki_page(str(wiki_id))
    if not wiki_page:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    # Load sections
    sections_result = await db.execute(
        select(WikiSection).where(WikiSection.wiki_page_id == wiki_page.id).order_by(WikiSection.order_index)
    )
    wiki_page.sections = list(sections_result.scalars().all())
    return wiki_page


@router.get("/slug/{slug}", response_model=WikiPageResponse)
async def get_wiki_page_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a wiki page by slug with sections."""
    wiki_service = WikiService(db)
    wiki_page = await wiki_service.get_wiki_page_by_slug(slug)
    if not wiki_page:
        raise HTTPException(status_code=404, detail="Wiki page not found")
    # Load sections
    sections_result = await db.execute(
        select(WikiSection).where(WikiSection.wiki_page_id == wiki_page.id).order_by(WikiSection.order_index)
    )
    wiki_page.sections = list(sections_result.scalars().all())
    return wiki_page


@router.delete("/{wiki_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wiki_page(
    wiki_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a wiki page and its sections."""
    wiki_service = WikiService(db)
    success = await wiki_service.delete_wiki_page(str(wiki_id))
    if not success:
        raise HTTPException(status_code=404, detail="Wiki page not found")
