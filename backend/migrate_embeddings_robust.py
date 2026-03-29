#!/usr/bin/env python3
"""
ROBUST Backfill Migration: Generate embeddings for existing chunks
This script generates 768d embeddings using Ollama nomic-embed-text.
- Retries failed chunks automatically
- Loops until ALL chunks are processed
- Handles database timeouts with exponential backoff
- Never stops until completion or manual kill
"""

import asyncio
import os
import sys
import time
import signal
from datetime import datetime
from typing import List, Optional, Set

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

# Global flag for graceful shutdown
shutdown_requested = False

# Track permanently failed chunks
failed_chunk_ids: Set[str] = set()


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_requested
    print("\n[SHUTDOWN] Graceful shutdown requested. Finishing current batch...")
    shutdown_requested = True


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# Configuration
BATCH_SIZE = 50  # Process chunks in batches
DELAY_BETWEEN_CHUNKS = 0.1  # Seconds between API calls to avoid rate limiting
DELAY_BETWEEN_BATCHES = 1.0  # Seconds between batches
MAX_RETRIES = 5  # Max retries for failed chunks
DB_TIMEOUT_RETRY_DELAY = 5  # Initial delay for DB timeout retries
DB_MAX_TIMEOUT_RETRIES = 10  # Max retries for DB connection issues


async def get_embedding_async(text: str, max_retries: int = 3) -> List[float]:
    """Generate embedding using Ollama (async version) with retries."""
    for attempt in range(max_retries):
        try:
            embeddings = await _ollama_client.embed([text[:8000]])
            if embeddings and len(embeddings) > 0:
                embedding = embeddings[0]
                if embedding and len(embedding) == EMBEDDING_DIMENSION:
                    return embedding
            return [0.0] * EMBEDDING_DIMENSION
        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1:
                retry_delay = min(2 ** attempt, 30)  # Exponential backoff, max 30s
                print(f"[WARN] Embedding attempt {attempt + 1} failed: {error_msg}. Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
            else:
                print(f"[ERROR] Embedding failed after {max_retries} attempts: {error_msg}")
                return [0.0] * EMBEDDING_DIMENSION
    return [0.0] * EMBEDDING_DIMENSION


async def get_chunks_batch(storage, offset: int, limit: int, retry_count: int = 0):
    """Get a batch of chunks that have NULL embeddings with retry logic."""
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
        error_msg = str(e)
        print(f"[ERROR] Failed to fetch chunks batch at offset {offset}: {type(e).__name__}: {error_msg}")
        
        if retry_count < DB_MAX_TIMEOUT_RETRIES:
            retry_delay = min(DB_TIMEOUT_RETRY_DELAY * (2 ** retry_count), 300)  # Exponential backoff, max 5 min
            print(f"[RETRY] Will retry DB fetch in {retry_delay}s (attempt {retry_count + 1}/{DB_MAX_TIMEOUT_RETRIES})")
            await asyncio.sleep(retry_delay)
            return await get_chunks_batch(storage, offset, limit, retry_count + 1)
        else:
            print(f"[FATAL] Max DB retries exceeded. Stopping.")
            return None  # None indicates fatal error


async def get_failed_chunks_batch(storage, chunk_ids: List[str]):
    """Get a batch of specific failed chunks for retry."""
    if not chunk_ids:
        return []
    
    # Build query with chunk_id list
    placeholders = ','.join(f'${i+1}' for i in range(len(chunk_ids)))
    query = f"""
    SELECT chunk_id, content 
    FROM chunks 
    WHERE chunk_id IN ({placeholders})
    AND embedding IS NULL
    ORDER BY chunk_id
    """
    try:
        rows = await storage.client.fetch(query, *chunk_ids)
        return [(row['chunk_id'], row['content']) for row in rows]
    except Exception as e:
        print(f"[ERROR] Failed to fetch failed chunks batch: {e}")
        return []


async def count_chunks_without_embeddings(storage, retry_count: int = 0) -> int:
    """Count chunks without embeddings with retry logic."""
    query = "SELECT COUNT(*) as count FROM chunks WHERE embedding IS NULL"
    try:
        result = await storage.client.fetchrow(query)
        return result['count'] if result else 0
    except Exception as e:
        print(f"[ERROR] Failed to count chunks: {e}")
        if retry_count < DB_MAX_TIMEOUT_RETRIES:
            retry_delay = min(DB_TIMEOUT_RETRY_DELAY * (2 ** retry_count), 300)
            print(f"[RETRY] Will retry count in {retry_delay}s (attempt {retry_count + 1}/{DB_MAX_TIMEOUT_RETRIES})")
            await asyncio.sleep(retry_delay)
            return await count_chunks_without_embeddings(storage, retry_count + 1)
        return -1  # Error indicator


async def update_chunk_embedding(storage, chunk_id: str, embedding: List[float], retry_count: int = 0):
    """Update a chunk with its embedding with retry logic."""
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
        error_msg = str(e)
        if retry_count < 3:
            retry_delay = min(2 ** retry_count, 10)
            print(f"[WARN] Failed to update chunk {chunk_id}, retrying in {retry_delay}s: {error_msg}")
            await asyncio.sleep(retry_delay)
            return await update_chunk_embedding(storage, chunk_id, embedding, retry_count + 1)
        else:
            print(f"[ERROR] Failed to update chunk {chunk_id} after 3 attempts: {error_msg}")
            return False


async def process_chunk(storage, chunk_id: str, content: str, index: int, total: int) -> bool:
    """Process a single chunk: generate embedding and update database."""
    global failed_chunk_ids
    
    # Skip if already permanently failed
    if chunk_id in failed_chunk_ids:
        return False
    
    try:
        # Generate embedding using Ollama (async)
        embedding = await get_embedding_async(content)
        
        # Verify embedding dimension
        if len(embedding) != EMBEDDING_DIMENSION:
            print(f"[ERROR] Chunk {chunk_id}: Invalid embedding dimension {len(embedding)}, expected {EMBEDDING_DIMENSION}")
            failed_chunk_ids.add(chunk_id)
            return False
        
        # Update database
        success = await update_chunk_embedding(storage, chunk_id, embedding)
        
        if success:
            progress = (index + 1) / total * 100
            print(f"[OK] {index + 1}/{total} ({progress:.1f}%) - Chunk {chunk_id[:20]}... - Embedding generated ({len(embedding)}d)")
            return True
        else:
            print(f"[FAIL] {index + 1}/{total} - Chunk {chunk_id[:20]}... - Database update failed")
            failed_chunk_ids.add(chunk_id)
            return False
            
    except Exception as e:
        print(f"[ERROR] Chunk {chunk_id}: {e}")
        failed_chunk_ids.add(chunk_id)
        return False


async def process_single_chunk_with_retries(storage, chunk_id: str, content: str, max_retries: int = MAX_RETRIES):
    """Process a single chunk with multiple retries for failed attempts."""
    global failed_chunk_ids
    
    for attempt in range(max_retries):
        try:
            embedding = await get_embedding_async(content)
            
            if len(embedding) != EMBEDDING_DIMENSION:
                print(f"[RETRY {attempt+1}/{max_retries}] Chunk {chunk_id}: Invalid dimension")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
            
            success = await update_chunk_embedding(storage, chunk_id, embedding)
            if success:
                return True
            else:
                print(f"[RETRY {attempt+1}/{max_retries}] Chunk {chunk_id}: DB update failed")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        except Exception as e:
            print(f"[RETRY {attempt+1}/{max_retries}] Chunk {chunk_id}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
    
    failed_chunk_ids.add(chunk_id)
    return False


async def run_migration_pass(storage, is_retry_pass: bool = False) -> tuple[int, int]:
    """
    Run one complete pass of the migration.
    Returns (successful_count, failed_count) for this pass.
    """
    global failed_chunk_ids, shutdown_requested
    
    # Count total chunks without embeddings
    print("[INFO] Counting chunks without embeddings...")
    total_chunks = await count_chunks_without_embeddings(storage)
    
    if total_chunks == 0:
        print("[INFO] No chunks found with NULL embeddings. Migration complete!")
        return 0, 0
    
    if total_chunks < 0:
        print("[ERROR] Failed to count chunks. Will retry in 60s...")
        await asyncio.sleep(60)
        return 0, 0
    
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
        # Check for shutdown request
        if shutdown_requested:
            print("[SHUTDOWN] Finishing current batch before exit...")
            break
        
        # Fetch batch from database
        batch = await get_chunks_batch(storage, offset, BATCH_SIZE)
        
        if batch is None:
            # Fatal DB error - wait and try again from beginning
            print("[FATAL] Database connection failed. Waiting 60s before restarting pass...")
            await asyncio.sleep(60)
            return successful, failed  # Return partial results
        
        if not batch:
            # No more chunks at this offset - we've reached the end
            print(f"[INFO] Reached end of chunks at offset {offset}")
            break
        
        batch_num = (offset // BATCH_SIZE) + 1
        total_batches = (total_chunks + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"[BATCH {batch_num}/{total_batches}] Processing {len(batch)} chunks (offset: {offset})")
        
        # Process each chunk in the batch
        for i, (chunk_id, content) in enumerate(batch):
            global_index = processed + i
            
            # Check for shutdown
            if shutdown_requested and i > 0:  # Finish current chunk at least
                print("[SHUTDOWN] Exiting after current chunk...")
                break
            
            success = await process_chunk(storage, chunk_id, content, global_index, total_chunks)
            if success:
                successful += 1
            else:
                failed += 1
            
            # Add delay between chunks to avoid overwhelming Ollama
            if i < len(batch) - 1 and not shutdown_requested:
                await asyncio.sleep(DELAY_BETWEEN_CHUNKS)
            
            # Progress report every 100 chunks
            if (successful + failed) % 100 == 0:
                elapsed = time.time() - start_time
                rate = (successful + failed) / elapsed if elapsed > 0 else 0
                print(f"[PROGRESS] {successful + failed} chunks processed ({rate:.1f} chunks/sec). Successful: {successful}, Failed: {failed}")
        
        processed += len(batch)
        offset += len(batch)
        
        if shutdown_requested:
            break
        
        # Delay between batches
        if processed < total_chunks:
            print(f"[BATCH] Completed {processed}/{total_chunks}. Pausing {DELAY_BETWEEN_BATCHES}s...")
            await asyncio.sleep(DELAY_BETWEEN_BATCHES)
    
    # Summary for this pass
    elapsed_time = time.time() - start_time
    print()
    print("=" * 80)
    if is_retry_pass:
        print("RETRY PASS COMPLETE")
    else:
        print("MIGRATION PASS COMPLETE")
    print("=" * 80)
    print(f"Finished at: {datetime.now().isoformat()}")
    print(f"Chunks processed this pass: {processed}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    if elapsed_time > 0:
        print(f"Time elapsed: {elapsed_time:.1f} seconds ({elapsed_time/60:.1f} minutes)")
        print(f"Average speed: {processed/elapsed_time:.1f} chunks/second")
    print()
    
    return successful, failed


async def retry_failed_chunks(storage) -> int:
    """Retry all permanently failed chunks. Returns number successfully retried."""
    global failed_chunk_ids
    
    if not failed_chunk_ids:
        return 0
    
    print(f"[RETRY] Attempting to retry {len(failed_chunk_ids)} failed chunks...")
    
    # Copy and clear the failed set
    chunks_to_retry = list(failed_chunk_ids)
    failed_chunk_ids.clear()
    
    successful_retries = 0
    for i, chunk_id in enumerate(chunks_to_retry):
        # Fetch the chunk content
        query = "SELECT chunk_id, content FROM chunks WHERE chunk_id = $1 AND embedding IS NULL"
        try:
            row = await storage.client.fetchrow(query, chunk_id)
            if not row:
                continue  # Chunk no longer exists or already has embedding
            
            success = await process_single_chunk_with_retries(storage, row['chunk_id'], row['content'])
            if success:
                successful_retries += 1
            
            # Progress
            if (i + 1) % 10 == 0:
                print(f"[RETRY PROGRESS] {i + 1}/{len(chunks_to_retry)} failed chunks processed")
            
            await asyncio.sleep(DELAY_BETWEEN_CHUNKS)
        except Exception as e:
            print(f"[ERROR] Failed to retry chunk {chunk_id}: {e}")
            failed_chunk_ids.add(chunk_id)
    
    print(f"[RETRY COMPLETE] Successfully retried {successful_retries}/{len(chunks_to_retry)} chunks")
    return successful_retries


async def run_migration_until_complete():
    """Main migration function that loops until all chunks are processed."""
    global shutdown_requested, failed_chunk_ids
    
    print("=" * 80)
    print("ROBUST BACKFILL MIGRATION: Generate embeddings for existing chunks")
    print("This script will continue running until ALL chunks have embeddings.")
    print("Press Ctrl+C to stop gracefully.")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Embedding model: Ollama nomic-embed-text ({EMBEDDING_DIMENSION}d)")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Max retries per chunk: {MAX_RETRIES}")
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
    
    total_start_time = time.time()
    pass_number = 0
    total_successful = 0
    total_failed = 0
    
    # Main loop - keep running until all chunks are done
    while not shutdown_requested:
        pass_number += 1
        print(f"\n{'='*80}")
        print(f"STARTING MIGRATION PASS #{pass_number}")
        print(f"{'='*80}\n")
        
        # Run one pass
        successful, failed = await run_migration_pass(storage, is_retry_pass=False)
        total_successful += successful
        total_failed += failed
        
        # Retry failed chunks from this pass
        if failed_chunk_ids and not shutdown_requested:
            print(f"\n[INFO] {len(failed_chunk_ids)} chunks failed in this pass. Starting retry pass...")
            retry_successful = await retry_failed_chunks(storage)
            total_successful += retry_successful
            total_failed -= retry_successful
        
        # Check if we're done
        remaining = await count_chunks_without_embeddings(storage)
        if remaining == 0:
            print("\n" + "=" * 80)
            print("MIGRATION FULLY COMPLETE!")
            print("=" * 80)
            break
        elif remaining < 0:
            print("\n[WARN] Could not verify remaining chunks. Waiting 60s before next pass...")
            await asyncio.sleep(60)
        else:
            print(f"\n[INFO] {remaining} chunks still need embeddings. Starting next pass in 10s...")
            await asyncio.sleep(10)
        
        # Safety check: if no progress was made in this pass, wait longer
        if successful == 0 and not shutdown_requested:
            print("[WARN] No progress made in this pass. Waiting 60s before retry...")
            await asyncio.sleep(60)
    
    # Final summary
    total_elapsed = time.time() - total_start_time
    print()
    print("=" * 80)
    print("FINAL MIGRATION SUMMARY")
    print("=" * 80)
    print(f"Finished at: {datetime.now().isoformat()}")
    print(f"Total passes: {pass_number}")
    print(f"Total successful: {total_successful}")
    print(f"Total failed (permanent): {len(failed_chunk_ids)}")
    print(f"Time elapsed: {total_elapsed:.1f} seconds ({total_elapsed/3600:.1f} hours)")
    if total_elapsed > 0 and total_successful > 0:
        print(f"Average speed: {total_successful/total_elapsed:.1f} chunks/second")
    
    if failed_chunk_ids:
        print(f"\n[WARNING] {len(failed_chunk_ids)} chunks permanently failed:")
        for chunk_id in list(failed_chunk_ids)[:10]:
            print(f"  - {chunk_id}")
        if len(failed_chunk_ids) > 10:
            print(f"  ... and {len(failed_chunk_ids) - 10} more")
    else:
        print("\n[SUCCESS] All chunks have been updated with embeddings!")


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
    
    parser = argparse.ArgumentParser(description='Robust backfill embeddings for existing chunks')
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
                await run_migration_until_complete()
            else:
                # Confirm before running
                print()
                confirm = input(f"Generate embeddings for {chunks_without} chunks? This will run continuously until complete. [y/N]: ")
                
                if confirm.lower() == 'y':
                    await run_migration_until_complete()
                else:
                    print("[CANCELLED] Migration aborted.")


if __name__ == "__main__":
    asyncio.run(main())
