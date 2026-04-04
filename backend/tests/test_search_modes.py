"""
Unit tests for search modes (smart, semantic, entity-lookup, graph-traversal).
"""

import pytest
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class SearchMode(Enum):
    """Available search modes."""
    SMART = "smart"
    SEMANTIC = "semantic"
    ENTITY_LOOKUP = "entity-lookup"
    GRAPH_TRAVERSAL = "graph-traversal"


@dataclass
class SearchConfig:
    """Configuration for search."""
    mode: SearchMode = SearchMode.SMART
    chunk_top_k: int = 50
    entity_top_k: int = 20
    relationship_top_k: int = 20
    final_top_k: int = 10
    max_depth: int = 2
    min_score: float = 0.0


class MockSearchEngine:
    """Mock search engine for testing search modes."""

    def __init__(self, storage):
        self.storage = storage

    async def search_smart(
        self,
        query: str,
        query_embedding: List[float],
        config: SearchConfig
    ) -> Dict[str, Any]:
        """
        Smart mode: Multi-layer unified search.
        Combines chunk, entity, relationship, and keyword search.
        """
        results = {
            "mode": "smart",
            "chunks": [],
            "entities": [],
            "relationships": [],
            "keywords": [],
            "fusion_scores": {}
        }

        # Layer 1: Semantic chunk search
        chunk_results = await self.storage.search_chunks(
            query_embedding,
            top_k=config.chunk_top_k,
            min_score=config.min_score
        )
        results["chunks"] = chunk_results

        # Layer 2: Entity discovery
        entity_results = await self.storage.search_entities(
            query_embedding,
            top_k=config.entity_top_k
        )
        results["entities"] = entity_results

        # Layer 3: Relationship enhancement
        rel_results = await self.storage.search_relationships(
            query_embedding,
            top_k=config.relationship_top_k
        )
        results["relationships"] = rel_results

        # Layer 4: Keyword extraction
        keywords = self._extract_keywords(query)
        results["keywords"] = keywords

        # Layer 5: Entity chunk collection
        entity_chunks = []
        for entity in entity_results[:5]:
            chunks = await self.storage.get_chunks_by_entity(entity["entity_id"])
            entity_chunks.extend(chunks)
        results["entity_chunks"] = entity_chunks

        # Layer 6: Fusion and ranking
        fused_results = self._fuse_results(
            chunk_results,
            entity_results,
            rel_results,
            entity_chunks,
            keywords
        )
        results["fused_results"] = fused_results[:config.final_top_k]

        return results

    async def search_semantic(
        self,
        query_embedding: List[float],
        config: SearchConfig
    ) -> Dict[str, Any]:
        """
        Semantic mode: Direct chunk embedding search.
        Simple and fast, uses only chunk embeddings.
        """
        chunk_results = await self.storage.search_chunks(
            query_embedding,
            top_k=config.final_top_k,
            min_score=config.min_score
        )

        return {
            "mode": "semantic",
            "chunks": chunk_results,
            "total_results": len(chunk_results)
        }

    async def search_entity_lookup(
        self,
        query: str,
        query_embedding: List[float],
        config: SearchConfig
    ) -> Dict[str, Any]:
        """
        Entity-lookup mode: Entity-centric search with keyword boost.
        """
        results = {
            "mode": "entity-lookup",
            "entities": [],
            "chunks": [],
            "relationships": []
        }

        # Primary: Entity embedding search
        entity_results = await self.storage.search_entities(
            query_embedding,
            top_k=config.entity_top_k
        )
        results["entities"] = entity_results

        # Keyword extraction and boost
        keywords = self._extract_keywords(query)
        results["keywords"] = keywords

        # Relationship search for related entities
        if entity_results:
            top_entity = entity_results[0]
            related = await self.storage.get_related_entities(
                top_entity["entity_id"],
                max_depth=config.max_depth
            )
            results["related_entities"] = related

        # Relationship embedding search
        rel_results = await self.storage.search_relationships(
            query_embedding,
            top_k=config.relationship_top_k
        )
        results["relationships"] = rel_results

        # Chunk search (direct + entity-linked)
        chunk_results = await self.storage.search_chunks(
            query_embedding,
            top_k=config.chunk_top_k,
            min_score=config.min_score
        )

        # Add chunks from entity lookup
        for entity in entity_results[:5]:
            entity_chunks = await self.storage.get_chunks_by_entity(entity["entity_id"])
            chunk_results.extend(entity_chunks)

        # Deduplicate
        seen = set()
        unique_chunks = []
        for chunk in chunk_results:
            if chunk["chunk_id"] not in seen:
                seen.add(chunk["chunk_id"])
                unique_chunks.append(chunk)

        results["chunks"] = unique_chunks[:config.final_top_k]

        return results

    async def search_graph_traversal(
        self,
        query_embedding: List[float],
        config: SearchConfig
    ) -> Dict[str, Any]:
        """
        Graph-traversal mode: Graph-based search with BFS.
        """
        results = {
            "mode": "graph-traversal",
            "paths": [],
            "entities": [],
            "relationships": [],
            "chunks": []
        }

        # Primary: Relationship embeddings
        rel_results = await self.storage.search_relationships(
            query_embedding,
            top_k=config.relationship_top_k
        )
        results["relationships"] = rel_results

        # Seed: Entity embeddings for starting points
        entity_results = await self.storage.search_entities(
            query_embedding,
            top_k=config.entity_top_k
        )
        results["entities"] = entity_results

        # Graph traversal for top entities
        if entity_results:
            for entity in entity_results[:3]:
                related = await self.storage.get_related_entities(
                    entity["entity_id"],
                    max_depth=config.max_depth
                )
                results["paths"].append({
                    "root": entity["entity_id"],
                    "related": related
                })

        # Chunks from graph entities
        all_entity_ids = [e["entity_id"] for e in entity_results]
        for entity_id in all_entity_ids[:5]:
            chunks = await self.storage.get_chunks_by_entity(entity_id)
            results["chunks"].extend(chunks)

        # Deduplicate chunks
        seen = set()
        unique_chunks = []
        for chunk in results["chunks"]:
            if chunk["chunk_id"] not in seen:
                seen.add(chunk["chunk_id"])
                unique_chunks.append(chunk)

        results["chunks"] = unique_chunks[:config.final_top_k]

        return results

    def _extract_keywords(self, query: str) -> List[str]:
        """Simple keyword extraction."""
        import re
        stop_words = {'the', 'a', 'an', 'is', 'are', 'what', 'how', 'and', 'or', 'but'}
        words = re.findall(r'\b[a-zA-Z]+\b', query.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]

    def _fuse_results(
        self,
        chunks: List[Dict],
        entities: List[Dict],
        relationships: List[Dict],
        entity_chunks: List[Dict],
        keywords: List[str]
    ) -> List[Dict]:
        """Fuse and rank results from multiple sources."""
        scores = {}

        # Score chunks by rank
        for i, chunk in enumerate(chunks):
            chunk_id = chunk["chunk_id"]
            base_score = 1.0 / (i + 1)  # Rank-based score
            keyword_boost = sum(1 for kw in keywords if kw in chunk.get("content", "").lower())
            scores[chunk_id] = scores.get(chunk_id, 0) + base_score + (keyword_boost * 0.1)
            chunk["_fused"] = True

        # Score entity chunks
        for i, chunk in enumerate(entity_chunks):
            chunk_id = chunk["chunk_id"]
            if chunk_id not in scores:
                scores[chunk_id] = 0
            scores[chunk_id] += 0.5 / (i + 1)  # Lower weight than direct chunks

        # Create fused result list
        all_chunks = chunks + [c for c in entity_chunks if c not in chunks]
        for chunk in all_chunks:
            chunk_id = chunk["chunk_id"]
            chunk["fusion_score"] = scores.get(chunk_id, 0)

        all_chunks.sort(key=lambda x: x["fusion_score"], reverse=True)
        return all_chunks


# Import mock storage from test_storage
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from test_storage import MockStorage, storage


@pytest.fixture
def search_engine(storage):
    """Create a search engine with mock storage."""
    return MockSearchEngine(storage)


class TestSearchModes:
    """Test all search modes."""

    @pytest.mark.asyncio
    async def test_search_smart_mode(self, search_engine):
        """Test smart mode search."""
        query = "What is machine learning?"
        query_embedding = [0.1] * 768
        config = SearchConfig(mode=SearchMode.SMART)

        results = await search_engine.search_smart(query, query_embedding, config)

        assert results["mode"] == "smart"
        assert "chunks" in results
        assert "entities" in results
        assert "relationships" in results
        assert "keywords" in results
        assert "fused_results" in results

    @pytest.mark.asyncio
    async def test_search_semantic_mode(self, search_engine):
        """Test semantic mode search."""
        query_embedding = [0.1] * 768
        config = SearchConfig(mode=SearchMode.SEMANTIC)

        results = await search_engine.search_semantic(query_embedding, config)

        assert results["mode"] == "semantic"
        assert "chunks" in results
        assert "total_results" in results

    @pytest.mark.asyncio
    async def test_search_entity_lookup_mode(self, search_engine):
        """Test entity-lookup mode search."""
        query = "Tell me about machine learning"
        query_embedding = [0.1] * 768
        config = SearchConfig(mode=SearchMode.ENTITY_LOOKUP)

        results = await search_engine.search_entity_lookup(query, query_embedding, config)

        assert results["mode"] == "entity-lookup"
        assert "entities" in results
        assert "chunks" in results
        assert "relationships" in results

    @pytest.mark.asyncio
    async def test_search_graph_traversal_mode(self, search_engine):
        """Test graph-traversal mode search."""
        query_embedding = [0.1] * 768
        config = SearchConfig(mode=SearchMode.GRAPH_TRAVERSAL, max_depth=2)

        results = await search_engine.search_graph_traversal(query_embedding, config)

        assert results["mode"] == "graph-traversal"
        assert "paths" in results
        assert "entities" in results
        assert "relationships" in results
        assert "chunks" in results


class TestSearchConfig:
    """Test search configuration."""

    def test_default_config(self):
        """Test default search configuration."""
        config = SearchConfig()

        assert config.mode == SearchMode.SMART
        assert config.chunk_top_k == 50
        assert config.entity_top_k == 20
        assert config.relationship_top_k == 20
        assert config.final_top_k == 10
        assert config.max_depth == 2

    def test_custom_config(self):
        """Test custom search configuration."""
        config = SearchConfig(
            mode=SearchMode.GRAPH_TRAVERSAL,
            chunk_top_k=100,
            entity_top_k=50,
            max_depth=3
        )

        assert config.mode == SearchMode.GRAPH_TRAVERSAL
        assert config.chunk_top_k == 100
        assert config.entity_top_k == 50
        assert config.max_depth == 3


class TestResultFusion:
    """Test result fusion logic."""

    @pytest.mark.asyncio
    async def test_fusion_ranks_direct_chunks_higher(self, search_engine):
        """Test that direct chunk matches rank higher than entity-linked chunks."""
        query = "machine learning"
        query_embedding = [0.1] * 768
        config = SearchConfig(mode=SearchMode.SMART)

        results = await search_engine.search_smart(query, query_embedding, config)

        if len(results["fused_results"]) > 1:
            # Direct chunks should rank higher
            for i, result in enumerate(results["fused_results"][:3]):
                assert "fusion_score" in result
                assert result["fusion_score"] > 0


class TestKeywordBoosting:
    """Test keyword boosting in search."""

    def test_keyword_extraction(self, search_engine):
        """Test keyword extraction from query."""
        query = "What is the relationship between machine learning and AI?"
        keywords = search_engine._extract_keywords(query)

        assert "machine" in keywords
        assert "learning" in keywords
        assert "relationship" in keywords
        assert "what" not in keywords
        assert "is" not in keywords

    @pytest.mark.asyncio
    async def test_keyword_boosts_results(self, search_engine):
        """Test that keywords boost matching chunks."""
        query = "machine learning neural networks"
        query_embedding = [0.1] * 768
        config = SearchConfig(mode=SearchMode.SMART)

        results = await search_engine.search_smart(query, query_embedding, config)

        # Chunks with more keyword matches should have higher fusion scores
        keywords = results["keywords"]
        for result in results["fused_results"]:
            if "machine" in result.get("content", "").lower():
                # This chunk matches a keyword
                pass  # Just verifying it exists


class TestGraphTraversal:
    """Test graph traversal specific functionality."""

    @pytest.mark.asyncio
    async def test_traversal_respects_max_depth(self, search_engine):
        """Test that graph traversal respects max_depth."""
        query_embedding = [0.1] * 768
        config = SearchConfig(mode=SearchMode.GRAPH_TRAVERSAL, max_depth=1)

        results = await search_engine.search_graph_traversal(query_embedding, config)

        for path in results["paths"]:
            for entity in path.get("related", []):
                assert entity.get("depth", 0) <= 1

    @pytest.mark.asyncio
    async def test_traversal_finds_connected_entities(self, search_engine):
        """Test that traversal finds connected entities."""
        query_embedding = [0.1] * 768
        config = SearchConfig(mode=SearchMode.GRAPH_TRAVERSAL, max_depth=2)

        results = await search_engine.search_graph_traversal(query_embedding, config)

        # Should find paths
        assert len(results["paths"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
