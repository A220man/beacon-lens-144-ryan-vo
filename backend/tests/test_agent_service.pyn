"""Tests for AgentService."""
import pytest
from unittest.mock import AsyncMock

from app.services.agent_service import AgentService

def test_agent_service_instantiation():
    mock_db = AsyncMock()
    service = AgentService(mock_db)
    assert service.db is mock_db
    assert hasattr(service, "answer_question")
