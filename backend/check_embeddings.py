#!/usr/bin/env python3
"""Simple script to check embedding status using the API's storage connection"""

import asyncio
import sys
import os

# Add necessary paths
sys.path.insert(0, '/Users/ken/clawd_workspace/projects/KG_RAG/proj_ph2/source/postgres')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from storage import create_kg_storage

async def check():
    # Database config
    config = {
        "host": os.getenv('PGVECTOR_HOST', 'localhost'),
        "port": int(os.getenv('PGVECTOR_PORT', '5432')),
        "database": os.getenv('PGVECTOR_DATABASE', 'kg_rag'),
        "user": os.getenv('PGVECTOR_USER', 'postgres'),
        "password": os.getenv('PGVECTOR_PASSWORD', 'postgres'),
        "min_connections": 2,
        "max_connections": 20,
        "use_pgbouncer": os.getenv('PGVECTOR_USE_PGBOUNCER', 'false').lower() == 'true'
    }
    
    print(f"Connecting to database at {config['host']}:{config['port']}...")
    storage = await create_kg_storage(config)
    
    print("Checking embedding status...")
    
    # Count total chunks
    total_result = await storage.client.fetchrow("SELECT COUNT(*) as count FROM chunks")
    total = total_result['count'] if total_result else 0
    
    # Count with embeddings
    with_result = await storage.client.fetchrow("SELECT COUNT(*) as count FROM chunks WHERE embedding IS NOT NULL")
    with_emb = with_result['count'] if with_result else 0
    
    # Count without embeddings
    without_result = await storage.client.fetchrow("SELECT COUNT(*) as count FROM chunks WHERE embedding IS NULL")
    without_emb = without_result['count'] if without_result else 0
    
    print(f"\n{'='*60}")
    print("DATABASE EMBEDDING STATUS")
    print('='*60)
    print(f"Total chunks:       {total:>10}")
    print(f"With embeddings:    {with_emb:>10} ({with_emb/total*100:.1f}%)")
    print(f"Without embeddings: {without_emb:>10} ({without_emb/total*100:.1f}%)")
    print('='*60)
    
    if without_emb > 0:
        print(f"\n[NEEDS MIGRATION] {without_emb} chunks need embeddings generated")
        print(f"Estimated time: ~{without_emb * 0.5 / 60:.0f} minutes")
    else:
        print("\n[OK] All chunks have embeddings!")
    
    return without_emb

if __name__ == "__main__":
    asyncio.run(check())
