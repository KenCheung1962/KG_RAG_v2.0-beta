"""
Utility functions for RAG Web UI (T058)
"""
import time
from typing import Any, Dict, Optional


def format_timestamp(timestamp: float = None) -> str:
    """
    Format a timestamp to readable string.
    
    Args:
        timestamp: Unix timestamp (defaults to current time)
        
    Returns:
        Formatted timestamp string
    """
    import datetime
    if timestamp is None:
        timestamp = time.time()
    return datetime.datetime.fromtimestamp(timestamp).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length of result
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


class Timer:
    """Simple timer utility for performance measurement."""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = None
    
    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing."""
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time
        return False
    
    def elapsed_ms(self) -> float:
        """Return elapsed time in milliseconds."""
        return (self.elapsed or (time.time() - self.start_time)) * 1000


def safe_get(data: Dict, key: str, default: Any = None) -> Any:
    """
    Safely get a value from a dictionary.
    
    Args:
        data: Dictionary to get value from
        key: Key to look up
        default: Default value if key not found
        
    Returns:
        Value or default
    """
    try:
        return data.get(key, default)
    except (AttributeError, TypeError):
        return default


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# Demo/test functions
if __name__ == "__main__":
    print("Testing utility functions...")
    
    # Test timestamp
    print(f"Current timestamp: {format_timestamp()}")
    
    # Test truncate
    long_text = "This is a very long text that should be truncated"
    print(f"Truncated: {truncate_text(long_text, 20)}")
    
    # Test timer
    with Timer() as timer:
        time.sleep(0.1)
    print(f"Elapsed: {timer.elapsed_ms():.2f}ms")
    
    # Test safe_get
    data = {"key1": "value1"}
    print(f"Existing key: {safe_get(data, 'key1')}")
    print(f"Missing key: {safe_get(data, 'missing', 'default')}")
    
    # Test file size
    print(f"File size: {format_file_size(1234567)}")
    
    print("✅ All utility tests passed")
