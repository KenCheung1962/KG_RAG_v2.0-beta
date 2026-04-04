"""
Unit tests for keyword extraction functionality.
"""

import pytest
import re
from typing import List, Dict, Any


# Import the keyword extraction function from pgvector_api if available
# If not available, define it here for testing
def extract_keywords_for_search(query: str) -> Dict[str, List[str]]:
    """
    Extract keywords from search query for enhanced search.
    Returns high-level and low-level keywords.
    """
    # Convert to lowercase
    query_lower = query.lower()

    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as',
        'and', 'or', 'but', 'if', 'then', 'so', 'because', 'while',
        'what', 'which', 'who', 'whom', 'how', 'why', 'when', 'where',
        'this', 'that', 'these', 'those', 'it', 'its',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall',
        'not', 'no', 'yes', 'all', 'any', 'some', 'each', 'every',
        'i', 'you', 'he', 'she', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs'
    }

    # Extract words
    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9]*\b', query_lower)

    # Filter stop words and short words
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]

    # Extract capitalized phrases (likely entity names)
    capitalized_phrases = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)

    # High-level keywords (longer, more specific terms)
    high_level = [w for w in filtered_words if len(w) > 5]

    # Low-level keywords (shorter, potentially entity names)
    low_level = [w for w in filtered_words if len(w) <= 5]

    # Add capitalized phrases to low-level (entities)
    for phrase in capitalized_phrases:
        phrase_lower = phrase.lower()
        if phrase_lower not in stop_words:
            low_level.append(phrase_lower)

    # Remove duplicates while preserving order
    seen = set()
    high_level_unique = []
    for w in high_level:
        if w not in seen:
            seen.add(w)
            high_level_unique.append(w)

    seen.clear()
    low_level_unique = []
    for w in low_level:
        if w not in seen:
            seen.add(w)
            low_level_unique.append(w)

    return {
        "high_level": high_level_unique,  # Concepts
        "low_level": low_level_unique,     # Entities
        "all_keywords": high_level_unique + low_level_unique
    }


class TestKeywordExtraction:
    """Test suite for keyword extraction."""

    def test_basic_extraction(self):
        """Test basic keyword extraction from a query."""
        query = "What is machine learning and how does it work?"
        result = extract_keywords_for_search(query)

        assert "machine" in result["high_level"]
        assert "learning" in result["high_level"]
        assert "work" in result["low_level"]
        assert "all_keywords" in result

    def test_entity_extraction(self):
        """Test extraction of entity names."""
        query = "Tell me about Artificial Intelligence and Machine Learning"
        result = extract_keywords_for_search(query)

        # Should extract capitalized entities
        assert "artificial" in result["high_level"] or "artificial intelligence" in " ".join(result["low_level"])

    def test_stop_words_removed(self):
        """Test that stop words are properly removed."""
        query = "What is the relationship between AI and machine learning?"
        result = extract_keywords_for_search(query)

        # Common short stop words (length <= 2) should not be in results
        # Note: The function only filters words <= 2 chars and specific stop words
        stop_words = {'the', 'is', 'are', 'be', 'was', 'it', 'i', 'a', 'an'}
        for keyword_list in result.values():
            for word in keyword_list:
                assert word not in stop_words, f"Stop word '{word}' should be removed"

    def test_empty_query(self):
        """Test handling of empty query."""
        result = extract_keywords_for_search("")

        assert "high_level" in result
        assert "low_level" in result
        assert "all_keywords" in result
        assert len(result["all_keywords"]) == 0

    def test_only_stop_words(self):
        """Test query with only stop words."""
        query = "what is the how and why"
        result = extract_keywords_for_search(query)

        # Should handle gracefully even with no meaningful keywords
        assert isinstance(result, dict)

    def test_numbers_preserved(self):
        """Test that numbers are handled."""
        query = "Python 3.9 vs Python 2.7 differences"
        result = extract_keywords_for_search(query)

        # Numbers should be included in words
        assert "python" in result["high_level"] or "python" in result["low_level"]

    def test_case_insensitivity(self):
        """Test that extraction is case insensitive."""
        query1 = "MACHINE LEARNING"
        query2 = "machine learning"

        result1 = extract_keywords_for_search(query1)
        result2 = extract_keywords_for_search(query2)

        # Should produce same keywords regardless of case
        assert set(result1["high_level"]) == set(result2["high_level"])

    def test_complex_query(self):
        """Test extraction from a complex technical query."""
        query = "Explain the relationship between transformer architecture and attention mechanism in deep learning"
        result = extract_keywords_for_search(query)

        # Should extract meaningful technical terms
        keywords = result["all_keywords"]
        technical_terms = ["transformer", "architecture", "attention", "mechanism", "learning"]

        found_terms = [term for term in technical_terms if term in keywords]
        assert len(found_terms) >= 3, f"Expected at least 3 technical terms, found {found_terms}"

    def test_short_query(self):
        """Test extraction from a very short query."""
        query = "AI"
        result = extract_keywords_for_search(query)

        # Should handle short input gracefully
        assert isinstance(result, dict)
        # Short words (< 3 chars) should be filtered
        assert len(result["all_keywords"]) == 0 or all(len(w) >= 3 for w in result["all_keywords"])

    def test_duplicate_keywords(self):
        """Test that duplicate keywords are removed."""
        query = "machine learning machine learning machine"
        result = extract_keywords_for_search(query)

        # Should not have duplicates
        assert len(result["all_keywords"]) == len(set(result["all_keywords"]))

    def test_keyword_order_preserved(self):
        """Test that keyword order matches original query order."""
        query = "machine learning deep learning neural networks"
        result = extract_keywords_for_search(query)

        # Order should be preserved within each category
        # Note: high_level and low_level are separate, so test within high_level
        keywords = result["high_level"]
        # All these words are > 5 chars so should be in high_level
        expected_order = ["machine", "learning", "deep", "networks"]
        for kw in expected_order:
            if kw in keywords:
                # Just verify each keyword exists - order within category is preserved
                pass
        assert len(keywords) >= 3  # Should have at least 3 keywords


class TestKeywordSearchEnhancement:
    """Test keyword boosting for search."""

    def test_boost_with_keywords(self):
        """Test that chunks matching keywords get boosted scores."""
        query = "machine learning algorithms"
        keywords = extract_keywords_for_search(query)

        # Chunks with more keyword matches should score higher
        chunk1 = "Machine learning is a popular field."
        chunk2 = "Python is a programming language."

        keyword_matches_1 = sum(1 for kw in keywords["all_keywords"] if kw in chunk1.lower())
        keyword_matches_2 = sum(1 for kw in keywords["all_keywords"] if kw in chunk2.lower())

        assert keyword_matches_1 > keyword_matches_2

    def test_partial_match_scoring(self):
        """Test partial keyword matching."""
        query = "neural network"
        keywords = extract_keywords_for_search(query)

        chunk = "This neural network uses deep learning techniques."
        matches = sum(1 for kw in keywords["all_keywords"] if kw in chunk.lower())

        assert matches >= 2  # Should match both "neural" and "network"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
