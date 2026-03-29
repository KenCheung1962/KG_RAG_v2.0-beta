"""
Configuration for RAG Web UI (T058)
Updated for Ollama/nomic-embed-text direct integration
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration settings for the RAG Web UI."""
    
    # API Configuration (KG RAG API on port 8001)
    # This is the unified indexing API (now using Ollama for embeddings internally)
    # NOTE: Base URL is the service root. The /api prefix is added by api_client.py
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8001")
    
    # API path prefix - routes are mounted at /api but KG RAG defines /api/v1/*
    # so full paths are /api/api/v1/*
    API_PREFIX: str = "/api/api"
    API_TIMEOUT: int = 60
    
    # Ollama Configuration (for direct embedding calls)
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    OLLAMA_EMBED_MODEL: str = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    OLLAMA_EMBED_DIM: int = 768  # nomic-embed-text produces 768-dim embeddings
    
    # Use Ollama directly for embeddings (vs API at port 8001)
    # Set to "true" to use Ollama directly, "false" to use API for embeddings
    USE_OLLAMA_DIRECT: bool = os.getenv("USE_OLLAMA_DIRECT", "true").lower() == "true"
    
    # Mock API Configuration (for demo/testing without T036)
    USE_MOCK_API: bool = os.getenv("USE_MOCK_API", "false").lower() == "true"
    MOCK_DELAY: float = float(os.getenv("MOCK_DELAY", "1.0"))
    
    # File Upload Configuration
    MAX_FILE_SIZE_MB: int = 200
    ALLOWED_EXT: tuple = ("pdf", "docx", "txt", "html")
    
    # UI Configuration
    PAGE_TITLE: str = "RAG Assistant"
    PAGE_ICON: str = "🤖"
    
    # Chat Configuration
    MAX_CHAT_HISTORY: int = 100
    MAX_QUERY_LENGTH: int = 2000
    
    # Security Configuration
    BLOCKED_EXTENSIONS: tuple = (".exe", ".bat", ".sh", ".py", ".js", ".html", ".css")


# Global config instance
config = Config()
