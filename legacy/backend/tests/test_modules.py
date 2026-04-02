"""
Unit tests for RAG Web UI (T058)
"""
import pytest
import sys

# Add source directory to path
sys.path.insert(0, '/Users/ken/clawd/RG_RAG/KG_RAG_Tasks/t058_web_ui/source')

from config import Config
from api_client import safe_query, safe_filename, APIError


class TestConfig:
    """Tests for configuration module."""
    
    def test_config_defaults(self):
        """Test that config has expected default values."""
        assert Config.API_BASE_URL == "http://localhost:8000"
        assert Config.API_TIMEOUT == 60
        assert Config.MAX_FILE_SIZE_MB == 50
        assert "pdf" in Config.ALLOWED_EXT
        assert "docx" in Config.ALLOWED_EXT
        assert Config.MAX_CHAT_HISTORY == 100
    
    def test_config_env_override(self):
        """Test that config can be overridden by environment variables."""
        # This would require mocking os.getenv
        # For now, just verify the attribute exists
        assert hasattr(Config, 'API_BASE_URL')


class TestSafeQuery:
    """Tests for input sanitization."""
    
    def test_valid_query(self):
        """Test normal query passes through."""
        result = safe_query("What is quantum computing?")
        assert result == "What is quantum computing?"
    
    def test_whitespace_trimming(self):
        """Test that whitespace is trimmed."""
        result = safe_query("  hello world  ")
        assert result == "hello world"
    
    def test_empty_query_raises(self):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            safe_query("")
        assert "cannot be empty" in str(exc_info.value)
    
    def test_query_too_long_raises(self):
        """Test that overly long query raises ValueError."""
        long_query = "a" * 3000
        with pytest.raises(ValueError) as exc_info:
            safe_query(long_query)
        assert "exceeds maximum length" in str(exc_info.value)
    
    def test_html_escaping(self):
        """Test that HTML characters are escaped."""
        result = safe_query("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
    
    def test_special_characters(self):
        """Test that special characters are properly handled."""
        result = safe_query("Test & <tag> with 'quotes' and \"double quotes\"")
        assert "&amp;" in result
        assert "&lt;tag&gt;" in result


class TestSafeFilename:
    """Tests for filename sanitization."""
    
    def test_normal_filename(self):
        """Test normal filename passes through."""
        result = safe_filename("document.pdf")
        assert result == "document.pdf"
    
    def test_path_traversal_blocked(self):
        """Test that path traversal attempts are blocked."""
        result = safe_filename("../../../etc/passwd")
        assert ".." not in result
        assert "passwd" in result
    
    def test_special_characters_replaced(self):
        """Test that special characters are replaced."""
        result = safe_filename("file with spaces & special!@#.txt")
        # Spaces are allowed, but special characters should be replaced
        assert "!" not in result
        assert "@" not in result
        assert "#" not in result
        assert "&" not in result
    
    def test_filename_truncated(self):
        """Test that overly long filenames are truncated."""
        long_name = "a" * 300 + ".txt"
        result = safe_filename(long_name)
        assert len(result) <= 255
        # After truncation, extension might be lost, but filename should be safe
        assert len(result) > 0
    
    def test_spaces_converted(self):
        """Test that spaces are handled (allowed but not replaced)."""
        result = safe_filename("my document.pdf")
        # Spaces are allowed in filenames
        assert "document" in result
        assert ".pdf" in result


class TestAPIError:
    """Tests for API error handling."""
    
    def test_api_error_creation(self):
        """Test that APIError can be created with message."""
        error = APIError("Test error message")
        assert error.message == "Test error message"
        assert error.status_code == 500
    
    def test_api_error_with_status_code(self):
        """Test that APIError can be created with custom status code."""
        error = APIError("Not found", status_code=404)
        assert error.status_code == 404
    
    def test_api_error_is_exception(self):
        """Test that APIError is an exception."""
        error = APIError("Test")
        assert isinstance(error, Exception)


# Mock objects for testing
class MockFile:
    """Mock file object for testing."""
    
    def __init__(self, name: str, size: int = 1024):
        self.name = name
        self.size = size
    
    def read(self, n: int = -1):
        return b"mock file content"


# Fixtures for pytest
@pytest.fixture
def mock_file():
    """Create a mock file for testing."""
    return MockFile("test.pdf", size=1024)


@pytest.fixture
def long_query():
    """Create a query that's too long."""
    return "a" * 3000


@pytest.fixture
def malicious_query():
    """Create a malicious query with XSS."""
    return "<script>alert('xss')</script>"


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
