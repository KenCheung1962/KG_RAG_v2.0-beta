"""
RAG Web UI Source Package (T058)

This package contains the core modules for the RAG Web UI application.
"""

__version__ = "1.0.0"
__author__ = "Kenny"

from .config import Config, config
from .api_client import APIClient, APIError, safe_query, safe_filename
from .chat_module import render_chat_interface, process_query
from .upload_module import render_document_upload, validate_file_type
from .utils import format_timestamp, truncate_text, Timer

__all__ = [
    # Config
    "Config",
    "config",
    
    # API Client
    "APIClient",
    "APIError",
    "safe_query",
    "safe_filename",
    
    # Chat Module
    "render_chat_interface",
    "process_query",
    
    # Upload Module
    "render_document_upload",
    "validate_file_type",
    
    # Utils
    "format_timestamp",
    "truncate_text",
    "Timer",
]
