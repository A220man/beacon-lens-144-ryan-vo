from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship, declarative_base
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    token_count = Column(Integer, nullable=False)
    embedding = Column(Vector(384), nullable=True)  # Using 384-dim for sentence-transformers/all-MiniLM-L6-v2
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_document_id", "document_id"),
        Index("ix_chunks_embedding", "embedding", postgresql_using="ivfflat", postgresql_with={"lists": 100}),
    )


class WikiPage(Base):
    __tablename__ = "wiki_pages"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    source_document_ids = Column(JSON, nullable=False, default=list)  # List of document UUIDs
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sections = relationship("WikiSection", back_populates="wiki_page", cascade="all, delete-orphan", order_by="WikiSection.order_index")


class WikiSection(Base):
    __tablename__ = "wiki_sections"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wiki_page_id = Column(PG_UUID(as_uuid=True), ForeignKey("wiki_pages.id", ondelete="CASCADE"), nullable=False)
    heading = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    wiki_page = relationship("WikiPage", back_populates="sections")

    __table_args__ = (
        Index("ix_wiki_sections_wiki_page_id", "wiki_page_id"),
        Index("ix_wiki_sections_order", "wiki_page_id", "order_index"),
    )


class MapCache(Base):
    __tablename__ = "map_cache"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_hash = Column(String(64), nullable=False, unique=True, index=True)  # SHA256 of normalized content
    slug = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    classification = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_map_cache_content_hash", "content_hash"),
    )
