"""
Ollama Client for Web UI - Direct embedding integration
Calls Ollama directly for text embeddings (nomic-embed-text)
"""
import os
import httpx
import asyncio
from typing import List, Optional
import numpy as np


class OllamaClient:
    """Client for Ollama embedding service."""
    
    def __init__(
        self, 
        host: str = None,
        model: str = None
    ):
        """
        Initialize Ollama client.
        
        Args:
            host: Ollama host URL (default: from OLLAMA_HOST env var or http://127.0.0.1:11434)
            model: Model name (default: from OLLAMA_EMBED_MODEL env var or nomic-embed-text)
        """
        self.host = (host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip('/')
        self.model = model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
        self.dimension = 768  # nomic-embed-text dimension
    
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (768 dimensions each)
        """
        if not texts:
            return []
        
        embeddings = []
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in texts:
                try:
                    response = await client.post(
                        f"{self.host}/api/embeddings",
                        json={
                            "model": self.model,
                            "prompt": text
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        embedding = result.get("embedding", [])
                        embeddings.append(embedding)
                    else:
                        print(f"Ollama error: {response.status_code}")
                        embeddings.append([0.0] * self.dimension)
                except Exception as e:
                    print(f"Error calling Ollama: {e}")
                    embeddings.append([0.0] * self.dimension)
        
        return embeddings
    
    def embed_sync(self, texts: List[str]) -> List[List[float]]:
        """Synchronous version of embed."""
        return asyncio.run(self.embed(texts))
    
    async def health_check(self) -> dict:
        """Check Ollama health and model availability."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.host}/api/tags")
                
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_available = any(
                        m.get("name") == self.model or 
                        m.get("name", "").startswith(self.model)
                        for m in models
                    )
                    
                    return {
                        "status": "healthy" if model_available else "model_not_found",
                        "host": self.host,
                        "model": self.model,
                        "model_available": model_available,
                        "available_models": [m.get("name") for m in models]
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status_code}",
                        "host": self.host
                    }
        except Exception as e:
            return {
                "status": "unreachable",
                "error": str(e),
                "host": self.host
            }
    
    def similarity(self, embed1: List[float], embed2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        a = np.array(embed1)
        b = np.array(embed2)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(np.dot(a, b) / (norm_a * norm_b))


# Global client instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create global Ollama client instance."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


def reset_ollama_client():
    """Reset the global client (useful for testing)."""
    global _ollama_client
    _ollama_client = None


# Example usage
if __name__ == "__main__":
    async def test():
        client = OllamaClient()
        
        # Health check
        print("Health check:")
        health = await client.health_check()
        print(f"  Status: {health}")
        
        # Test embedding
        texts = ["Hello world", "Machine learning"]
        print(f"\nEmbedding texts: {texts}")
        embeddings = await client.embed(texts)
        
        print(f"Generated {len(embeddings)} embeddings")
        print(f"Dimension: {len(embeddings[0])}")
        
        # Similarity
        if len(embeddings) >= 2:
            sim = client.similarity(embeddings[0], embeddings[1])
            print(f"Similarity: {sim:.4f}")
    
    asyncio.run(test())
