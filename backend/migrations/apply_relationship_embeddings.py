#!/usr/bin/env python3
"""
Migration: Add relationship embedding support
Applies SQL migration and optionally generates embeddings for existing relationships
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def apply_migration():
    """Apply the SQL migration."""
    sys.path.insert(0, '/Users/ken/clawd_workspace/projects/KG_RAG/proj_ph2/source/postgres')
    from client import PostgresClient, init_postgres_client
    
    print("Applying relationship embedding migration...")
    
    # Read migration SQL
    migration_path = os.path.join(os.path.dirname(__file__), 'add_relationship_embeddings.sql')
    with open(migration_path, 'r') as f:
        migration_sql = f.read()
    
    # Apply migration
    client = await init_postgres_client()
    
    try:
        # Split and execute each statement
        statements = [s.strip() for s in migration_sql.split(';') if s.strip()]
        
        for statement in statements:
            if statement and not statement.startswith('--'):
                print(f"Executing: {statement[:80]}...")
                await client.execute(statement)
        
        print("✅ Migration applied successfully!")
        
        # Check current relationship count
        result = await client.fetch("SELECT COUNT(*) as cnt FROM relationships")
        count = result[0]["cnt"] if result else 0
        print(f"📊 Total relationships in database: {count}")
        
        # Check how many have embeddings
        result = await client.fetch("SELECT COUNT(*) as cnt FROM relationships WHERE embedding IS NOT NULL")
        with_embeddings = result[0]["cnt"] if result else 0
        print(f"📊 Relationships with embeddings: {with_embeddings}")
        
        if with_embeddings == 0 and count > 0:
            print("\n⚠️  Note: Existing relationships don't have embeddings.")
            print("   To generate embeddings for existing relationships, run:")
            print("   python3 generate_relationship_embeddings.py")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(apply_migration())
