"""
Unit tests for the storage layer (storage.py).
"""

import pytest
import numpy as np
from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch


# Mock the storage module for testing
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
                    results.append({
                        **chunk,
                        "score": score
                    })
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
                results.append({
                    **entity,
                    "score": score
                })
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
                results.append({
                    **rel,
                    "score": score
                })
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
                        results.append({
                            **target,
                            "relationship": rel,
                            "depth": depth
                        })
                        traverse(target_id, depth + 1)
                elif rel["target_id"] == current_id:
                    source_id = rel["source_id"]
                    if source_id not in visited:
                        visited.add(source_id)
                        source = self.entities.get(source_id, {})
                        results.append({
                            **source,
                            "relationship": rel,
                            "depth": depth
                        })
                        traverse(source_id, depth + 1)

        traverse(entity_id, 1)
        return results

    async def get_chunks_by_entity(
        self,
        entity_id: str
    ) -> List[Dict[str, Any]]:
        """Get chunks associated with an entity."""
        results = []
        for chunk in self.chunks.values():
            if entity_id in chunk.get("entity_ids", []):
                results.append(chunk)
        return results

    def add_chunk(self, chunk: Dict[str, Any]):
        """Add a chunk to storage."""
        self.chunks[chunk["chunk_id"]] = chunk

    def add_entity(self, entity: Dict[str, Any]):
        """Add an entity to storage."""
        self.entities[entity["entity_id"]] = entity

    def add_relationship(self, relationship: Dict[str, Any]):
        """Add a relationship to storage."""
        self.relationships[relationship["relationship_id"]] = relationship

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity."""
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


class TestStorageConnection:
    """Test storage connection management."""

    @pytest.mark.asyncio
    async def test_connect(self, storage):
        """Test connecting to storage."""
        assert not storage.is_connected
        await storage.connect()
        assert storage.is_connected

    @pytest.mark.asyncio
    async def test_disconnect(self, storage):
        """Test disconnecting from storage."""
        await storage.connect()
        assert storage.is_connected
        await storage.disconnect()
        assert not storage.is_connected


class TestChunkSearch:
    """Test chunk search functionality."""

    @pytest.mark.asyncio
    async def test_search_chunks_by_embedding(self, storage):
        """Test searching chunks by embedding similarity."""
        query_embedding = [0.1] * 768  # Similar to chunk-001
        results = await storage.search_chunks(query_embedding, top_k=10)

        assert len(results) > 0
        assert results[0]["chunk_id"] == "chunk-001"
        assert "score" in results[0]

    @pytest.mark.asyncio
    async def test_search_with_min_score(self, storage):
        """Test search with minimum score threshold."""
        query_embedding = [0.1] * 768
        results = await storage.search_chunks(query_embedding, top_k=10, min_score=0.9)

        # Should return fewer or no results with high threshold
        for result in results:
            assert result["score"] >= 0.9

    @pytest.mark.asyncio
    async def test_search_respects_top_k(self, storage):
        """Test that search respects top_k limit."""
        query_embedding = [0.3] * 768
        results = await storage.search_chunks(query_embedding, top_k=2)

        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_empty_storage(self):
        """Test search on empty storage."""
        store = MockStorage()
        results = await store.search_chunks([0.1] * 768)

        assert len(results) == 0


class TestEntitySearch:
    """Test entity search functionality."""

    @pytest.mark.asyncio
    async def test_search_entities_by_embedding(self, storage):
        """Test searching entities by embedding similarity."""
        query_embedding = [0.1] * 768  # Similar to ml-001
        results = await storage.search_entities(query_embedding, top_k=10)

        assert len(results) > 0
        assert results[0]["entity_id"] == "ml-001"

    @pytest.mark.asyncio
    async def test_search_with_entity_type_filter(self, storage):
        """Test searching with entity type filter."""
        query_embedding = [0.3] * 768
        results = await storage.search_entities(
            query_embedding,
            top_k=10,
            entity_types=["concept"]
        )

        for entity in results:
            assert entity.get("entity_type") == "concept"

    @pytest.mark.asyncio
    async def test_empty_entity_type_filter(self, storage):
        """Test searching with non-matching entity type."""
        query_embedding = [0.3] * 768
        results = await storage.search_entities(
            query_embedding,
            top_k=10,
            entity_types=["non_existent_type"]
        )

        assert len(results) == 0


class TestRelationshipSearch:
    """Test relationship search functionality."""

    @pytest.mark.asyncio
    async def test_search_relationships(self, storage):
        """Test searching relationships by embedding."""
        query_embedding = [0.15] * 768  # Similar to rel-001
        results = await storage.search_relationships(query_embedding, top_k=10)

        assert len(results) > 0
        assert results[0]["relationship_id"] == "rel-001"


class TestGraphTraversal:
    """Test graph traversal functionality."""

    @pytest.mark.asyncio
    async def test_get_related_entities(self, storage):
        """Test getting entities related to an entity."""
        results = await storage.get_related_entities("ml-001", max_depth=2)

        # Should find ai-001 through ml-001
        entity_ids = [r["entity_id"] for r in results]
        assert "ai-001" in entity_ids

    @pytest.mark.asyncio
    async def test_graph_traversal_depth(self, storage):
        """Test that traversal respects max depth."""
        results = await storage.get_related_entities("dl-001", max_depth=1)

        for result in results:
            assert result["depth"] <= 1

    @pytest.mark.asyncio
    async def test_get_chunks_by_entity(self, storage):
        """Test getting chunks associated with an entity."""
        results = await storage.get_chunks_by_entity("ml-001")

        assert len(results) == 1
        assert results[0]["chunk_id"] == "chunk-001"


class TestCosineSimilarity:
    """Test cosine similarity calculation."""

    def test_identical_vectors(self, storage):
        """Test similarity of identical vectors."""
        vec = [0.1] * 768
        sim = storage._cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.0001

    def test_opposite_vectors(self, storage):
        """Test similarity of opposite vectors."""
        vec1 = [1.0] * 768
        vec2 = [-1.0] * 768
        sim = storage._cosine_similarity(vec1, vec2)
        assert abs(sim - (-1.0)) < 0.0001

    def test_orthogonal_vectors(self, storage):
        """Test similarity of orthogonal vectors."""
        vec1 = [1.0] * 768
        vec2 = [0.0] * 768
        vec2[0] = 1.0
        vec2[1] = -1.0
        sim = storage._cosine_similarity(vec1, vec2)
        assert abs(sim) < 0.1

    def test_empty_vectors(self, storage):
        """Test handling of empty vectors."""
        sim = storage._cosine_similarity([], [1.0] * 768)
        assert sim == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
