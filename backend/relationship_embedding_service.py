#!/usr/bin/env python3
"""
Relationship Embedding Service

Provides centralized embedding generation for relationships with:
1. Embedding generation from relationship data
2. Lazy/on-demand generation with caching
3. Batch processing capabilities
4. Queue management for background tasks

This service supports the 3-phase embedding strategy:
- Phase 1: Generate embeddings during upload
- Phase 2: Lazy generation when querying
- Phase 3: Batch backfill for existing relationships
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Ollama embedding function from pgvector_api
# This avoids circular imports
_ollama_embedding_func: Optional[Callable] = None

def set_ollama_embedding_func(func: Callable):
    """Set the Ollama embedding function from pgvector_api."""
    global _ollama_embedding_func
    _ollama_embedding_func = func

def get_ollama_embedding_safe(text: str) -> Optional[List[float]]:
    """Safely get embedding, returns None if function not set or fails."""
    global _ollama_embedding_func
    if _ollama_embedding_func is None:
        return None
    try:
        return _ollama_embedding_func(text)
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return None


@dataclass
class EmbeddingTask:
    """Task for embedding generation."""
    relationship_id: str
    source_id: str
    target_id: str
    relationship_type: str
    description: Optional[str] = None
    keywords: Optional[str] = None
    priority: int = 1  # Higher = more important
    created_at: float = 0.0
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class RelationshipEmbeddingService:
    """
    Service for managing relationship embeddings.
    
    Features:
    - Generate embeddings from relationship descriptions
    - Queue management for batch processing
    - Lazy/on-demand generation
    - Background processing
    """
    
    def __init__(self, storage_client=None, batch_size: int = 200, max_concurrent: int = 10):
        self.storage = storage_client
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False
        self._stats = {
            "generated": 0,
            "failed": 0,
            "skipped": 0,
            "last_processed": None
        }
        self._cache: Dict[str, List[float]] = {}  # In-memory cache
        self._cache_max_size = 1000
        # Semaphore to limit concurrent embedding generation (prevents overwhelming Ollama)
        self._embedding_semaphore = asyncio.Semaphore(max_concurrent)
        # Retry settings
        self._max_retries = 3
        self._retry_delay = 1.0
        
    def _generate_description(self, source_id: str, target_id: str, 
                             relationship_type: str, 
                             existing_description: Optional[str] = None) -> str:
        """
        Generate a human-readable description for embedding.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID  
            relationship_type: Type of relationship
            existing_description: Optional existing description to use
            
        Returns:
            Description string suitable for embedding
        """
        if existing_description and len(existing_description) > 10:
            return existing_description
        
        # Generate from components
        desc = f"{source_id} {relationship_type} {target_id}"
        return desc
    
    def _generate_keywords(self, source_id: str, target_id: str, 
                          relationship_type: str,
                          existing_keywords: Optional[str] = None) -> str:
        """Generate keywords for the relationship."""
        if existing_keywords:
            return existing_keywords
        
        # Extract meaningful keywords
        keywords = [relationship_type]
        
        # Add entity name components (simplified)
        for entity_id in [source_id, target_id]:
            if '_' in entity_id:
                # Extract name after prefix like "ent_"
                parts = entity_id.split('_')
                if len(parts) > 1:
                    keywords.append(parts[-1])
        
        return ', '.join(keywords)
    
    async def generate_embedding(self, 
                                 source_id: str, 
                                 target_id: str,
                                 relationship_type: str,
                                 description: Optional[str] = None,
                                 keywords: Optional[str] = None,
                                 retry_count: int = 0) -> Optional[List[float]]:
        """
        Generate embedding for a relationship with semaphore control and retry logic.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship
            description: Optional description to embed
            keywords: Optional keywords
            retry_count: Current retry attempt (internal use)
            
        Returns:
            Embedding vector or None if generation fails
        """
        # Generate description if not provided
        desc = self._generate_description(
            source_id, target_id, relationship_type, description
        )
        
        # Check cache first
        cache_key = hashlib.md5(desc.encode()).hexdigest()
        if cache_key in self._cache:
            logger.debug(f"Cache hit for relationship embedding")
            return self._cache[cache_key]
        
        # Use semaphore to limit concurrent embedding generation
        async with self._embedding_semaphore:
            try:
                # Run embedding generation in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                embedding = await loop.run_in_executor(
                    None,  # Default executor
                    get_ollama_embedding_safe,
                    desc
                )
                
                if embedding:
                    # Add to cache
                    if len(self._cache) >= self._cache_max_size:
                        # Remove oldest entries
                        self._cache.pop(next(iter(self._cache)))
                    self._cache[cache_key] = embedding
                    
                    self._stats["generated"] += 1
                    return embedding
                else:
                    # Retry logic
                    if retry_count < self._max_retries:
                        logger.warning(f"Embedding generation failed, retrying {retry_count + 1}/{self._max_retries}...")
                        await asyncio.sleep(self._retry_delay * (retry_count + 1))  # Exponential backoff
                        return await self.generate_embedding(
                            source_id, target_id, relationship_type, 
                            description, keywords, retry_count + 1
                        )
                    else:
                        self._stats["failed"] += 1
                        return None
                        
            except Exception as e:
                logger.error(f"Embedding generation error: {e}")
                # Retry logic
                if retry_count < self._max_retries:
                    logger.warning(f"Embedding generation error, retrying {retry_count + 1}/{self._max_retries}...")
                    await asyncio.sleep(self._retry_delay * (retry_count + 1))
                    return await self.generate_embedding(
                        source_id, target_id, relationship_type,
                        description, keywords, retry_count + 1
                    )
                else:
                    self._stats["failed"] += 1
                    return None
    
    async def create_relationship_with_embedding(self,
                                                  relationship_id: str,
                                                  source_id: str,
                                                  target_id: str,
                                                  relationship_type: str,
                                                  properties: Optional[Dict] = None,
                                                  storage=None) -> Dict[str, Any]:
        """
        Create a relationship with embedding (Phase 1: Upload-time generation).
        
        This should be called when creating new relationships during file upload.
        
        Args:
            relationship_id: Unique relationship ID
            source_id: Source entity ID
            target_id: Target entity ID
            relationship_type: Type of relationship
            properties: Optional properties dict
            storage: KGStorage instance
            
        Returns:
            Result dict with success status and embedding info
        """
        from storage import Relationship
        
        # Extract description and keywords from properties if available
        props = properties or {}
        description = props.get('description')
        keywords = props.get('keywords')
        
        # Generate description if not in properties
        description = self._generate_description(
            source_id, target_id, relationship_type, description
        )
        
        # Generate keywords if not in properties
        keywords = self._generate_keywords(
            source_id, target_id, relationship_type, keywords
        )
        
        # Generate embedding
        embedding = await self.generate_embedding(
            source_id, target_id, relationship_type, description, keywords
        )
        
        # Create relationship object
        rel = Relationship(
            relationship_id=relationship_id,
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            properties=props,
            description=description,
            keywords=keywords,
            embedding=embedding
        )
        
        # Store in database if storage provided
        if storage:
            try:
                result = await storage.create_relationship(rel)
                return {
                    "success": result.get("success", False),
                    "relationship_id": relationship_id,
                    "has_embedding": embedding is not None,
                    "embedding_dim": len(embedding) if embedding else 0
                }
            except Exception as e:
                logger.error(f"Failed to create relationship with embedding: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "relationship_id": relationship_id
                }
        
        return {
            "success": True,
            "relationship": rel,
            "has_embedding": embedding is not None
        }
    
    async def ensure_embedding(self, 
                               relationship_id: str,
                               source_id: Optional[str] = None,
                               target_id: Optional[str] = None,
                               relationship_type: Optional[str] = None,
                               storage=None) -> Optional[List[float]]:
        """
        Ensure a relationship has an embedding (Phase 2: Lazy generation).
        
        This checks if embedding exists, generates if missing, and updates the DB.
        
        Args:
            relationship_id: Relationship ID to check
            source_id: Source entity ID (optional, fetched if not provided)
            target_id: Target entity ID (optional, fetched if not provided)
            relationship_type: Relationship type (optional, fetched if not provided)
            storage: KGStorage instance
            
        Returns:
            Embedding vector or None
        """
        if not storage:
            return None
        
        try:
            # Check if relationship already has embedding
            query = """
            SELECT source_id, target_id, relationship_type, description, keywords, embedding
            FROM relationships
            WHERE relationship_id = $1
            """
            row = await storage.client.fetchrow(query, relationship_id)
            
            if not row:
                logger.warning(f"Relationship {relationship_id} not found")
                return None
            
            # If already has embedding, return it
            if row.get("embedding"):
                embedding = row["embedding"]
                if isinstance(embedding, str):
                    embedding = json.loads(embedding)
                return embedding
            
            # Need to generate embedding
            src = source_id or row["source_id"]
            tgt = target_id or row["target_id"]
            rel_type = relationship_type or row["relationship_type"]
            desc = row.get("description")
            keywords = row.get("keywords")
            
            # Generate embedding
            embedding = await self.generate_embedding(src, tgt, rel_type, desc, keywords)
            
            if embedding:
                # Update database with embedding
                update_query = """
                UPDATE relationships
                SET embedding = $1::vector,
                    description = COALESCE($2, description),
                    keywords = COALESCE($3, keywords)
                WHERE relationship_id = $4
                """
                
                desc = desc or self._generate_description(src, tgt, rel_type)
                keywords = keywords or self._generate_keywords(src, tgt, rel_type)
                
                await storage.client.execute(
                    update_query,
                    json.dumps(embedding),
                    desc,
                    keywords,
                    relationship_id
                )
                
                logger.info(f"Generated lazy embedding for relationship {relationship_id}")
                self._stats["generated"] += 1
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to ensure embedding for {relationship_id}: {e}")
            return None
    
    async def batch_generate_embeddings(self, 
                                        relationship_ids: Optional[List[str]] = None,
                                        limit: Optional[int] = None,
                                        storage=None) -> Dict[str, Any]:
        """
        Generate embeddings for multiple relationships (Phase 3: Batch backfill).
        
        Args:
            relationship_ids: Specific IDs to process (None = all without embeddings)
            limit: Maximum number to process
            storage: KGStorage instance
            
        Returns:
            Stats dict with processing results
        """
        if not storage:
            return {"success": False, "error": "No storage provided"}
        
        stats = {
            "processed": 0,
            "generated": 0,
            "failed": 0,
            "skipped": 0
        }
        
        try:
            # Get relationships without embeddings
            if relationship_ids:
                query = """
                SELECT relationship_id, source_id, target_id, relationship_type, 
                       description, keywords, embedding
                FROM relationships
                WHERE relationship_id = ANY($1)
                ORDER BY created_at DESC
                """
                rows = await storage.client.fetch(query, relationship_ids)
            else:
                query = """
                SELECT relationship_id, source_id, target_id, relationship_type,
                       description, keywords, embedding
                FROM relationships
                WHERE embedding IS NULL
                ORDER BY created_at DESC
                LIMIT $1
                """
                rows = await storage.client.fetch(query, limit or 1000)
            
            logger.info(f"Batch processing {len(rows)} relationships for embeddings")
            
            # Process in batches
            for i in range(0, len(rows), self.batch_size):
                batch = rows[i:i + self.batch_size]
                
                # Process batch concurrently
                tasks = []
                for row in batch:
                    task = self._process_single_relationship(row, storage)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Update stats
                for result in results:
                    stats["processed"] += 1
                    if isinstance(result, Exception):
                        stats["failed"] += 1
                    elif result.get("generated"):
                        stats["generated"] += 1
                    elif result.get("skipped"):
                        stats["skipped"] += 1
                    else:
                        stats["failed"] += 1
                
                logger.info(f"Batch progress: {stats['processed']}/{len(rows)} "
                          f"(generated: {stats['generated']}, failed: {stats['failed']})")
                
                # Delay between batches to avoid overwhelming Ollama and database
                # Longer delay for larger batches to allow system recovery
                delay = min(2.0, max(0.5, self.batch_size / 200))  # 0.5-2s based on batch size
                await asyncio.sleep(delay)
            
            self._stats["last_processed"] = datetime.now().isoformat()
            return {
                "success": True,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"Batch generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "stats": stats
            }
    
    async def _process_single_relationship(self, row: Dict, storage) -> Dict[str, Any]:
        """Process a single relationship for embedding with timeout handling."""
        rel_id = row["relationship_id"]
        
        try:
            # Skip if already has embedding
            if row.get("embedding"):
                return {"skipped": True, "relationship_id": rel_id}
            
            # Generate embedding with timeout (30 seconds max)
            try:
                embedding = await asyncio.wait_for(
                    self.generate_embedding(
                        row["source_id"],
                        row["target_id"],
                        row["relationship_type"],
                        row.get("description"),
                        row.get("keywords")
                    ),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Embedding generation timeout for {rel_id}")
                return {"failed": True, "relationship_id": rel_id, "reason": "timeout"}
            
            if embedding:
                # Update database with timeout (10 seconds max)
                update_query = """
                UPDATE relationships
                SET embedding = $1::vector,
                    description = COALESCE($2, description),
                    keywords = COALESCE($3, keywords)
                WHERE relationship_id = $4
                """
                
                desc = row.get("description") or self._generate_description(
                    row["source_id"], row["target_id"], row["relationship_type"]
                )
                keywords = row.get("keywords") or self._generate_keywords(
                    row["source_id"], row["target_id"], row["relationship_type"]
                )
                
                try:
                    await asyncio.wait_for(
                        storage.client.execute(
                            update_query,
                            json.dumps(embedding),
                            desc,
                            keywords,
                            rel_id
                        ),
                        timeout=10.0
                    )
                    return {"generated": True, "relationship_id": rel_id}
                except asyncio.TimeoutError:
                    logger.warning(f"Database update timeout for {rel_id}")
                    return {"failed": True, "relationship_id": rel_id, "reason": "db_timeout"}
            else:
                return {"failed": True, "relationship_id": rel_id, "reason": "generation_failed"}
                
        except Exception as e:
            logger.error(f"Failed to process relationship {rel_id}: {e}")
            return {"failed": True, "relationship_id": rel_id, "reason": str(e)}
            return {"failed": True, "error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            **self._stats,
            "cache_size": len(self._cache),
            "queue_size": self._task_queue.qsize() if hasattr(self._task_queue, 'qsize') else 0
        }
    
    async def start_background_processor(self, storage, interval_seconds: int = 60):
        """
        Start background processor for continuous batch processing.
        
        Args:
            storage: KGStorage instance
            interval_seconds: Seconds between batch processing runs
        """
        self._processing = True
        logger.info(f"Starting background embedding processor (interval: {interval_seconds}s)")
        
        while self._processing:
            try:
                # Process a batch
                result = await self.batch_generate_embeddings(
                    limit=self.batch_size,
                    storage=storage
                )
                
                if result.get("success"):
                    stats = result.get("stats", {})
                    if stats.get("processed", 0) > 0:
                        logger.info(f"Background batch complete: {stats}")
                    else:
                        logger.debug("No relationships to process in background")
                
                # Wait before next batch
                await asyncio.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"Background processor error: {e}")
                await asyncio.sleep(interval_seconds)
    
    def stop_background_processor(self):
        """Stop the background processor."""
        self._processing = False
        logger.info("Background embedding processor stopped")


# Global service instance
_embedding_service: Optional[RelationshipEmbeddingService] = None

def get_embedding_service(storage=None, batch_size: int = 500) -> RelationshipEmbeddingService:
    """Get or create global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = RelationshipEmbeddingService(
            storage_client=storage,
            batch_size=batch_size
        )
    return _embedding_service


def reset_embedding_service():
    """Reset the global embedding service (useful for testing)."""
    global _embedding_service
    _embedding_service = None
