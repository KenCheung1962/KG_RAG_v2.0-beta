"""
T036 Phase 4 - Database Module
LightRAG storage connection and operations
"""

import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path
from .config import settings


class LightRAGDatabase:
    """LightRAG storage database handler."""
    
    def __init__(self):
        self.storage_path = Path(settings.lightrag_storage_path)
        # Initialize to empty dicts to prevent NoneType errors
        self._entities: Dict = {}
        self._relationships: Dict = {}
    
    def _load_json(self, filename: str) -> Optional[Dict]:
        """Load JSON file from storage."""
        filepath = self.storage_path / filename
        if filepath.exists():
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    
    def _save_json(self, filename: str, data: Any) -> bool:
        """Save data to JSON file."""
        filepath = self.storage_path / filename
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception:
            return False
    
    @property
    def entities(self) -> Dict:
        """Load and cache entities."""
        if not self._entities:  # Empty dict, try to load
            loaded = self._load_json('kv_store_full_entities.json')
            if loaded:
                self._entities = loaded
        return self._entities
    
    @property
    def relationships(self) -> Dict:
        """Load and cache relationships."""
        if not self._relationships:  # Empty dict, try to load
            loaded = self._load_json('kv_store_full_relations.json')
            if loaded:
                self._relationships = loaded
        return self._relationships
    
    @property
    def linked_entities(self) -> Dict:
        """Load linked entities with relationships."""
        data = self._load_json('vdb_linked_entities.json') or {}
        return data.get('linked_entities', [])
    
    def get_entities_count(self) -> int:
        """Get total number of entities."""
        return len(self.entities)
    
    def get_relationships_count(self) -> int:
        """Get total number of relationships."""
        data = self._load_json('vdb_linked_entities.json') or {}
        return data.get('link_count', 0)
    
    def search_entities(self, query: str, limit: int = 10) -> List[Dict]:
        """Search entities by name."""
        results = []
        query_lower = query.lower()
        
        for doc_id, entity_data in self.entities.items():
            entity_names = entity_data.get('entity_names', [])
            for name in entity_names:
                if query_lower in name.lower():
                    results.append({
                        'id': doc_id,
                        'name': name,
                        'type': entity_data.get('type', 'unknown'),
                        'count': entity_data.get('count', 0)
                    })
                    if len(results) >= limit:
                        return results
        
        return results
    
    def get_entity_by_id(self, entity_id: str) -> Optional[Dict]:
        """Get entity by ID."""
        return self.entities.get(entity_id)
    
    def get_entity_by_name(self, entity_name: str) -> Optional[Dict]:
        """Get entity by name (case-insensitive search)."""
        for entity_id, entity in self.entities.items():
            names = entity.get('entity_names', [])
            if any(entity_name.lower() == n.lower() for n in names):
                return entity
        return None

    def get_entity_by_name(self, entity_name: str) -> Optional[Dict]:
        """Get entity by name (case-insensitive search)."""
        for entity_id, entity in self.entities.items():
            names = entity.get('entity_names', [])
            if any(entity_name.lower() == n.lower() for n in names):
                return entity
        return None
    
    def get_linked_entity(self, entity_name: str) -> Optional[Dict]:
        """Get linked entity with relationships by name."""
        for entity in self.linked_entities:
            if entity.get('name') == entity_name:
                return entity
        return None
    
    def validate_connection(self) -> Dict[str, Any]:
        """Validate database connection and return status."""
        entities_count = self.get_entities_count()
        relationships_count = self.get_relationships_count()
        
        return {
            'connected': True,
            'storage_path': str(self.storage_path),
            'entities_count': entities_count,
            'relationships_count': relationships_count,
            'validated_at': datetime.now(timezone.utc).isoformat()
        }
    
    # ==================== WRITE OPERATIONS (Phase 5) ====================
    
    def create_entity(self, entity_id: str, name: str, entity_type: str, 
                      metadata: Optional[Dict] = None) -> Dict:
        """Create a new entity."""
        entity_data = {
            'entity_names': [name],
            'type': entity_type,
            'count': 1,
            'create_time': datetime.now(timezone.utc).isoformat(),
            'update_time': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        # Update in-memory cache
        self._entities[entity_id] = entity_data
        
        # Persist to disk
        self._save_json('kv_store_full_entities.json', self._entities)
        
        # Clear linked entities cache so it will be rebuilt
        self._clear_linked_entities_cache()
        
        return entity_data
    
    def update_entity(self, entity_id: str, name: Optional[str] = None,
                      entity_type: Optional[str] = None,
                      metadata: Optional[Dict] = None) -> Optional[Dict]:
        """Update an existing entity."""
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
        
        entity_data['update_time'] = datetime.now(timezone.utc).isoformat()
        
        # Update in-memory cache
        self._entities[entity_id] = entity_data
        
        # Persist to disk
        self._save_json('kv_store_full_entities.json', self._entities)
        
        return entity_data
    
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity."""
        if entity_id not in self._entities:
            return False
        
        del self._entities[entity_id]
        
        # Persist to disk
        self._save_json('kv_store_full_entities.json', self._entities)
        
        # Clear linked entities cache
        self._clear_linked_entities_cache()
        
        return True
    
    def create_relationship(self, relationship_id: str, source_entity: str,
                            target_entity: str, relationship_type: str,
                            confidence: float = 0.7,
                            metadata: Optional[Dict] = None) -> Dict:
        """Create a new relationship."""
        relationship_data = {
            'src_id': source_entity,
            'tgt_id': target_entity,
            'relationship_type': relationship_type,
            'confidence': confidence,
            'create_time': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        
        # Update in-memory cache
        self._relationships[relationship_id] = relationship_data
        
        # Persist to disk
        self._save_json('kv_store_full_relations.json', self._relationships)
        
        # Clear linked entities cache
        self._clear_linked_entities_cache()
        
        return relationship_data
    
    def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship."""
        if relationship_id not in self._relationships:
            return False
        
        del self._relationships[relationship_id]
        
        # Persist to disk
        self._save_json('kv_store_full_relations.json', self._relationships)
        
        # Clear linked entities cache
        self._clear_linked_entities_cache()
        
        return True
    
    def _clear_linked_entities_cache(self):
        """Clear the linked entities cache file."""
        cache_file = self.storage_path / 'vdb_linked_entities.json'
        if cache_file.exists():
            cache_file.unlink()
        self._linked_entities = None
    
    # ==================== QUERY METHODS (Phase 5.4) ====================
    
    def query_knowledge_graph(self, query: str, entity_types: Optional[List[str]] = None,
                              max_depth: int = 2, limit: int = 20,
                              include_metadata: bool = True) -> Dict[str, Any]:
        """
        Query the knowledge graph.
        
        Args:
            query: Natural language query
            entity_types: Filter by entity types
            max_depth: Graph traversal depth
            limit: Maximum results
            include_metadata: Include entity metadata
            
        Returns:
            Query results with graph information
        """
        import uuid
        
        query_id = str(uuid.uuid4())
        results = []
        
        # Search for matching entities
        matching_entities = self._search_entities_by_query(query, limit * 2)
        
        # Filter by entity types if specified
        if entity_types:
            matching_entities = [
                e for e in matching_entities
                if e.get('type') in entity_types
            ]
        
        # Build graph information
        for entity in matching_entities[:limit]:
            entity_name = entity.get('name', 'Unknown')
            
            # Get relationships for this entity
            relationships = self._get_entity_relationships(entity_name)
            
            # Calculate relevance score (simple keyword matching)
            relevance_score = self._calculate_relevance(query, entity_name)
            
            result = {
                'entity_id': entity.get('id', ''),
                'entity_name': entity_name,
                'entity_type': entity.get('type', 'concept'),
                'relevance_score': relevance_score,
                'relationships': relationships[:5],  # Limit relationships
                'metadata': entity.get('metadata', {}) if include_metadata else {}
            }
            results.append(result)
        
        # Sort by relevance
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Build graph info
        graph_info = {
            'entities_found': len(matching_entities),
            'max_depth': max_depth,
            'relationship_types': self._get_relationship_types()
        }
        
        return {
            'query_id': query_id,
            'query': query,
            'results': results,
            'total_results': len(results),
            'graph_info': graph_info
        }
    
    def get_entity_graph(self, entity_id: str, depth: int = 2) -> Optional[Dict[str, Any]]:
        """
        Get subgraph for a specific entity.
        
        Args:
            entity_id: Entity ID
            depth: Traversal depth
            
        Returns:
            Entity subgraph with neighbors
        """
        # Get entity by ID
        entity_data = self.get_entity_by_id(entity_id)
        if not entity_data:
            return None
        
        entity_name = entity_data.get('entity_names', [None])[0]
        
        # Get neighbors (entities connected to this one)
        neighbors = []
        neighbor_ids = set()
        
        for rel_id, rel_data in self.relationships.items():
            src_id = rel_data.get('src_id', '')
            tgt_id = rel_data.get('tgt_id', '')
            
            if src_id == entity_id:
                # This entity is the source
                neighbor_ids.add(tgt_id)
                neighbor = self.get_entity_by_id(tgt_id)
                if neighbor:
                    neighbors.append({
                        'id': tgt_id,
                        'name': neighbor.get('entity_names', ['Unknown'])[0],
                        'type': neighbor.get('type', 'unknown'),
                        'relationship': rel_data.get('relationship_type', 'related_to'),
                        'direction': 'outbound'
                    })
            elif tgt_id == entity_id:
                # This entity is the target
                neighbor_ids.add(src_id)
                neighbor = self.get_entity_by_id(src_id)
                if neighbor:
                    neighbors.append({
                        'id': src_id,
                        'name': neighbor.get('entity_names', ['Unknown'])[0],
                        'type': neighbor.get('type', 'unknown'),
                        'relationship': rel_data.get('relationship_type', 'related_to'),
                        'direction': 'inbound'
                    })
        
        # Get relationship types
        relationship_types = self._get_relationship_types()
        
        return {
            'entity_id': entity_id,
            'entity_name': entity_name,
            'entity_type': entity_data.get('type', 'concept'),
            'neighbors': neighbors,
            'relationship_types': relationship_types,
            'depth': depth,
            'total_neighbors': len(neighbors)
        }
    
    def _search_entities_by_query(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search entities matching a query."""
        results = []
        query_lower = query.lower()
        
        for doc_id, entity_data in self.entities.items():
            entity_names = entity_data.get('entity_names', [])
            for name in entity_names:
                # Simple keyword matching
                if query_lower in name.lower():
                    results.append({
                        'id': doc_id,
                        'name': name,
                        'type': entity_data.get('type', 'concept'),
                        'metadata': entity_data.get('metadata', {})
                    })
                    if len(results) >= limit:
                        return results
        
        return results
    
    def _get_entity_relationships(self, entity_name: str) -> List[Dict[str, Any]]:
        """Get relationships for an entity."""
        relationships = []
        
        for rel_id, rel_data in self.relationships.items():
            src_id = rel_data.get('src_id', '')
            tgt_id = rel_data.get('tgt_id', '')
            
            # Find the other entity
            if src_id == entity_name or tgt_id == entity_name:
                other_id = tgt_id if src_id == entity_name else src_id
                other_entity = self.get_entity_by_name(other_id)
                
                if other_entity:
                    relationships.append({
                        'id': rel_id,
                        'entity': other_entity.get('entity_names', ['Unknown'])[0],
                        'type': rel_data.get('relationship_type', 'related_to'),
                        'confidence': rel_data.get('confidence', 0.7)
                    })
        
        return relationships
    
    def _calculate_relevance(self, query: str, entity_name: str) -> float:
        """Calculate relevance score between query and entity."""
        query_words = set(query.lower().split())
        entity_words = set(entity_name.lower().split())
        
        # Simple Jaccard similarity
        intersection = len(query_words & entity_words)
        union = len(query_words | entity_words)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _get_relationship_types(self) -> List[str]:
        """Get all unique relationship types."""
        types = set()
        for rel_data in self.relationships.values():
            rel_type = rel_data.get('relationship_type', '')
            if rel_type:
                types.add(rel_type)
        return list(types)


# Global database instance
db = LightRAGDatabase()


# Global database instance
db = LightRAGDatabase()


def get_database() -> LightRAGDatabase:
    """Get database instance for FastAPI dependency injection."""
    return db
