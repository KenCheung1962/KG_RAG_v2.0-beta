#!/usr/bin/env python3
"""
T072 - PostgreSQL Storage Integration for KG RAG
Priority 2: Storage integration with existing KG RAG storage

This module provides PostgreSQL storage integration for the KG RAG system,
replacing the Neo4j storage with PostgreSQL + pgvector.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import json
from dataclasses import dataclass
from enum import Enum

from client import PostgresClient, init_postgres_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DistanceMetric(Enum):
    """Distance metrics for vector similarity search."""
    COSINE = "cosine"
    L2 = "l2"
    INNER_PRODUCT = "inner_product"


@dataclass
class Entity:
    """Knowledge graph entity."""
    entity_id: str
    entity_type: str
    name: str
    description: Optional[str] = None
    properties: Dict[str, Any] = None
    embedding: Optional[List[float]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary for database storage."""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "name": self.name,
            "description": self.description,
            "properties": json.dumps(self.properties) if self.properties else "{}",
            "embedding": self.embedding,
            "created_at": self.created_at or datetime.now(),
            "updated_at": self.updated_at or datetime.now()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Entity':
        """Create entity from dictionary."""
        properties = json.loads(data.get("properties", "{}")) if data.get("properties") else {}
        embedding = data.get("embedding")
        if embedding and isinstance(embedding, str):
            embedding = json.loads(embedding)
            
        return cls(
            entity_id=data["entity_id"],
            entity_type=data["entity_type"],
            name=data["name"],
            description=data.get("description"),
            properties=properties,
            embedding=embedding,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


@dataclass
class Relationship:
    """Knowledge graph relationship with embedding support."""
    relationship_id: str
    source_id: str
    target_id: str
    relationship_type: str
    properties: Dict[str, Any] = None
    weight: float = 1.0
    description: Optional[str] = None  # Human-readable description for embedding
    keywords: Optional[str] = None       # Keywords for filtering
    embedding: Optional[List[float]] = None  # Vector embedding of description
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary for database storage."""
        result = {
            "relationship_id": self.relationship_id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "properties": json.dumps(self.properties) if self.properties else "{}",
            "weight": self.weight,
            "description": self.description,
            "keywords": self.keywords,
            "created_at": self.created_at or datetime.now()
        }
        
        # Handle embedding - convert list to JSON string if present
        if self.embedding is not None:
            result["embedding"] = json.dumps(self.embedding)
        else:
            result["embedding"] = None
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Relationship':
        """Create relationship from dictionary."""
        properties = json.loads(data.get("properties", "{}")) if data.get("properties") else {}
        
        # Handle embedding - parse JSON string if present
        embedding = data.get("embedding")
        if embedding and isinstance(embedding, str):
            embedding = json.loads(embedding)
        
        return cls(
            relationship_id=data["relationship_id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relationship_type=data["relationship_type"],
            properties=properties,
            weight=float(data.get("weight", 1.0)),
            description=data.get("description"),
            keywords=data.get("keywords"),
            embedding=embedding,
            created_at=data.get("created_at")
        )


@dataclass
class Chunk:
    """Text chunk for RAG."""
    chunk_id: str
    entity_id: str
    content: str
    source: Optional[str] = None
    chunk_index: int = 0
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary for database storage."""
        return {
            "chunk_id": self.chunk_id,
            "entity_id": self.entity_id,
            "content": self.content,
            "source": self.source,
            "chunk_index": self.chunk_index,
            "embedding": self.embedding,
            "metadata": json.dumps(self.metadata) if self.metadata else "{}",
            "created_at": self.created_at or datetime.now()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Chunk':
        """Create chunk from dictionary."""
        metadata = json.loads(data.get("metadata", "{}")) if data.get("metadata") else {}
        embedding = data.get("embedding")
        if embedding and isinstance(embedding, str):
            embedding = json.loads(embedding)
            
        return cls(
            chunk_id=data["chunk_id"],
            entity_id=data["entity_id"],
            content=data["content"],
            source=data.get("source"),
            chunk_index=int(data.get("chunk_index", 0)),
            embedding=embedding,
            metadata=metadata,
            created_at=data.get("created_at")
        )


@dataclass
class SearchResult:
    """Search result from vector similarity search."""
    chunk_id: str
    content: str
    source: Optional[str]
    similarity: float
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert search result to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "source": self.source,
            "similarity": self.similarity,
            "metadata": self.metadata
        }


class KGStorage:
    """Knowledge Graph Storage using PostgreSQL with pgvector."""
    
    def __init__(self, postgres_client: PostgresClient):
        self.client = postgres_client
        
    async def health_check(self) -> Dict[str, Any]:
        """Check storage health."""
        return await self.client.health_check()
    
    # ===== Entity Operations =====
    
    async def create_entity(self, entity: Entity) -> Dict[str, Any]:
        """Create a new entity."""
        query = """
        INSERT INTO entities (
            entity_id, entity_type, name, description, 
            properties, embedding, created_at, updated_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (entity_id) DO UPDATE SET
            entity_type = EXCLUDED.entity_type,
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            properties = EXCLUDED.properties,
            embedding = EXCLUDED.embedding,
            updated_at = EXCLUDED.updated_at
        RETURNING entity_id
        """
        
        entity_dict = entity.to_dict()
        
        # Convert embedding list to JSON string for pgvector
        embedding = entity_dict["embedding"]
        if embedding is not None:
            embedding = json.dumps(embedding)
        
        try:
            result = await self.client.execute(
                query,
                entity_dict["entity_id"],
                entity_dict["entity_type"],
                entity_dict["name"],
                entity_dict["description"],
                entity_dict["properties"],
                embedding,
                entity_dict["created_at"],
                entity_dict["updated_at"]
            )
            
            return {
                "success": True,
                "entity_id": entity.entity_id,
                "message": "Entity created/updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create entity {entity.entity_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        query = "SELECT * FROM entities WHERE entity_id = $1"
        
        try:
            row = await self.client.fetchrow(query, entity_id)
            if row:
                return Entity.from_dict(dict(row))
            return None
            
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
            return None
    
    async def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update entity fields."""
        if not updates:
            return {"success": False, "error": "No updates provided"}
        
        # Build SET clause
        set_clauses = []
        values = []
        param_index = 1
        
        for key, value in updates.items():
            if key in ["properties", "embedding"] and value is not None:
                if key == "properties":
                    value = json.dumps(value)
                set_clauses.append(f"{key} = ${param_index}")
                values.append(value)
                param_index += 1
            elif key not in ["entity_id", "created_at"]:
                set_clauses.append(f"{key} = ${param_index}")
                values.append(value)
                param_index += 1
        
        # Always update updated_at
        set_clauses.append("updated_at = NOW()")
        
        query = f"""
        UPDATE entities 
        SET {', '.join(set_clauses)}
        WHERE entity_id = ${param_index}
        RETURNING entity_id
        """
        
        values.append(entity_id)
        
        try:
            result = await self.client.execute(query, *values)
            return {
                "success": True,
                "entity_id": entity_id,
                "message": "Entity updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to update entity {entity_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def delete_entity(self, entity_id: str) -> Dict[str, Any]:
        """Delete entity by ID."""
        query = "DELETE FROM entities WHERE entity_id = $1 RETURNING entity_id"
        
        try:
            result = await self.client.execute(query, entity_id)
            return {
                "success": True,
                "entity_id": entity_id,
                "message": "Entity deleted successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to delete entity {entity_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_entities(
        self, 
        query_vector: List[float],
        entity_type: Optional[str] = None,
        limit: int = 10,
        distance_metric: DistanceMetric = DistanceMetric.COSINE
    ) -> List[Dict[str, Any]]:
        """Search entities by vector similarity."""
        where_clause = "WHERE 1=1"
        # Convert query_vector list to JSON string for pgvector
        query_vector_str = json.dumps(query_vector)
        params = [query_vector_str]
        param_index = 2
        
        if entity_type:
            where_clause += f" AND entity_type = ${param_index}"
            params.append(entity_type)
            param_index += 1
        
        query = f"""
        SELECT *, 
            (1 - (embedding <=> $1::vector)) as similarity
        FROM entities
        {where_clause}
        ORDER BY embedding <=> $1::vector
        LIMIT ${param_index}
        """
        
        params.append(limit)
        
        try:
            results = await self.client.fetch(query, *params)
            return [
                {
                    **dict(record),
                    "similarity": float(record["similarity"])
                }
                for record in results
            ]
            
        except Exception as e:
            logger.error(f"Failed to search entities: {e}")
            return []
    
    # ===== Relationship Operations =====
    
    async def create_relationship(self, relationship: Relationship) -> Dict[str, Any]:
        """Create a new relationship with embedding support."""
        query = """
        INSERT INTO relationships (
            relationship_id, source_id, target_id, 
            relationship_type, properties, weight, 
            description, keywords, embedding, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (relationship_id) DO UPDATE SET
            source_id = EXCLUDED.source_id,
            target_id = EXCLUDED.target_id,
            relationship_type = EXCLUDED.relationship_type,
            properties = EXCLUDED.properties,
            weight = EXCLUDED.weight,
            description = EXCLUDED.description,
            keywords = EXCLUDED.keywords,
            embedding = EXCLUDED.embedding,
            created_at = EXCLUDED.created_at
        RETURNING relationship_id
        """
        
        relationship_dict = relationship.to_dict()
        
        try:
            result = await self.client.execute(
                query,
                relationship_dict["relationship_id"],
                relationship_dict["source_id"],
                relationship_dict["target_id"],
                relationship_dict["relationship_type"],
                relationship_dict["properties"],
                relationship_dict["weight"],
                relationship_dict.get("description"),
                relationship_dict.get("keywords"),
                relationship_dict.get("embedding"),
                relationship_dict["created_at"]
            )
            
            return {
                "success": True,
                "relationship_id": relationship.relationship_id,
                "message": "Relationship created/updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create relationship {relationship.relationship_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_relationships(
        self, 
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        relationship_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Relationship]:
        """Get relationships with optional filters."""
        where_clauses = []
        params = []
        param_index = 1
        
        if source_id:
            where_clauses.append(f"source_id = ${param_index}")
            params.append(source_id)
            param_index += 1
            
        if target_id:
            where_clauses.append(f"target_id = ${param_index}")
            params.append(target_id)
            param_index += 1
            
        if relationship_type:
            where_clauses.append(f"relationship_type = ${param_index}")
            params.append(relationship_type)
            param_index += 1
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
        SELECT * FROM relationships
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_index}
        """
        
        params.append(limit)
        
        try:
            rows = await self.client.fetch(query, *params)
            return [Relationship.from_dict(dict(row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get relationships: {e}")
            return []
    
    async def search_relationships(
        self,
        query_vector: List[float],
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        limit: int = 10,
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
        match_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search relationships by vector similarity on description embedding."""
        where_clauses = [
            "embedding IS NOT NULL",  # Only search relationships with embeddings
        ]
        
        # Convert query_vector to pgvector string format
        vector_str = '[' + ','.join(str(x) for x in query_vector) + ']'
        params = [vector_str, match_threshold, limit]
        param_index = 4
        
        if source_id:
            where_clauses.append(f"source_id = ${param_index}")
            params.append(source_id)
            param_index += 1
            
        if target_id:
            where_clauses.append(f"target_id = ${param_index}")
            params.append(target_id)
            param_index += 1
        
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
        SELECT 
            relationship_id,
            source_id,
            target_id,
            relationship_type,
            description,
            keywords,
            weight,
            properties,
            1 - (embedding <=> $1::vector) as similarity
        FROM relationships
        WHERE {where_clause}
          AND 1 - (embedding <=> $1::vector) >= $2
        ORDER BY embedding <=> $1::vector
        LIMIT $3
        """
        
        try:
            rows = await self.client.fetch(query, *params)
            return [
                {
                    "relationship_id": str(row["relationship_id"]),
                    "source_id": str(row["source_id"]),
                    "target_id": str(row["target_id"]),
                    "relationship_type": str(row["relationship_type"]),
                    "description": str(row["description"]) if row["description"] else None,
                    "keywords": str(row["keywords"]) if row["keywords"] else None,
                    "weight": float(row["weight"]),
                    "properties": json.loads(row["properties"]) if row.get("properties") else {},
                    "similarity": float(row["similarity"])
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to search relationships: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def get_related_entities(
        self,
        entity_id: str,
        max_depth: int = 2,
        limit_per_level: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get related entities by traversing relationships up to max_depth.
        Returns list of entities with their relationship paths.
        """
        # Use recursive CTE for graph traversal
        query = """
        WITH RECURSIVE related_paths AS (
            -- Base case: direct relationships
            SELECT 
                r.source_id,
                r.target_id,
                r.relationship_type,
                r.description,
                r.weight,
                1 as depth,
                ARRAY[($1::varchar)] as path
            FROM relationships r
            WHERE r.source_id = $1 OR r.target_id = $1
            
            UNION ALL
            
            -- Recursive case: traverse further
            SELECT 
                r.source_id,
                r.target_id,
                r.relationship_type,
                r.description,
                r.weight,
                rp.depth + 1,
                rp.path || CASE 
                    WHEN r.source_id = rp.target_id THEN r.target_id
                    ELSE r.source_id
                END
            FROM relationships r
            INNER JOIN related_paths rp ON (
                (r.source_id = rp.target_id OR r.target_id = rp.source_id)
                AND rp.depth < $2
                AND NOT (CASE 
                    WHEN r.source_id = rp.target_id THEN r.target_id
                    ELSE r.source_id
                END = ANY(rp.path))  -- Avoid cycles
            )
        )
        SELECT DISTINCT ON (related_entity_id)
            rp.*,
            e.name as related_entity_name,
            e.entity_type as related_entity_type,
            CASE 
                WHEN rp.source_id = $1 THEN rp.target_id
                ELSE rp.source_id
            END as related_entity_id
        FROM related_paths rp
        JOIN entities e ON e.entity_id = CASE 
            WHEN rp.source_id = $1 THEN rp.target_id
            ELSE rp.source_id
        END
        ORDER BY related_entity_id, rp.depth, rp.weight DESC
        LIMIT $3
        """
        
        try:
            rows = await self.client.fetch(query, entity_id, max_depth, limit_per_level)
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get related entities for {entity_id}: {e}")
            return []
    
    # ===== Chunk Operations =====
    
    async def create_chunk(self, chunk: Chunk) -> Dict[str, Any]:
        """Create a new chunk."""
        query = """
        INSERT INTO chunks (
            chunk_id, entity_id, content, source,
            chunk_index, embedding, metadata, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (chunk_id) DO UPDATE SET
            entity_id = EXCLUDED.entity_id,
            content = EXCLUDED.content,
            source = EXCLUDED.source,
            chunk_index = EXCLUDED.chunk_index,
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata,
            created_at = EXCLUDED.created_at
        RETURNING chunk_id
        """
        
        chunk_dict = chunk.to_dict()
        
        # Convert embedding list to JSON string for pgvector
        embedding = chunk_dict["embedding"]
        if embedding is not None:
            embedding = json.dumps(embedding)
        
        try:
            result = await self.client.execute(
                query,
                chunk_dict["chunk_id"],
                chunk_dict["entity_id"],
                chunk_dict["content"],
                chunk_dict["source"],
                chunk_dict["chunk_index"],
                embedding,
                chunk_dict["metadata"],
                chunk_dict["created_at"]
            )
            
            return {
                "success": True,
                "chunk_id": chunk.chunk_id,
                "message": "Chunk created/updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create chunk {chunk.chunk_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        """Get chunk by ID."""
        query = "SELECT * FROM chunks WHERE chunk_id = $1"
        
        try:
            row = await self.client.fetchrow(query, chunk_id)
            if row:
                return Chunk.from_dict(dict(row))
            return None
            
        except Exception as e:
            logger.error(f"Failed to get chunk {chunk_id}: {e}")
            return None
    
    async def get_chunks_by_entity(self, entity_id: str, limit: int = 100) -> List[Chunk]:
        """Get chunks by entity ID."""
        query = """
        SELECT * FROM chunks 
        WHERE entity_id = $1 
        ORDER BY chunk_index
        LIMIT $2
        """
        
        try:
            rows = await self.client.fetch(query, entity_id, limit)
            return [Chunk.from_dict(dict(row)) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get chunks for entity {entity_id}: {e}")
            return []
    
    async def search_chunks(
        self,
        query_vector: List[float],
        entity_id: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 10,
        distance_metric: DistanceMetric = DistanceMetric.COSINE,
        match_threshold: float = 0.7
    ) -> List[SearchResult]:
        """Search chunks by vector similarity using direct SQL with pgvector."""
        where_clauses = [
            "embedding IS NOT NULL",  # Only search chunks with embeddings
            "LENGTH(TRIM(content)) > 0"  # Exclude whitespace-only chunks
        ]
        
        # Convert query_vector to pgvector string format: [0.1,0.2,...]
        vector_str = '[' + ','.join(str(x) for x in query_vector) + ']'
        params = [vector_str, match_threshold, limit]
        param_index = 4
        
        if entity_id:
            where_clauses.append(f"entity_id = ${param_index}")
            params.append(entity_id)
            param_index += 1
            
        if source:
            where_clauses.append(f"source = ${param_index}")
            params.append(source)
            param_index += 1
        
        where_clause = " AND ".join(where_clauses)
        
        # Use direct vector similarity search with cosine distance
        # cosine similarity = 1 - cosine distance
        query = f"""
        SELECT 
            chunk_id,
            content,
            source,
            metadata,
            1 - (embedding <=> $1::vector) as similarity
        FROM chunks
        WHERE {where_clause}
          AND 1 - (embedding <=> $1::vector) >= $2
        ORDER BY embedding <=> $1::vector
        LIMIT $3
        """
        
        try:
            rows = await self.client.fetch(query, *params)
            return [
                SearchResult(
                    chunk_id=str(row["chunk_id"]),
                    content=str(row["content"]),
                    source=str(row["source"]) if row["source"] else None,
                    similarity=float(row["similarity"]),
                    metadata=json.loads(row["metadata"]) if row.get("metadata") else {}
                )
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to search chunks: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def batch_create_chunks(self, chunks: List[Chunk]) -> Dict[str, Any]:
        """Create multiple chunks in batch."""
        if not chunks:
            return {"success": True, "inserted": 0, "message": "No chunks to create"}
        
        records = [chunk.to_dict() for chunk in chunks]
        
        result = await self.client.batch_insert(
            table="chunks",
            records=records,
            batch_size=1000
        )
        
        return result
    
    # ===== Graph Operations =====
    
    async def get_entity_graph(
        self, 
        entity_id: str, 
        max_depth: int = 2,
        limit_per_depth: int = 10
    ) -> Dict[str, Any]:
        """
        Get entity graph with relationships up to max_depth.
        
        Returns a graph structure with entities and relationships.
        """
        # This is a simplified implementation
        # In production, you might want to use recursive CTEs
        
        # Get the entity
        entity = await self.get_entity(entity_id)
        if not entity:
            return {"entities": [], "relationships": []}
        
        # Get direct relationships
        relationships = await self.get_relationships(
            source_id=entity_id,
            limit=limit_per_depth
        )
        
        # Get target entities
        target_ids = [rel.target_id for rel in relationships]
        entities = [entity]
        
        # Get target entities (simplified - in production, batch this)
        for target_id in target_ids:
            target_entity = await self.get_entity(target_id)
            if target_entity:
                entities.append(target_entity)
        
        return {
            "entities": [e.to_dict() for e in entities],
            "relationships": [r.to_dict() for r in relationships]
        }
    
    # ===== Statistics =====
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        try:
            async with self.client.acquire_connection() as conn:
                # Entity count by type
                entity_stats = await conn.fetch("""
                    SELECT entity_type, COUNT(*) as count
                    FROM entities
                    GROUP BY entity_type
                    ORDER BY count DESC
                """)
                
                # Relationship count by type
                relationship_stats = await conn.fetch("""
                    SELECT relationship_type, COUNT(*) as count
                    FROM relationships
                    GROUP BY relationship_type
                    ORDER BY count DESC
                """)
                
                # Chunk count by source
                chunk_stats = await conn.fetch("""
                    SELECT source, COUNT(*) as count
                    FROM chunks
                    WHERE source IS NOT NULL
                    GROUP BY source
                    ORDER BY count DESC
                """)
                
                # Total counts
                total_entities = await conn.fetchval("SELECT COUNT(*) FROM entities")
                total_relationships = await conn.fetchval("SELECT COUNT(*) FROM relationships")
                total_chunks = await conn.fetchval("SELECT COUNT(*) FROM chunks")
                
                return {
                    "total_entities": total_entities,
                    "total_relationships": total_relationships,
                    "total_chunks": total_chunks,
                    "entity_stats": [dict(record) for record in entity_stats],
                    "relationship_stats": [dict(record) for record in relationship_stats],
                    "chunk_stats": [dict(record) for record in chunk_stats]
                }
                
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "error": str(e)
            }
    
    # ===== Embedding Management Operations =====
    
    async def get_relationships_without_embeddings(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get relationships that don't have embeddings yet.
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of relationship records without embeddings
        """
        query = """
        SELECT relationship_id, source_id, target_id, relationship_type,
               description, keywords, properties, created_at
        FROM relationships
        WHERE embedding IS NULL
        ORDER BY created_at DESC
        LIMIT $1
        """
        
        try:
            rows = await self.client.fetch(query, limit)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get relationships without embeddings: {e}")
            return []
    
    async def update_relationship_embedding(
        self, 
        relationship_id: str, 
        embedding: List[float],
        description: Optional[str] = None,
        keywords: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update relationship with embedding and optional description/keywords.
        
        Args:
            relationship_id: Relationship ID
            embedding: Vector embedding
            description: Optional description
            keywords: Optional keywords
            
        Returns:
            Result dict
        """
        try:
            # Build update query
            set_clauses = ["embedding = $1::vector"]
            params = [json.dumps(embedding)]
            param_index = 2
            
            if description:
                set_clauses.append(f"description = ${param_index}")
                params.append(description)
                param_index += 1
            
            if keywords:
                set_clauses.append(f"keywords = ${param_index}")
                params.append(keywords)
                param_index += 1
            
            params.append(relationship_id)
            
            query = f"""
            UPDATE relationships
            SET {', '.join(set_clauses)}
            WHERE relationship_id = ${param_index}
            RETURNING relationship_id
            """
            
            result = await self.client.execute(query, *params)
            
            return {
                "success": True,
                "relationship_id": relationship_id,
                "message": "Embedding updated successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to update embedding for {relationship_id}: {e}")
            return {
                "success": False,
                "relationship_id": relationship_id,
                "error": str(e)
            }
    
    async def get_embedding_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about relationship embeddings.
        
        Returns:
            Stats dict with counts
        """
        try:
            # Total relationships
            total_result = await self.client.fetch(
                "SELECT COUNT(*) as cnt FROM relationships"
            )
            total = total_result[0]["cnt"] if total_result else 0
            
            # With embeddings
            with_emb_result = await self.client.fetch(
                "SELECT COUNT(*) as cnt FROM relationships WHERE embedding IS NOT NULL"
            )
            with_embeddings = with_emb_result[0]["cnt"] if with_emb_result else 0
            
            # Without embeddings
            without_embeddings = total - with_embeddings
            
            # Percentage complete
            percentage = (with_embeddings / total * 100) if total > 0 else 0
            
            return {
                "total_relationships": total,
                "with_embeddings": with_embeddings,
                "without_embeddings": without_embeddings,
                "percentage_complete": round(percentage, 2),
                "status": "complete" if without_embeddings == 0 else "in_progress"
            }
            
        except Exception as e:
            logger.error(f"Failed to get embedding statistics: {e}")
            return {
                "error": str(e),
                "total_relationships": 0,
                "with_embeddings": 0,
                "without_embeddings": 0,
                "percentage_complete": 0
            }
    
    async def ensure_relationship_embedding(
        self, 
        relationship_id: str,
        embedding_func: Optional[Callable] = None
    ) -> Optional[List[float]]:
        """
        Ensure a relationship has an embedding, generating if necessary.
        
        This is a convenience method that combines get + generate + update.
        
        Args:
            relationship_id: Relationship ID
            embedding_func: Function to generate embedding(text) -> List[float]
            
        Returns:
            Embedding vector or None
        """
        try:
            # Check current state
            query = """
            SELECT source_id, target_id, relationship_type, description, keywords, embedding
            FROM relationships
            WHERE relationship_id = $1
            """
            row = await self.client.fetchrow(query, relationship_id)
            
            if not row:
                logger.warning(f"Relationship {relationship_id} not found")
                return None
            
            # Return existing embedding
            if row.get("embedding"):
                emb = row["embedding"]
                if isinstance(emb, str):
                    emb = json.loads(emb)
                return emb
            
            # Need to generate
            if not embedding_func:
                logger.warning(f"No embedding function provided for {relationship_id}")
                return None
            
            # Generate description
            desc = row.get("description") or f"{row['source_id']} {row['relationship_type']} {row['target_id']}"
            
            # Generate embedding
            embedding = embedding_func(desc)
            
            if embedding:
                # Update database
                await self.update_relationship_embedding(
                    relationship_id=relationship_id,
                    embedding=embedding,
                    description=desc,
                    keywords=row.get("keywords") or row["relationship_type"]
                )
                
                logger.debug(f"Generated embedding for relationship {relationship_id}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to ensure embedding for {relationship_id}: {e}")
            return None


# Factory function for creating storage instance
async def create_kg_storage(config: Dict[str, Any]) -> KGStorage:
    """Create KGStorage instance with configuration."""
    postgres_client = await init_postgres_client(config)
    return KGStorage(postgres_client)


# Example usage
async def example_usage():
    """Example usage of KGStorage."""
    config = {
        "host": "localhost",
        "port": 5432,
        "database": "kg_rag",
        "user": "postgres",
        "password": "postgres",
        "min_connections": 2,
        "max_connections": 20
    }
    
    storage = await create_kg_storage(config)
    
    # Health check
    health = await storage.health_check()
    print(f"Health check: {health}")
    
    # Create entity
    entity = Entity(
        entity_id="test_entity_1",
        entity_type="person",
        name="John Doe",
        description="Test person entity",
        properties={"age": 30, "occupation": "engineer"}
    )
    
    result = await storage.create_entity(entity)
    print(f"Create entity: {result}")
    
    # Get entity
    retrieved_entity = await storage.get_entity("test_entity_1")
    print(f"Retrieved entity: {retrieved_entity}")
    
    # Search chunks (if you have embeddings)
    # search_results = await storage.search_chunks(
    #     query_vector=[0.1] * 768,  # Example embedding
    #     limit=5
    # )
    # print(f"Search results: {len(search_results)} chunks")
    
    # Get statistics
    stats = await storage.get_statistics()
    print(f"Statistics: {stats}")
    
    await storage.client.disconnect()


if __name__ == "__main__":
    asyncio.run(example_usage())
