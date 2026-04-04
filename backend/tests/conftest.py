"""
Pytest configuration and fixtures for KG RAG backend tests.
"""

import os
import sys
import pytest
import numpy as np
from unittest.mock import MagicMock, AsyncMock, patch
from typing import List, Dict, Any, Optional

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_postgres_client():
    """Mock PostgresClient for testing without database connection."""
    mock = MagicMock()
    mock.is_connected = True
    mock.pool = MagicMock()
    return mock


@pytest.fixture
def sample_chunks() -> List[Dict[str, Any]]:
    """Sample chunk data for testing."""
    return [
        {
            "chunk_id": "chunk-001",
            "content": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
            "source": "test_doc.pdf",
            "entity_ids": ["ml-001", "ai-001"],
            "relationship_ids": [],
            "embedding": [0.1] * 768,
            "created_at": "2026-01-01T00:00:00Z"
        },
        {
            "chunk_id": "chunk-002",
            "content": "Deep learning uses neural networks with multiple layers to achieve better accuracy.",
            "source": "test_doc.pdf",
            "entity_ids": ["dl-001"],
            "relationship_ids": ["rel-001"],
            "embedding": [0.2] * 768,
            "created_at": "2026-01-02T00:00:00Z"
        },
        {
            "chunk_id": "chunk-003",
            "content": "Natural language processing helps computers understand human language.",
            "source": "test_doc.pdf",
            "entity_ids": ["nlp-001"],
            "relationship_ids": ["rel-002"],
            "embedding": [0.3] * 768,
            "created_at": "2026-01-03T00:00:00Z"
        }
    ]


@pytest.fixture
def sample_entities() -> List[Dict[str, Any]]:
    """Sample entity data for testing."""
    return [
        {
            "entity_id": "ml-001",
            "entity_type": "concept",
            "name": "Machine Learning",
            "description": "A subset of AI that enables learning from data",
            "embedding": [0.1] * 768
        },
        {
            "entity_id": "ai-001",
            "entity_type": "concept",
            "name": "Artificial Intelligence",
            "description": "The broader field of making machines intelligent",
            "embedding": [0.15] * 768
        },
        {
            "entity_id": "dl-001",
            "entity_type": "concept",
            "name": "Deep Learning",
            "description": "Neural networks with multiple layers",
            "embedding": [0.2] * 768
        },
        {
            "entity_id": "nlp-001",
            "entity_type": "concept",
            "name": "Natural Language Processing",
            "description": "Processing human language",
            "embedding": [0.25] * 768
        }
    ]


@pytest.fixture
def sample_relationships() -> List[Dict[str, Any]]:
    """Sample relationship data for testing."""
    return [
        {
            "relationship_id": "rel-001",
            "source_id": "dl-001",
            "target_id": "ml-001",
            "relationship_type": "is_subset_of",
            "description": "Deep learning is a subset of machine learning",
            "embedding": [0.12] * 768
        },
        {
            "relationship_id": "rel-002",
            "source_id": "nlp-001",
            "target_id": "ai-001",
            "relationship_type": "is_part_of",
            "description": "NLP is part of AI research",
            "embedding": [0.18] * 768
        }
    ]


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client for testing without Ollama service."""
    mock = MagicMock()
    mock.host = "http://localhost:11434"
    mock.model = "nomic-embed-text"
    mock.dimension = 768

    async def mock_embed(texts: List[str]) -> List[List[float]]:
        """Return mock embeddings."""
        return [[0.1] * 768 for _ in texts]

    mock.embed = mock_embed
    mock.embed_sync = lambda texts: [0.1] * 768
    mock.health_check = AsyncMock(return_value={"status": "healthy", "model_available": True})
    mock.similarity = lambda e1, e2: 0.5

    return mock


@pytest.fixture
def mock_api_config():
    """Mock API configuration."""
    return {
        "ollama": {
            "host": "http://localhost:11434",
            "model": "nomic-embed-text",
            "dimension": 768
        },
        "search": {
            "default_mode": "smart",
            "chunk_top_k": 50,
            "entity_top_k": 20,
            "relationship_top_k": 20,
            "final_top_k": 10
        },
        "llm": {
            "primary": "deepseek",
            "fallback": "minimax",
            "temperature": 0.7,
            "max_tokens": 2000
        }
    }


class MockStorage:
    """Mock storage layer for testing without database."""

    def __init__(self):
        self.chunks: Dict[str, Dict] = {}
        self.entities: Dict[str, Dict] = {}
        self.relationships: Dict[str, Dict] = {}
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """Simulate connection."""
        self._connected = True
        return True

    async def disconnect(self):
        """Simulate disconnection."""
        self._connected = False

    async def search_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Simulate chunk search by cosine similarity."""
        results = []
        for chunk_id, chunk in self.chunks.items():
            if chunk.get("embedding"):
                score = self._cosine_similarity(query_embedding, chunk["embedding"])
                if score >= min_score:
                    results.append({**chunk, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def search_entities(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        entity_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Simulate entity search."""
        results = []
        for entity_id, entity in self.entities.items():
            if entity_types and entity.get("entity_type") not in entity_types:
                continue
            if entity.get("embedding"):
                score = self._cosine_similarity(query_embedding, entity["embedding"])
                results.append({**entity, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def search_relationships(
        self,
        query_embedding: List[float],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Simulate relationship search."""
        results = []
        for rel_id, rel in self.relationships.items():
            if rel.get("embedding"):
                score = self._cosine_similarity(query_embedding, rel["embedding"])
                results.append({**rel, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def get_related_entities(
        self,
        entity_id: str,
        max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Simulate graph traversal."""
        visited = {entity_id}
        results = []

        def traverse(current_id: str, depth: int):
            if depth > max_depth:
                return
            for rel_id, rel in self.relationships.items():
                if rel["source_id"] == current_id:
                    target_id = rel["target_id"]
                    if target_id not in visited:
                        visited.add(target_id)
                        target = self.entities.get(target_id, {})
                        results.append({**target, "relationship": rel, "depth": depth})
                        traverse(target_id, depth + 1)
                elif rel["target_id"] == current_id:
                    source_id = rel["source_id"]
                    if source_id not in visited:
                        visited.add(source_id)
                        source = self.entities.get(source_id, {})
                        results.append({**source, "relationship": rel, "depth": depth})
                        traverse(source_id, depth + 1)

        traverse(entity_id, 1)
        return results

    async def get_chunks_by_entity(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get chunks associated with an entity."""
        return [c for c in self.chunks.values() if entity_id in c.get("entity_ids", [])]

    def add_chunk(self, chunk: Dict[str, Any]):
        self.chunks[chunk["chunk_id"]] = chunk

    def add_entity(self, entity: Dict[str, Any]):
        self.entities[entity["entity_id"]] = entity

    def add_relationship(self, relationship: Dict[str, Any]):
        self.relationships[relationship["relationship_id"]] = relationship

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        if not vec1 or not vec2:
            return 0.0
        v1 = np.array(vec1, dtype=np.float64)
        v2 = np.array(vec2, dtype=np.float64)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))


@pytest.fixture
def storage():
    """Create a mock storage instance with sample data."""
    store = MockStorage()

    # Add sample entities
    store.add_entity({
        "entity_id": "ml-001",
        "entity_type": "concept",
        "name": "Machine Learning",
        "description": "A subset of AI",
        "embedding": [0.1] * 768
    })
    store.add_entity({
        "entity_id": "ai-001",
        "entity_type": "concept",
        "name": "Artificial Intelligence",
        "description": "Making machines intelligent",
        "embedding": [0.5] * 768
    })
    store.add_entity({
        "entity_id": "dl-001",
        "entity_type": "concept",
        "name": "Deep Learning",
        "description": "Neural networks",
        "embedding": [0.2] * 768
    })

    # Add sample relationships
    store.add_relationship({
        "relationship_id": "rel-001",
        "source_id": "dl-001",
        "target_id": "ml-001",
        "relationship_type": "is_subset_of",
        "description": "Deep learning is subset of ML",
        "embedding": [0.15] * 768
    })
    store.add_relationship({
        "relationship_id": "rel-002",
        "source_id": "ml-001",
        "target_id": "ai-001",
        "relationship_type": "is_subset_of",
        "description": "ML is subset of AI",
        "embedding": [0.3] * 768
    })

    # Add sample chunks
    store.add_chunk({
        "chunk_id": "chunk-001",
        "content": "Machine learning enables systems to learn from data.",
        "source": "doc1.pdf",
        "entity_ids": ["ml-001"],
        "relationship_ids": [],
        "embedding": [0.1] * 768
    })
    store.add_chunk({
        "chunk_id": "chunk-002",
        "content": "Deep learning uses neural networks for pattern recognition.",
        "source": "doc2.pdf",
        "entity_ids": ["dl-001"],
        "relationship_ids": ["rel-001"],
        "embedding": [0.2] * 768
    })
    store.add_chunk({
        "chunk_id": "chunk-003",
        "content": "Artificial intelligence encompasses many techniques.",
        "source": "doc3.pdf",
        "entity_ids": ["ai-001"],
        "relationship_ids": ["rel-002"],
        "embedding": [0.5] * 768
    })

    return store
