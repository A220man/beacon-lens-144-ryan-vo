"""Agent API routes."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from ...database import get_db
from ...services.wiki_service import WikiService
from ...services.document_service import DocumentService

router = APIRouter(prefix="/agent", tags=["agent"])

