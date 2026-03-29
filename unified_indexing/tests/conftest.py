"""
Test fixtures for unified_indexing module.
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unified_indexing.main import app
from unified_indexing.database import LightRAGDatabase


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def db():
    """Create database instance."""
    return LightRAGDatabase()


@pytest.fixture
def sample_entity():
    """Sample entity for testing."""
    return {
        "id": "test-entity-001",
        "name": "Test Entity",
        "type": "paper",
        "content": "This is a test entity for validation."
    }


@pytest.fixture
def mock_entities():
    """Mock entity list for testing."""
    return [
        {"id": "entity-001", "name": "Entity One", "type": "paper"},
        {"id": "entity-002", "name": "Entity Two", "type": "person"},
        {"id": "entity-003", "name": "Entity Three", "type": "concept"},
    ]
