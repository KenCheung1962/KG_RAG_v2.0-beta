"""
T036 Phase 4 - Configuration Module
FastAPI configuration for Unified RAG Knowledge Graph API
"""

from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Unified RAG Knowledge Graph API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # API
    api_prefix: str = "/api/v1"
    docs_url: str = "/docs"
    openapi_url: str = "/openapi.json"
    
    # LightRAG Storage Paths
    lightrag_storage_path: str = "/Users/ken/clawd/lightrag_storage_merged"
    
    # Security
    secret_key: str = "change-this-in-production!"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_hosts: list = ["*"]
    
    # Database
    database_url: Optional[str] = None

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
