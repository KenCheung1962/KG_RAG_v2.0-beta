#!/usr/bin/env python3
"""
T036 Phase 5.6 - API Testing Suite

Test coverage for Entity, Relationship, and Query APIs.

Tests:
- Entity CRUD (POST/PUT/DELETE)
- Relationship CRUD (POST/DELETE)
- Query API (POST /query, GET /graph)

Coverage Target: ≥ 80%
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Mock the database before importing app
mock_db = Mock()
mock_db.get_entities_count.return_value = 100
mock_db.get_relationships_count.return_value = 500
mock_db.validate_connection.return_value = {
    'connected': True,
    'storage_path': '/tmp/test',
    'entities_count': 100,
    'relationships_count': 500,
    'validated_at': datetime.utcnow().isoformat()
}
mock_db.entities = {}
mock_db.relationships = {}


class MockLightRAGDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self._entities = {}
        self._relationships = {}
    
    def get_entities_count(self):
        return len(self._entities)
    
    def get_relationships_count(self):
        return len(self._relationships)
    
    def validate_connection(self):
        return {
            'connected': True,
            'storage_path': '/tmp/test',
            'entities_count': len(self._entities),
            'relationships_count': len(self._relationships),
            'validated_at': datetime.utcnow().isoformat()
        }
    
    def create_entity(self, entity_id, name, entity_type, metadata=None):
        entity_data = {
            'entity_names': [name],
            'type': entity_type,
            'count': 1,
            'create_time': datetime.utcnow().isoformat(),
            'update_time': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        self._entities[entity_id] = entity_data
        return entity_data
    
    def update_entity(self, entity_id, name=None, entity_type=None, metadata=None):
        if entity_id not in self._entities:
            return None
        entity_data = self._entities[entity_id]
        if name:
            entity_names = entity_data.get('entity_names', [])
            if name not in entity_names:
                entity_names.append(name)
            entity_data['entity_names'] = entity_names
        if entity_type:
            entity_data['type'] = entity_type
        if metadata:
            existing_metadata = entity_data.get('metadata', {})
            existing_metadata.update(metadata)
            entity_data['metadata'] = existing_metadata
        entity_data['update_time'] = datetime.utcnow().isoformat()
        self._entities[entity_id] = entity_data
        return entity_data
    
    def delete_entity(self, entity_id):
        if entity_id not in self._entities:
            return False
        del self._entities[entity_id]
        return True
    
    def create_relationship(self, relationship_id, source_entity, target_entity, 
                           relationship_type, confidence=0.7, metadata=None):
        relationship_data = {
            'src_id': source_entity,
            'tgt_id': target_entity,
            'relationship_type': relationship_type,
            'confidence': confidence,
            'create_time': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        self._relationships[relationship_id] = relationship_data
        return relationship_data
    
    def delete_relationship(self, relationship_id):
        if relationship_id not in self._relationships:
            return False
        del self._relationships[relationship_id]
        return True
    
    def query_knowledge_graph(self, query, entity_types=None, max_depth=2, 
                             limit=20, include_metadata=True):
        import uuid
        query_id = str(uuid.uuid4())
        
        # Search for matching entities
        results = []
        query_lower = query.lower()
        
        for doc_id, entity_data in self._entities.items():
            entity_names = entity_data.get('entity_names', [])
            for name in entity_names:
                if query_lower in name.lower():
                    # Filter by entity types if specified
                    if entity_types and entity_data.get('type') not in entity_types:
                        continue
                    
                    # Calculate relevance score
                    relevance = 0.5 if query_lower in name.lower() else 0.0
                    
                    result = {
                        'entity_id': doc_id,
                        'entity_name': name,
                        'entity_type': entity_data.get('type', 'concept'),
                        'relevance_score': relevance,
                        'relationships': [],
                        'metadata': entity_data.get('metadata', {}) if include_metadata else {}
                    }
                    results.append(result)
                    if len(results) >= limit:
                        break
        
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        graph_info = {
            'entities_found': len(results),
            'max_depth': max_depth,
            'relationship_types': []
        }
        
        return {
            'query_id': query_id,
            'query': query,
            'results': results,
            'total_results': len(results),
            'graph_info': graph_info
        }
    
    def get_entity_graph(self, entity_id, depth=2):
        if entity_id not in self._entities:
            return None
        
        entity_data = self._entities[entity_id]
        entity_name = entity_data.get('entity_names', ['Unknown'])[0]
        
        neighbors = []
        for rel_id, rel_data in self._relationships.items():
            src_id = rel_data.get('src_id', '')
            tgt_id = rel_data.get('tgt_id', '')
            
            if src_id == entity_id:
                neighbor = self._entities.get(tgt_id)
                if neighbor:
                    neighbors.append({
                        'id': tgt_id,
                        'name': neighbor.get('entity_names', ['Unknown'])[0],
                        'type': neighbor.get('type', 'unknown'),
                        'relationship': rel_data.get('relationship_type', 'related_to'),
                        'direction': 'outbound'
                    })
            elif tgt_id == entity_id:
                neighbor = self._entities.get(src_id)
                if neighbor:
                    neighbors.append({
                        'id': src_id,
                        'name': neighbor.get('entity_names', ['Unknown'])[0],
                        'type': neighbor.get('type', 'unknown'),
                        'relationship': rel_data.get('relationship_type', 'related_to'),
                        'direction': 'inbound'
                    })
        
        return {
            'entity_id': entity_id,
            'entity_name': entity_name,
            'entity_type': entity_data.get('type', 'concept'),
            'neighbors': neighbors,
            'relationship_types': list(set(n.get('relationship') for n in neighbors)),
            'depth': depth,
            'total_neighbors': len(neighbors)
        }


@pytest.fixture
def mock_database():
    """Create a mock database instance."""
    return MockLightRAGDatabase()


@pytest.fixture
def client(mock_database):
    """Create a test client with mocked database."""
    with patch('main.get_database', return_value=mock_database):
        with patch('database.LightRAGDatabase') as mock_class:
            mock_class.return_value = mock_database
            from main import app
            with TestClient(app) as client:
                yield client, mock_database


class TestEntityCRUD:
    """Test Entity CRUD operations."""
    
    def test_create_entity(self, client):
        """Test POST /api/v1/entities - Create entity."""
        test_client, db = client
        
        payload = {
            'name': 'Test Entity',
            'entity_type': 'concept',
            'metadata': {'test': True}
        }
        
        response = test_client.post('/api/v1/entities', json=payload)
        
        assert response.status_code == 201
        
        data = response.json()
        assert 'id' in data
        assert data['name'] == 'Test Entity'
        assert data['entity_type'] == 'concept'
        assert data['metadata'] == {'test': True}
        assert 'created_at' in data
        assert 'updated_at' in data
        
        # Verify entity was created in database
        assert len(db._entities) == 1
    
    def test_create_entity_minimal(self, client):
        """Test entity creation with minimal data."""
        test_client, db = client
        
        payload = {
            'name': 'Minimal Entity',
            'entity_type': 'paper'
        }
        
        response = test_client.post('/api/v1/entities', json=payload)
        
        assert response.status_code == 201
        assert response.json()['name'] == 'Minimal Entity'
    
    def test_create_entity_invalid_type(self, client):
        """Test entity creation with invalid type."""
        test_client, db = client
        
        payload = {
            'name': 'Invalid Entity',
            'entity_type': 'invalid_type'
        }
        
        response = test_client.post('/api/v1/entities', json=payload)
        
        assert response.status_code == 422  # Validation error
    
    def test_update_entity(self, client):
        """Test PUT /api/v1/entities/{id} - Update entity."""
        test_client, db = client
        
        # Create entity first
        create_response = test_client.post('/api/v1/entities', json={
            'name': 'Original Name',
            'entity_type': 'concept'
        })
        entity_id = create_response.json()['id']
        
        # Update entity
        update_payload = {
            'name': 'Updated Name',
            'metadata': {'updated': True}
        }
        
        response = test_client.put(f'/api/v1/entities/{entity_id}', json=update_payload)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data['name'] == 'Updated Name'
        assert data['metadata'] == {'updated': True}
    
    def test_update_entity_not_found(self, client):
        """Test updating non-existent entity."""
        test_client, db = client
        
        response = test_client.put('/api/v1/entities/nonexistent-id', json={
            'name': 'Should Fail'
        })
        
        assert response.status_code == 404
    
    def test_delete_entity(self, client):
        """Test DELETE /api/v1/entities/{id} - Delete entity."""
        test_client, db = client
        
        # Create entity first
        create_response = test_client.post('/api/v1/entities', json={
            'name': 'To Delete',
            'entity_type': 'concept'
        })
        entity_id = create_response.json()['id']
        
        # Delete entity
        response = test_client.delete(f'/api/v1/entities/{entity_id}')
        
        assert response.status_code == 204
        
        # Verify entity was deleted
        assert len(db._entities) == 0
    
    def test_delete_entity_not_found(self, client):
        """Test deleting non-existent entity."""
        test_client, db = client
        
        response = test_client.delete('/api/v1/entities/nonexistent-id')
        
        assert response.status_code == 404


class TestRelationshipCRUD:
    """Test Relationship CRUD operations."""
    
    def test_create_relationship(self, client):
        """Test POST /api/v1/relationships - Create relationship."""
        test_client, db = client
        
        # Create entities first
        entity1 = test_client.post('/api/v1/entities', json={
            'name': 'Entity 1',
            'entity_type': 'concept'
        }).json()['id']
        
        entity2 = test_client.post('/api/v1/entities', json={
            'name': 'Entity 2',
            'entity_type': 'concept'
        }).json()['id']
        
        # Create relationship
        payload = {
            'source_entity_id': entity1,
            'target_entity_id': entity2,
            'relationship_type': 'related_to',
            'confidence': 0.85
        }
        
        response = test_client.post('/api/v1/relationships', json=payload)
        
        assert response.status_code == 201
        
        data = response.json()
        assert 'id' in data
        assert data['source_entity_id'] == entity1
        assert data['target_entity_id'] == entity2
        assert data['relationship_type'] == 'related_to'
        assert data['confidence'] == 0.85
    
    def test_create_relationship_with_metadata(self, client):
        """Test relationship creation with metadata."""
        test_client, db = client
        
        entity1 = test_client.post('/api/v1/entities', json={
            'name': 'Source Entity',
            'entity_type': 'paper'
        }).json()['id']
        
        entity2 = test_client.post('/api/v1/entities', json={
            'name': 'Target Entity',
            'entity_type': 'author'
        }).json()['id']
        
        payload = {
            'source_entity_id': entity1,
            'target_entity_id': entity2,
            'relationship_type': 'authored_by',
            'confidence': 0.95,
            'metadata': {'year': 2024}
        }
        
        response = test_client.post('/api/v1/relationships', json=payload)
        
        assert response.status_code == 201
        assert response.json()['metadata'] == {'year': 2024}
    
    def test_delete_relationship(self, client):
        """Test DELETE /api/v1/relationships/{id} - Delete relationship."""
        test_client, db = client
        
        # Create entities and relationship
        entity1 = test_client.post('/api/v1/entities', json={
            'name': 'Source',
            'entity_type': 'concept'
        }).json()['id']
        
        entity2 = test_client.post('/api/v1/entities', json={
            'name': 'Target',
            'entity_type': 'concept'
        }).json()['id']
        
        rel_response = test_client.post('/api/v1/relationships', json={
            'source_entity_id': entity1,
            'target_entity_id': entity2,
            'relationship_type': 'related_to'
        })
        relationship_id = rel_response.json()['id']
        
        # Delete relationship
        response = test_client.delete(f'/api/v1/relationships/{relationship_id}')
        
        assert response.status_code == 204
        
        # Verify relationship was deleted
        assert len(db._relationships) == 0
    
    def test_delete_relationship_not_found(self, client):
        """Test deleting non-existent relationship."""
        test_client, db = client
        
        response = test_client.delete('/api/v1/relationships/nonexistent-id')
        
        assert response.status_code == 404


class TestQueryAPI:
    """Test Query API operations."""
    
    def test_query_knowledge_graph(self, client):
        """Test POST /api/v1/query - Query knowledge graph."""
        test_client, db = client
        
        # Create test entities
        test_client.post('/api/v1/entities', json={
            'name': 'Machine Learning',
            'entity_type': 'concept'
        })
        test_client.post('/api/v1/entities', json={
            'name': 'Deep Learning',
            'entity_type': 'concept'
        })
        
        # Query
        payload = {
            'query': 'Machine Learning',
            'limit': 10
        }
        
        response = test_client.post('/api/v1/query', json=payload)
        
        assert response.status_code == 200
        
        data = response.json()
        assert 'query_id' in data
        assert data['query'] == 'Machine Learning'
        assert 'results' in data
        assert 'total_results' in data
        assert 'graph_info' in data
    
    def test_query_with_entity_types(self, client):
        """Test query with entity type filter."""
        test_client, db = client
        
        # Create entities
        test_client.post('/api/v1/entities', json={
            'name': 'Test Paper',
            'entity_type': 'paper'
        })
        test_client.post('/api/v1/entities', json={
            'name': 'Test Author',
            'entity_type': 'author'
        })
        
        # Query with type filter
        payload = {
            'query': 'Test',
            'entity_types': ['paper'],
            'limit': 10
        }
        
        response = test_client.post('/api/v1/query', json=payload)
        
        assert response.status_code == 200
        
        results = response.json()['results']
        # Should only return paper-type entities
        for result in results:
            assert result['entity_type'] == 'paper'
    
    def test_query_with_max_depth(self, client):
        """Test query with max_depth parameter."""
        test_client, db = client
        
        payload = {
            'query': 'Test',
            'max_depth': 3,
            'limit': 5
        }
        
        response = test_client.post('/api/v1/query', json=payload)
        
        assert response.status_code == 200
        assert response.json()['graph_info']['max_depth'] == 3
    
    def test_get_entity_graph(self, client):
        """Test GET /api/v1/entities/{id}/graph - Get entity subgraph."""
        test_client, db = client
        
        # Create entity
        create_response = test_client.post('/api/v1/entities', json={
            'name': 'Test Entity',
            'entity_type': 'concept'
        })
        entity_id = create_response.json()['id']
        
        # Get entity graph
        response = test_client.get(f'/api/v1/entities/{entity_id}/graph')
        
        assert response.status_code == 200
        
        data = response.json()
        assert data['entity_id'] == entity_id
        assert data['entity_name'] == 'Test Entity'
        assert data['entity_type'] == 'concept'
        assert 'neighbors' in data
        assert 'relationship_types' in data
        assert data['depth'] == 2  # Default depth
    
    def test_get_entity_graph_with_depth(self, client):
        """Test entity graph with custom depth."""
        test_client, db = client
        
        # Create entity
        create_response = test_client.post('/api/v1/entities', json={
            'name': 'Graph Test',
            'entity_type': 'concept'
        })
        entity_id = create_response.json()['id']
        
        # Get entity graph with depth=3
        response = test_client.get(f'/api/v1/entities/{entity_id}/graph?depth=3')
        
        assert response.status_code == 200
        assert response.json()['depth'] == 3
    
    def test_get_entity_graph_not_found(self, client):
        """Test getting graph for non-existent entity."""
        test_client, db = client
        
        response = test_client.get('/api/v1/entities/nonexistent-id/graph')
        
        assert response.status_code == 404


class TestHealthAndStats:
    """Test health check and statistics endpoints."""
    
    def test_health_check(self, client):
        """Test GET /health endpoint."""
        test_client, db = client
        
        response = test_client.get('/health')
        
        assert response.status_code == 200
        
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'version' in data
        assert 'entities_count' in data
        assert 'relationships_count' in data
    
    def test_statistics(self, client):
        """Test GET /api/v1/stats endpoint."""
        test_client, db = client
        
        response = test_client.get('/api/v1/stats')
        
        assert response.status_code == 200
        
        data = response.json()
        assert 'entities' in data
        assert 'relationships' in data
        assert 'validated_at' in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
