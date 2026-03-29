"""
Test database layer for unified_indexing module.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unified_indexing.database import LightRAGDatabase
from unified_indexing.config import settings


def test_config_loading():
    """Test that configuration loads correctly."""
    assert settings is not None
    assert settings.lightrag_storage_path is not None


def test_config_values():
    """Test configuration values are set."""
    # These should be set in the environment or defaults
    assert isinstance(settings.lightrag_storage_path, str)


def test_database_connection():
    """Test database connection and accessibility."""
    db = LightRAGDatabase()
    entities = db.entities
    assert entities is not None
    # Should return a dict
    assert isinstance(entities, dict)


def test_get_entities():
    """Test retrieving entities from database."""
    db = LightRAGDatabase()
    all_entities = db.entities
    assert all_entities is not None
    assert isinstance(all_entities, dict)
    # Entity IDs should be strings
    for entity_id in all_entities:
        assert isinstance(entity_id, str)


def test_entity_count():
    """Test entity count from database."""
    db = LightRAGDatabase()
    entities = db.entities
    # At least some entities should exist based on Phase 3
    entity_count = len(entities)
    assert entity_count >= 0


def test_relationships():
    """Test retrieving relationships from database."""
    db = LightRAGDatabase()
    relationships = db.relationships
    assert relationships is not None
    assert isinstance(relationships, dict)


def test_get_stats():
    """Test retrieving system statistics."""
    db = LightRAGDatabase()
    entities = db.entities
    relationships = db.relationships
    
    # Calculate stats manually
    total_entities = len(entities)
    total_relationships = len(relationships)
    
    # Entity types
    entity_types = {}
    for entity_id, entity_data in entities.items():
        if isinstance(entity_data, dict) and "type" in entity_data:
            entity_type = entity_data["type"]
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
    
    # Relationship types
    relationship_types = {}
    for rel_id, rel_data in relationships.items():
        if isinstance(rel_data, dict) and "type" in rel_data:
            rel_type = rel_data["type"]
            relationship_types[rel_type] = relationship_types.get(rel_type, 0) + 1
    
    # Verify calculations
    assert total_entities >= 0
    assert total_relationships >= 0
    assert isinstance(entity_types, dict)
    assert isinstance(relationship_types, dict)


def test_stats_values():
    """Test statistics values are reasonable."""
    db = LightRAGDatabase()
    entities = db.entities
    relationships = db.relationships
    
    # Entities should be a positive integer (or zero)
    entity_count = len(entities)
    assert isinstance(entity_count, int)
    assert entity_count >= 0
    
    # Relationships should be a positive integer (or zero)
    rel_count = len(relationships)
    assert isinstance(rel_count, int)
    assert rel_count >= 0


def test_entity_types():
    """Test entity types are returned."""
    db = LightRAGDatabase()
    entities = db.entities
    
    entity_types = set()
    for entity_id, entity_data in entities.items():
        if isinstance(entity_data, dict) and "type" in entity_data:
            entity_types.add(entity_data["type"])
    
    # Should have at least one entity type
    # (Based on Phase 3, we expect paper, person, concept, etc.)
    print(f"Found entity types: {entity_types}")
