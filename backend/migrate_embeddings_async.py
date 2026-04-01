#!/usr/bin/env python3
"""
Async Parallel Backfill Migration: Uses asyncio with semaphore for controlled concurrency
"""

import asyncio
import os
import sys
import time
import json
from datetime import datetime
from typing import List, Tuple

# Add necessary paths
# Using local storage.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pgvector_api import EMBEDDING_DIMENSION
from ollama_client import OllamaClient

# Configuration
DB_CONFIG = {
    "host": os.getenv('PGVECTOR_HOST', 'localhost'),
    "port": int(os.getenv('PGVECTOR_PORT', '5432')),
    "database": os.getenv('PGVECTOR_DATABASE', 'kg_rag'),
    "user": os.getenv('PGVECTOR_USER', 'postgres'),
    "password": os.getenv('PGVECTOR_PASSWORD', 'postgres'),
}

# Concurrency settings
MAX_CONCURRENT_EMBEDDINGS = 10  # Number of parallel Ollama requests
MAX_CONCURRENT_DB_UPDATES = 20  # Number of parallel DB updates
BATCH_FETCH_SIZE = 500  # Fetch this many chunks at a time

# Global clients
_ollama_client = None
_db_pool = None


async def init_clients():
    """Initialize Ollama and database clients."""
    global _ollama_client, _db_pool
    
    _ollama_client = OllamaClient(
        host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
        model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
    )
    
    import asyncpg
    _db_pool = await asyncpg.create_pool(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        database=DB_CONFIG['database'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        min_size=5,
        max_size=20,
        command_timeout=60
    )


async def close_clients():
    """Close all clients."""
    global _db_pool
    if _db_pool:
        await _db_pool.close()


async def get_embedding_async(text: str) -> List[float]:
    """Generate embedding using Ollama."""
    try:
        embeddings = await _ollama_client.embed([text[:8000]])
        if embeddings and len(embeddings) > 0:
            embedding = embeddings[0]
            if embedding and len(embedding) == EMBEDDING_DIMENSION:
                return embedding
        return [0.0] * EMBEDDING_DIMENSION
    except Exception as e:
        print(f"[ERROR] Embedding failed: {e}")
        return [0.0] * EMBEDDING_DIMENSION


async def update_chunk_embedding(chunk_id: str, embedding: List[float]) -> bool:
    """Update a chunk with its embedding."""
    try:
        vector_str = '[' + ','.join(str(x) for x in embedding) + ']'
        async with _db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE chunks SET embedding = $1::vector WHERE chunk_id = $2",
                vector_str, chunk_id
            )
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update {chunk_id}: {e}")
        return False


async def process_single_chunk(chunk_id: str, content: str, 
                                sem_embedding: asyncio.Semaphore,
                                sem_db: asyncio.Semaphore) -> Tuple[str, bool]:
    """Process a single chunk with semaphore-controlled concurrency."""
    # Generate embedding with concurrency limit
    async with sem_embedding:
        embedding = await get_embedding_async(content)
    
    # Update database with concurrency limit
    async with sem_db:
        success = await update_chunk_embedding(chunk_id, embedding)
    
    return chunk_id, success


async def get_total_count() -> int:
    """Get total chunks without embeddings."""
    async with _db_pool.acquire() as conn:
        result = await conn.fetchval("SELECT COUNT(*) FROM chunks WHERE embedding IS NULL")
        return result or 0


async def fetch_batch(offset: int, limit: int) -> List[Tuple[str, str]]:
    """Fetch a batch of chunks."""
    async with _db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT chunk_id, content FROM chunks WHERE embedding IS NULL ORDER BY chunk_id LIMIT $1 OFFSET $2",
            limit, offset
        )
        return [(row['chunk_id'], row['content']) for row in rows]


async def run_migration():
    """Main migration function with async parallelism."""
    print("=" * 80)
    print("ASYNC PARALLEL BACKFILL MIGRATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Max concurrent embeddings: {MAX_CONCURRENT_EMBEDDINGS}")
    print(f"Max concurrent DB updates: {MAX_CONCURRENT_DB_UPDATES}")
    print()
    
    # Initialize
    await init_clients()
    
    try:
        # Get total count
        print("[INFO] Counting chunks...")
        total = await get_total_count()
        
        if total == 0:
            print("[INFO] No chunks need migration!")
            return
        
        print(f"[INFO] Total chunks to process: {total}")
        print()
        
        # Create semaphores for concurrency control
        sem_embedding = asyncio.Semaphore(MAX_CONCURRENT_EMBEDDINGS)
        sem_db = asyncio.Semaphore(MAX_CONCURRENT_DB_UPDATES)
        
        start_time = time.time()
        processed = 0
        success = 0
        failed = 0
        offset = 0
        
        while processed < total:
            # Fetch batch
            batch = await fetch_batch(offset, BATCH_FETCH_SIZE)
            
            if not batch:
                break
            
            # Process all chunks in batch concurrently
            tasks = [
                process_single_chunk(chunk_id, content, sem_embedding, sem_db)
                for chunk_id, content in batch
            ]
            
            # Wait for all to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count results
            batch_success = sum(1 for r in results if isinstance(r, tuple) and r[1])
            batch_failed = len(results) - batch_success
            
            success += batch_success
            failed += batch_failed
            processed += len(batch)
            offset += len(batch)
            
            # Progress report
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            progress = processed / total * 100
            eta = (total - processed) / rate if rate > 0 else 0
            
            print(f"[BATCH] Processed: {len(batch)}, Success: {batch_success}, Failed: {batch_failed}")
            print(f"[PROGRESS] {processed}/{total} ({progress:.1f}%) | "
                  f"Rate: {rate:.1f} chunks/sec | ETA: {eta/3600:.1f} hours")
            print()
        
        # Final summary
        elapsed = time.time() - start_time
        print("=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print(f"Total: {processed}, Success: {success}, Failed: {failed}")
        print(f"Time: {elapsed/3600:.1f} hours, Rate: {processed/elapsed:.1f} chunks/sec")
        
    finally:
        await close_clients()


if __name__ == "__main__":
    asyncio.run(run_migration())
