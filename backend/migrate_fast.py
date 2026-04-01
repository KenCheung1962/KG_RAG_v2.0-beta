#!/usr/bin/env python3
"""Fast embedding migration with concurrent Ollama requests"""

import asyncio
import os
import sys
import time
from datetime import datetime

# Using local storage.py

import asyncpg
import httpx

# Config
DB_CONFIG = {
    "host": os.getenv('PGVECTOR_HOST', 'localhost'),
    "port": int(os.getenv('PGVECTOR_PORT', '5432')),
    "database": os.getenv('PGVECTOR_DATABASE', 'kg_rag'),
    "user": os.getenv('PGVECTOR_USER', 'postgres'),
    "password": os.getenv('PGVECTOR_PASSWORD', 'postgres'),
}

OLLAMA_URL = "http://127.0.0.1:11434/api/embeddings"
OLLAMA_MODEL = "nomic-embed-text:latest"
EMBEDDING_DIM = 768

# Concurrency
CONCURRENT_REQUESTS = 20  # Ollama can handle this many
BATCH_SIZE = 1000  # Process 1000 chunks at a time


async def get_embedding(client: httpx.AsyncClient, text: str, sem: asyncio.Semaphore) -> list:
    """Get embedding with semaphore-controlled concurrency."""
    async with sem:
        try:
            resp = await client.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": text[:8000]},
                timeout=30.0
            )
            if resp.status_code == 200:
                emb = resp.json().get("embedding", [])
                if len(emb) == EMBEDDING_DIM:
                    return emb
        except Exception as e:
            pass
        return [0.0] * EMBEDDING_DIM


async def update_chunk(conn: asyncpg.Connection, chunk_id: str, embedding: list):
    """Update chunk with embedding."""
    vector_str = '[' + ','.join(str(x) for x in embedding) + ']'
    await conn.execute(
        "UPDATE chunks SET embedding = $1::vector WHERE chunk_id = $2",
        vector_str, chunk_id
    )


async def process_batch(db_pool: asyncpg.Pool, http_client: httpx.AsyncClient, 
                        sem: asyncio.Semaphore, offset: int) -> tuple:
    """Process one batch of chunks."""
    async with db_pool.acquire() as conn:
        # Fetch batch
        rows = await conn.fetch(
            "SELECT chunk_id, content FROM chunks WHERE embedding IS NULL ORDER BY chunk_id LIMIT $1 OFFSET $2",
            BATCH_SIZE, offset
        )
        
        if not rows:
            return 0, 0, 0
        
        # Generate embeddings concurrently
        tasks = [get_embedding(http_client, row['content'], sem) for row in rows]
        embeddings = await asyncio.gather(*tasks)
        
        # Update database
        success = 0
        for row, emb in zip(rows, embeddings):
            if emb[0] != 0.0:  # Check if valid
                await update_chunk(conn, row['chunk_id'], emb)
                success += 1
        
        return len(rows), success, len(rows) - success


async def main():
    print("="*60)
    print("FAST EMBEDDING MIGRATION")
    print("="*60)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Ollama: {OLLAMA_URL}")
    print(f"Concurrency: {CONCURRENT_REQUESTS}")
    print(f"Batch size: {BATCH_SIZE}")
    print()
    
    # Connect to DB
    pool = await asyncpg.create_pool(**DB_CONFIG, min_size=5, max_size=20)
    
    # Get total count
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM chunks WHERE embedding IS NULL")
    
    print(f"Total chunks to process: {total}")
    print()
    
    if total == 0:
        print("Nothing to do!")
        return
    
    # Setup HTTP client and semaphore
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=CONCURRENT_REQUESTS)) as http_client:
        sem = asyncio.Semaphore(CONCURRENT_REQUESTS)
        
        start_time = time.time()
        processed = 0
        success_total = 0
        offset = 0
        
        while processed < total:
            batch_start = time.time()
            count, success, failed = await process_batch(pool, http_client, sem, offset)
            
            if count == 0:
                break
            
            processed += count
            success_total += success
            offset += count
            
            # Stats
            elapsed = time.time() - start_time
            rate = processed / elapsed
            progress = processed / total * 100
            eta = (total - processed) / rate if rate > 0 else 0
            batch_time = time.time() - batch_start
            
            print(f"[{processed}/{total} {progress:.1f}%] "
                  f"Batch: {count} in {batch_time:.1f}s | "
                  f"Rate: {rate:.1f}/sec | "
                  f"ETA: {eta/3600:.1f}h")
    
    await pool.close()
    
    # Summary
    elapsed = time.time() - start_time
    print()
    print("="*60)
    print("COMPLETE")
    print(f"Processed: {processed}, Success: {success_total}")
    print(f"Time: {elapsed/3600:.1f}h, Rate: {processed/elapsed:.1f}/sec")


if __name__ == "__main__":
    asyncio.run(main())
