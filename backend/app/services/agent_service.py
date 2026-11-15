"""Wiki generation service with map/reduce pipeline."""
import hashlib
import re
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Document, Chunk, WikiPage, WikiSection, MapCache
from ..embeddings import get_embedding_service
from ..chunking import chunk_text


class WikiService:
    """Service for wiki generation using map/reduce pipeline."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = get_embedding_service()

    def _normalize_content(self, content: str) -> str:
        """Normalize content for consistent hashing."""
        return re.sub(r"\s+", " ", content.strip()).lower()

    def _content_hash(self, content: str) -> str:
        """Generate SHA256 hash of normalized content."""
        normalized = self._normalize_content(content)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _extract_slug(self, content: str) -> str:
        """Extract a URL-friendly slug from content."""
        sentences = re.split(r"[.!?]\s+", content)
        base = sentences[0] if sentences else content[:50]
        slug = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
        return slug[:100] or "untitled"

    def _classify_content(self, content: str) -> str:
        """Classify content type based on keywords."""
        content_lower = content.lower()
        if any(kw in content_lower for kw in ["api", "endpoint", "http", "rest", "graphql"]):
            return "api-reference"
        elif any(kw in content_lower for kw in ["install", "setup", "configure", "deploy"]):
            return "guide"
        elif any(kw in content_lower for kw in ["error", "troubleshoot", "debug", "issue", "problem"]):
            return "troubleshooting"
        elif any(kw in content_lower for kw in ["architecture", "design", "pattern", "concept"]):
            return "concept"
        elif any(kw in content_lower for kw in ["tutorial", "walkthrough", "step-by-step", "example"]):
            return "tutorial"
        else:
            return "reference"

    async def _map_document(self, document: Document) -> Dict[str, Any]:
        """Map phase: extract slug, summary, classification for a document."""
        content_hash = self._content_hash(document.content)

        cached = await self._get_cached_map(content_hash)
        if cached:
            return cached

        sentences = re.split(r"[.!?]\s+", document.content)
        summary = ". ".join(sentences[:3])
        if len(summary) > 300:
            summary = summary[:300].rsplit(" ", 1)[0] + "..."

        slug = self._extract_slug(document.content)
        classification = self._classify_content(document.content)

        result = {
            "content_hash": content_hash,
            "slug": slug,
            "summary": summary,
            "classification": classification,
        }

        await self._cache_map(result)
        return result

    async def _get_cached_map(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached map result."""
        result = await self.db.execute(
            select(MapCache).where(MapCache.content_hash == content_hash)
        )
        cached = result.scalar_one_or_none()
        if cached:
            return {
                "content_hash": cached.content_hash,
                "slug": cached.slug,
                "summary": cached.summary,
                "classification": cached.classification,
            }
        return None

    async def _cache_map(self, map_result: Dict[str, Any]) -> None:
        """Store map result in cache."""
        cache_entry = MapCache(
            content_hash=map_result["content_hash"],
            slug=map_result["slug"],
            summary=map_result["summary"],
            classification=map_result["classification"],
        )
        self.db.add(cache_entry)
        await self.db.flush()

    async def generate_wiki(self, document_ids: List[str]) -> WikiPage:
        """Generate wiki from documents using map/reduce pipeline."""
        docs_result = await self.db.execute(
            select(Document).where(Document.id.in_(document_ids))
        )
        documents = list(docs_result.scalars().all())

        if not documents:
            raise ValueError("No documents found for wiki generation")

        map_results = []
        for doc in documents:
            map_result = await self._map_document(doc)
            map_result["document_id"] = str(doc.id)
            map_result["title"] = doc.filename
            map_results.append(map_result)

        wiki_page = await self._reduce_to_wiki(map_results, [str(d.id) for d in documents])

        await self.db.commit()
        await self.db.refresh(wiki_page)
        return wiki_page

    async def _reduce_to_wiki(
        self, map_results: List[Dict[str, Any]], source_doc_ids: List[str]
    ) -> WikiPage:
        """Reduce phase: merge map results into a wiki page with sections."""
        by_classification: Dict[str, List[Dict[str, Any]]] = {}
        for mr in map_results:
            cls = mr["classification"]
            if cls not in by_classification:
                by_classification[cls] = []
            by_classification[cls].append(mr)

        base_slug = map_results[0]["slug"]
        slug = base_slug
        counter = 1
        while await self._slug_exists(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        sections_content = []
        section_objects = []
        order = 0

        class_order = ["concept", "guide", "tutorial", "api-reference", "reference", "troubleshooting"]
        sorted_classes = sorted(
            by_classification.keys(),
            key=lambda c: class_order.index(c) if c in class_order else len(class_order)
        )

        for cls in sorted_classes:
            items = by_classification[cls]
            if not items:
                continue

            heading = cls.replace("-", " ").title()
            section_content = f"## {heading}\n\n"

            for item in items:
                section_content += f"### {item['title']}\n\n"
                section_content += f"{item['summary']}\n\n"
                section_content += f"*Source: {item['document_id']}*\n\n"

            sections_content.append(section_content)
            section_objects.append({
                "heading": heading,
                "content": section_content.strip(),
                "order_index": order,
            })
            order += 1

        full_content = "\n\n---\n\n".join(sections_content)

        all_summaries = [mr["summary"] for mr in map_results]
        wiki_summary = " ".join(all_summaries[:3])
        if len(wiki_summary) > 500:
            wiki_summary = wiki_summary[:500].rsplit(" ", 1)[0] + "..."

        # Generate combined title from all document titles
        if len(map_results) == 1:
            wiki_title = map_results[0]["title"]
        else:
            titles = [mr["title"] for mr in map_results]
            wiki_title = " + ".join(titles)
            if len(wiki_title) > 200:
                wiki_title = wiki_title[:197] + "..."

        wiki_page = WikiPage(
            slug=slug,
            title=wiki_title,
            content=full_content,
            summary=wiki_summary,
            source_document_ids=source_doc_ids,
        )
        self.db.add(wiki_page)
        await self.db.flush()

        for sec_data in section_objects:
            section = WikiSection(
                wiki_page_id=wiki_page.id,
                heading=sec_data["heading"],
                content=sec_data["content"],
                order_index=sec_data["order_index"],
            )
            self.db.add(section)

        return wiki_page

    async def _slug_exists(self, slug: str) -> bool:
        """Check if slug already exists."""
        result = await self.db.execute(
            select(WikiPage.id).where(WikiPage.slug == slug)
        )
        return result.scalar_one_or_none() is not None

    async def get_wiki_page(self, wiki_id: str) -> Optional[WikiPage]:
        """Get wiki page by ID with sections."""
        result = await self.db.execute(
            select(WikiPage).where(WikiPage.id == wiki_id)
        )
        return result.scalar_one_or_none()

    async def get_wiki_page_by_slug(self, slug: str) -> Optional[WikiPage]:
        """Get wiki page by slug with sections."""
        result = await self.db.execute(
            select(WikiPage).where(WikiPage.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_wiki_pages(self, limit: int = 50, offset: int = 0) -> List[WikiPage]:
        """List wiki pages with pagination."""
        result = await self.db.execute(
            select(WikiPage)
            .order_by(WikiPage.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def search_wiki_pages(self, query: str, limit: int = 10) -> List[WikiPage]:
        """Search wiki pages using text search."""
        result = await self.db.execute(
            select(WikiPage)
            .where(
                WikiPage.content.ilike(f"%{query}%") |
                WikiPage.title.ilike(f"%{query}%") |
                WikiPage.summary.ilike(f"%{query}%")
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_wiki_page(self, wiki_id: str) -> bool:
        """Delete a wiki page and its sections."""
        result = await self.db.execute(
            select(WikiPage).where(WikiPage.id == wiki_id)
        )
        wiki_page = result.scalar_one_or_none()
        if not wiki_page:
            return False
        await self.db.delete(wiki_page)
        await self.db.commit()
        return True


