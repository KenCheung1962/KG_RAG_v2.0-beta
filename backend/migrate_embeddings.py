#!/usr/bin/env python3
"""
Backfill Migration: Generate embeddings for existing chunks
This script generates 768d embeddings using Ollama nomic-embed-text for all chunks with NULL embeddings.
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from typing import List, Optional

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the embedding function and storage
from pgvector_api import EMBEDDING_DIMENSION
from storage import create_kg_storage

# Import Ollama client directly for async usage
from ollama_client import OllamaClient

# Initialize Ollama client
_ollama_client = OllamaClient(
    host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
    model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
)

async def get_embedding_async(text: str) -> List[float]:
    """Generate embedding using Ollama (async version)."""
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

# Configuration
BATCH_SIZE = 50  # Process chunks in batches
DELAY_BETWEEN_CHUNKS = 0.1  # Seconds between API calls to avoid rate limiting
DELAY_BETWEEN_BATCHES = 1.0  # Seconds between batches


async def get_chunks_batch(storage, offset: int, limit: int):
    """Get a batch of chunks that have NULL embeddings."""
    query = """
    SELECT chunk_id, content 
    FROM chunks 
    WHERE embedding IS NULL 
    ORDER BY chunk_id
    LIMIT $1 OFFSET $2
    """
    try:
        rows = await storage.client.fetch(query, limit, offset)
        return [(row['chunk_id'], row['content']) for row in rows]
    except Exception as e:
        print(f"[ERROR] Failed to fetch chunks batch: {type(e).__name__}: {e}")
        return []


async def count_chunks_without_embeddings(storage) -> int:
    """Count chunks without embeddings."""
    query = "SELECT COUNT(*) as count FROM chunks WHERE embedding IS NULL"
    try:
        result = await storage.client.fetchrow(query)
        return result['count'] if result else 0
    except Exception as e:
        print(f"[ERROR] Failed to count chunks: {e}")
        return 0


async def update_chunk_embedding(storage, chunk_id: str, embedding: List[float]):
    """Update a chunk with its embedding."""
    import json
    
    # pgvector expects vector type, not json
    # Convert list to string format: [0.1, 0.2, ...]
    vector_str = '[' + ','.join(str(x) for x in embedding) + ']'
    
    query = """
    UPDATE chunks 
    SET embedding = $1::vector
    WHERE chunk_id = $2
    """
    try:
        await storage.client.execute(query, vector_str, chunk_id)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update chunk {chunk_id}: {e}")
        return False


async def process_chunk(storage, chunk_id: str, content: str, index: int, total: int) -> bool:
    """Process a single chunk: generate embedding and update database."""
    try:
        # Generate embedding using Ollama (async)
        embedding = await get_embedding_async(content)
        
        # Verify embedding dimension
        if len(embedding) != EMBEDDING_DIMENSION:
            print(f"[ERROR] Chunk {chunk_id}: Invalid embedding dimension {len(embedding)}, expected {EMBEDDING_DIMENSION}")
            return False
        
        # Update database
        success = await update_chunk_embedding(storage, chunk_id, embedding)
        
        if success:
            progress = (index + 1) / total * 100
            print(f"[OK] {index + 1}/{total} ({progress:.1f}%) - Chunk {chunk_id[:20]}... - Embedding generated ({len(embedding)}d)")
            return True
        else:
            print(f"[FAIL] {index + 1}/{total} - Chunk {chunk_id[:20]}... - Database update failed")
            return False
            
    except Exception as e:
        print(f"[ERROR] Chunk {chunk_id}: {e}")
        return False


async def run_migration():
    """Main migration function."""
    print("=" * 80)
    print("BACKFILL MIGRATION: Generate embeddings for existing chunks")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Embedding model: Ollama nomic-embed-text ({EMBEDDING_DIMENSION}d)")
    print(f"Batch size: {BATCH_SIZE}")
    print()
    
    # Database config
    config = {
        "host": os.getenv('PGVECTOR_HOST', 'localhost'),
        "port": int(os.getenv('PGVECTOR_PORT', '5432')),
        "database": os.getenv('PGVECTOR_DATABASE', 'kg_rag'),
        "user": os.getenv('PGVECTOR_USER', 'postgres'),
        "password": os.getenv('PGVECTOR_PASSWORD', 'postgres'),
        "min_connections": 2,
        "max_connections": 20,
    }
    
    # Initialize storage
    print("[INFO] Initializing storage connection...")
    storage = await create_kg_storage(config)
    
    # Count total chunks without embeddings
    print("[INFO] Counting chunks without embeddings...")
    total_chunks = await count_chunks_without_embeddings(storage)
    
    if total_chunks == 0:
        print("[INFO] No chunks found with NULL embeddings. Migration not needed.")
        return
    
    print(f"[INFO] Found {total_chunks} chunks without embeddings")
    print()
    
    # Statistics
    successful = 0
    failed = 0
    processed = 0
    start_time = time.time()
    offset = 0
    
    # Process in batches - fetch from DB as we go
    while processed < total_chunks:
        # Fetch batch from database
        batch = await get_chunks_batch(storage, offset, BATCH_SIZE)
        
        if not batch:
            # No more chunks or error
            print(f"[INFO] No more chunks to process at offset {offset}")
            break
        
        batch_num = (offset // BATCH_SIZE) + 1
        total_batches = (total_chunks + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"[BATCH {batch_num}/{total_batches}] Processing {len(batch)} chunks (offset: {offset})")
        
        # Process each chunk in the batch
        for i, (chunk_id, content) in enumerate(batch):
            global_index = processed + i
            
            success = await process_chunk(storage, chunk_id, content, global_index, total_chunks)
            if success:
                successful += 1
            else:
                failed += 1
            
            # Add delay between chunks to avoid overwhelming Ollama
            if i < len(batch) - 1:  # Don't delay after last chunk in batch
                await asyncio.sleep(DELAY_BETWEEN_CHUNKS)
        
        processed += len(batch)
        offset += len(batch)
        
        # Delay between batches
        if processed < total_chunks:
            print(f"[BATCH] Completed {processed}/{total_chunks}. Pausing {DELAY_BETWEEN_BATCHES}s...")
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)
    
    # Summary
    elapsed_time = time.time() - start_time
    print()
    print("=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print(f"Finished at: {datetime.now().isoformat()}")
    print(f"Total chunks processed: {total_chunks}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Time elapsed: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
    print(f"Average speed: {total_chunks/elapsed_time:.1f} chunks/second")
    print()
    
    if failed > 0:
        print(f"[WARNING] {failed} chunks failed. You may need to re-run the migration.")
    else:
        print("[SUCCESS] All chunks have been updated with embeddings!")


async def check_status():
    """Check current status of embeddings in database."""
    print("=" * 80)
    print("DATABASE EMBEDDING STATUS CHECK")
    print("=" * 80)
    
    # Database config
    config = {
        "host": os.getenv('PGVECTOR_HOST', 'localhost'),
        "port": int(os.getenv('PGVECTOR_PORT', '5432')),
        "database": os.getenv('PGVECTOR_DATABASE', 'kg_rag'),
        "user": os.getenv('PGVECTOR_USER', 'postgres'),
        "password": os.getenv('PGVECTOR_PASSWORD', 'postgres'),
        "min_connections": 2,
        "max_connections": 20,
    }
    
    storage = await create_kg_storage(config)
    
    # Count total chunks
    total_query = "SELECT COUNT(*) as count FROM chunks"
    total_result = await storage.client.fetchrow(total_query)
    total_chunks = total_result['count'] if total_result else 0
    
    # Count chunks with embeddings
    with_emb_query = "SELECT COUNT(*) as count FROM chunks WHERE embedding IS NOT NULL"
    with_emb_result = await storage.client.fetchrow(with_emb_query)
    chunks_with_emb = with_emb_result['count'] if with_emb_result else 0
    
    # Count chunks without embeddings
    without_emb_query = "SELECT COUNT(*) as count FROM chunks WHERE embedding IS NULL"
    without_emb_result = await storage.client.fetchrow(without_emb_query)
    chunks_without_emb = without_emb_result['count'] if without_emb_result else 0
    
    print(f"Total chunks: {total_chunks}")
    print(f"Chunks WITH embeddings: {chunks_with_emb} ({chunks_with_emb/total_chunks*100:.1f}%)")
    print(f"Chunks WITHOUT embeddings: {chunks_without_emb} ({chunks_without_emb/total_chunks*100:.1f}%)")
    print()
    
    if chunks_without_emb == 0:
        print("[OK] All chunks have embeddings. No migration needed.")
    else:
        print(f"[ACTION NEEDED] Run migration to generate {chunks_without_emb} embeddings")
    
    return chunks_without_emb


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backfill embeddings for existing chunks')
    parser.add_argument('--check', action='store_true', help='Check current status without running migration')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for processing (default: 50)')
    parser.add_argument('--delay', type=float, default=0.1, help='Delay between chunks in seconds (default: 0.1)')
    parser.add_argument('--yes', '-y', action='store_true', help='Skip confirmation and run immediately')
    
    args = parser.parse_args()
    
    # Update configuration from args
    global BATCH_SIZE, DELAY_BETWEEN_CHUNKS
    BATCH_SIZE = args.batch_size
    DELAY_BETWEEN_CHUNKS = args.delay
    
    if args.check:
        await check_status()
    else:
        # First check status
        chunks_without = await check_status()
        
        if chunks_without > 0:
            if args.yes:
                # Skip confirmation
                print("[AUTO] Starting migration immediately (--yes flag set)")
                await run_migration()
            else:
                # Confirm before running
                print()
                confirm = input(f"Generate embeddings for {chunks_without} chunks? This will take approximately {chunks_without * (DELAY_BETWEEN_CHUNKS + 0.5)/60:.0f} minutes. [y/N]: ")
                
                if confirm.lower() == 'y':
                    await run_migration()
                else:
                    print("[CANCELLED] Migration aborted.")

if __name__ == "__main__":
    asyncio.run(main())
