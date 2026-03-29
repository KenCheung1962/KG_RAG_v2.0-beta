#!/usr/bin/env python3
"""
Parallel Backfill Migration: Generate embeddings for existing chunks using multiple workers
This script uses multiple processes to speed up embedding generation.
"""

import asyncio
import os
import sys
import time
import json
import multiprocessing as mp
from datetime import datetime
from typing import List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

# Add necessary paths
sys.path.insert(0, '/Users/ken/clawd_workspace/projects/KG_RAG/proj_ph2/source/postgres')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Embedding dimension
EMBEDDING_DIMENSION = 768

# Database config (shared)
DB_CONFIG = {
    "host": os.getenv('PGVECTOR_HOST', 'localhost'),
    "port": int(os.getenv('PGVECTOR_PORT', '5432')),
    "database": os.getenv('PGVECTOR_DATABASE', 'kg_rag'),
    "user": os.getenv('PGVECTOR_USER', 'postgres'),
    "password": os.getenv('PGVECTOR_PASSWORD', 'postgres'),
    "min_connections": 2,
    "max_connections": 20,
}

# Ollama config (shared)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")


def get_embedding_sync(text: str) -> List[float]:
    """Generate embedding using Ollama (synchronous version for multiprocessing)."""
    import httpx
    
    try:
        response = httpx.post(
            f"{OLLAMA_HOST}/api/embeddings",
            json={"model": OLLAMA_MODEL, "prompt": text[:8000]},
            timeout=30.0
        )
        
        if response.status_code == 200:
            result = response.json()
            embedding = result.get("embedding", [])
            if embedding and len(embedding) == EMBEDDING_DIMENSION:
                return embedding
        return [0.0] * EMBEDDING_DIMENSION
    except Exception as e:
        print(f"[ERROR] Embedding failed: {e}")
        return [0.0] * EMBEDDING_DIMENSION


def process_chunk_batch(batch: List[Tuple[str, str]], worker_id: int) -> Tuple[int, int, int]:
    """
    Process a batch of chunks in a worker process.
    Returns: (processed_count, success_count, failed_count)
    """
    import asyncpg
    import asyncio
    
    async def update_chunks():
        # Connect to database
        conn = await asyncpg.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        
        success = 0
        failed = 0
        
        try:
            for chunk_id, content in batch:
                try:
                    # Generate embedding (sync call)
                    embedding = get_embedding_sync(content)
                    
                    if len(embedding) == EMBEDDING_DIMENSION:
                        # Update database
                        vector_str = '[' + ','.join(str(x) for x in embedding) + ']'
                        await conn.execute(
                            "UPDATE chunks SET embedding = $1::vector WHERE chunk_id = $2",
                            vector_str, chunk_id
                        )
                        success += 1
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1
                    print(f"[Worker {worker_id}] Error processing {chunk_id}: {e}")
        finally:
            await conn.close()
        
        return len(batch), success, failed
    
    # Run async function
    return asyncio.run(update_chunks())


async def get_total_chunks() -> int:
    """Get total count of chunks without embeddings."""
    import asyncpg
    
    conn = await asyncpg.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        database=DB_CONFIG['database'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password']
    )
    
    try:
        result = await conn.fetchval("SELECT COUNT(*) FROM chunks WHERE embedding IS NULL")
        return result or 0
    finally:
        await conn.close()


async def get_chunk_batch(offset: int, limit: int) -> List[Tuple[str, str]]:
    """Get a batch of chunks to process."""
    import asyncpg
    
    conn = await asyncpg.connect(
        host=DB_CONFIG['host'],
        port=DB_CONFIG['port'],
        database=DB_CONFIG['database'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password']
    )
    
    try:
        rows = await conn.fetch(
            "SELECT chunk_id, content FROM chunks WHERE embedding IS NULL ORDER BY chunk_id LIMIT $1 OFFSET $2",
            limit, offset
        )
        return [(row['chunk_id'], row['content']) for row in rows]
    finally:
        await conn.close()


async def run_parallel_migration(num_workers: int = 4, batch_size: int = 50):
    """Run migration with multiple workers."""
    print("=" * 80)
    print("PARALLEL BACKFILL MIGRATION")
    print("=" * 80)
    print(f"Started at: {datetime.now().isoformat()}")
    print(f"Workers: {num_workers}")
    print(f"Batch size per worker: {batch_size}")
    print(f"Ollama: {OLLAMA_HOST}")
    print(f"Model: {OLLAMA_MODEL}")
    print()
    
    # Get total count
    print("[INFO] Counting chunks without embeddings...")
    total_chunks = await get_total_chunks()
    
    if total_chunks == 0:
        print("[INFO] No chunks need migration!")
        return
    
    print(f"[INFO] Total chunks to process: {total_chunks}")
    print()
    
    # Calculate batches
    chunks_per_worker_batch = batch_size
    total_batches = (total_chunks + chunks_per_worker_batch - 1) // chunks_per_worker_batch
    
    print(f"[INFO] Total batches: {total_batches}")
    print(f"[INFO] Starting migration with {num_workers} parallel workers...")
    print()
    
    start_time = time.time()
    processed_total = 0
    success_total = 0
    failed_total = 0
    batch_num = 0
    
    # Process batches with parallel workers
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        while processed_total < total_chunks:
            # Fetch next set of batches for all workers
            futures = []
            
            for worker_id in range(num_workers):
                offset = batch_num * num_workers * chunks_per_worker_batch + worker_id * chunks_per_worker_batch
                
                if offset >= total_chunks:
                    break
                
                # Get batch for this worker
                batch = await get_chunk_batch(offset, chunks_per_worker_batch)
                
                if not batch:
                    continue
                
                # Submit to worker
                future = executor.submit(process_chunk_batch, batch, worker_id)
                futures.append((future, worker_id, len(batch)))
            
            if not futures:
                break
            
            # Wait for all workers to complete their batches
            batch_start_time = time.time()
            batch_processed = 0
            batch_success = 0
            batch_failed = 0
            
            for future, worker_id, chunk_count in futures:
                try:
                    processed, success, failed = future.result(timeout=300)  # 5 min timeout
                    batch_processed += processed
                    batch_success += success
                    batch_failed += failed
                except Exception as e:
                    print(f"[ERROR] Worker {worker_id} failed: {e}")
                    batch_failed += chunk_count
            
            processed_total += batch_processed
            success_total += batch_success
            failed_total += batch_failed
            batch_num += 1
            
            # Calculate progress and ETA
            elapsed = time.time() - start_time
            progress = processed_total / total_chunks * 100
            rate = processed_total / elapsed if elapsed > 0 else 0
            remaining_chunks = total_chunks - processed_total
            eta_seconds = remaining_chunks / rate if rate > 0 else 0
            eta_hours = eta_seconds / 3600
            
            batch_time = time.time() - batch_start_time
            
            print(f"[BATCH {batch_num}] Processed: {batch_processed}, Success: {batch_success}, Failed: {batch_failed}")
            print(f"[PROGRESS] {processed_total}/{total_chunks} ({progress:.1f}%) | "
                  f"Rate: {rate:.1f} chunks/sec | ETA: {eta_hours:.1f} hours | "
                  f"Batch time: {batch_time:.1f}s")
            print()
    
    # Final summary
    elapsed = time.time() - start_time
    print("=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print(f"Finished at: {datetime.now().isoformat()}")
    print(f"Total processed: {processed_total}")
    print(f"Successful: {success_total}")
    print(f"Failed: {failed_total}")
    print(f"Total time: {elapsed/3600:.1f} hours")
    print(f"Average rate: {processed_total/elapsed:.1f} chunks/second")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Parallel backfill migration for embeddings')
    parser.add_argument('--workers', '-w', type=int, default=4, 
                        help='Number of parallel workers (default: 4)')
    parser.add_argument('--batch-size', '-b', type=int, default=50,
                        help='Batch size per worker (default: 50)')
    
    args = parser.parse_args()
    
    # Set multiprocessing start method
    mp.set_start_method('spawn', force=True)
    
    # Run migration
    asyncio.run(run_parallel_migration(args.workers, args.batch_size))
