"""
Mock API Client for T058 RAG Web UI Testing

This module provides a mock implementation of the T036 API
for testing the UI without a running backend.
"""

import time
import random
from typing import Optional


class MockAPIClient:
    """
    Mock API Client that simulates T036 FastAPI responses.
    
    Useful for:
    - Demoing the UI without backend
    - Testing UI components
    - Development without T036
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", mock_delay: float = 1.0):
        self.base_url = base_url
        self.mock_delay = mock_delay
        self.mock_mode = True
        
        # Sample knowledge base for demo
        self.sample_responses = {
            "what is rag": "RAG (Retrieval-Augmented Generation) is a technique that enhances LLM responses by fetching relevant information from a knowledge base. It combines the generative power of AI with accurate retrieval of context.",
            "what is knowledge graph": "A Knowledge Graph is a structured representation of knowledge consisting of entities, relationships, and attributes. It enables semantic search and reasoning over complex data.",
            "how does lightrag work": "LightRAG is a lightweight RAG system that combines knowledge graphs with vector retrieval. It supports hybrid, local, and global search modes for optimal results.",
            "what is embedding": "Embeddings are numerical representations of text that capture semantic meaning. They enable similarity search and are fundamental to RAG systems.",
            "default": "I don't have specific information about that in my knowledge base. Try uploading relevant documents or rephrasing your question."
        }
    
    def query(self, query: str, mode: str = "hybrid", top_k: int = 10) -> dict:
        """
        Simulate a query response.
        
        Args:
            query: User's question
            mode: Search mode (local/global/hybrid)
            top_k: Number of results to return
            
        Returns:
            Mock response dictionary
        """
        # Simulate network delay
        time.sleep(self.mock_delay)
        
        # Find matching response
        query_lower = query.lower()
        response_text = self.sample_responses.get("default")
        
        for key, value in self.sample_responses.items():
            if key in query_lower:
                response_text = value
                break
        
        # Generate mock sources
        sources = [
            {
                "content": f"Source document {i+1} containing relevant information about the topic.",
                "score": random.uniform(0.7, 0.95),
                "doc_id": f"doc_{i+1:03d}"
            }
            for i in range(min(3, top_k))
        ]
        
        return {
            "response": response_text,
            "sources": sources,
            "confidence": sum(s["score"] for s in sources) / len(sources) if sources else 0.0,
            "query": query,
            "mode": mode,
            "top_k": top_k,
            "results_count": len(sources),
            "cache_hit": False,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    
    def health_check(self) -> bool:
        """Simulate health check."""
        time.sleep(0.1)
        return True
    
    def get_stats(self) -> dict:
        """Get mock statistics."""
        time.sleep(0.1)
        return {
            "total_documents": 42,
            "total_chunks": 156,
            "total_entities": 512,
            "total_relationships": 1024,
            "index_size_mb": 128.5,
            "status": "healthy"
        }
    
    def get_entities(self, limit: int = 10) -> list:
        """Get mock entities."""
        time.sleep(0.1)
        return [
            {"id": f"entity_{i}", "name": f"Entity {i}", "type": "Concept"}
            for i in range(limit)
        ]
    
    def search_entities(self, query: str, limit: int = 10) -> list:
        """Search mock entities."""
        time.sleep(0.1)
        return [
            {"id": f"result_{i}", "name": f"Result {i} for {query}", "score": 0.9 - (i * 0.1)}
            for i in range(min(limit, 5))
        ]
    
    def get_relationships(self, entity_id: str) -> list:
        """Get mock relationships."""
        time.sleep(0.1)
        return [
            {"type": "related_to", "target": "Another Entity", "score": 0.85}
        ]


def demo():
    """Demo function for testing."""
    client = MockAPIClient()
    
    print("\n1. Testing query...")
    result = client.query("What is RAG?")
    print(f"Response: {result['response'][:80]}...")
    print(f"Confidence: {result['confidence']:.2%}")
    
    print("\n✅ Mock client working!")


if __name__ == "__main__":
    demo()
