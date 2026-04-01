#!/usr/bin/env python3
"""
Migration: Generate embeddings for existing relationships

This script generates vector embeddings for relationship descriptions.
WARNING: This will make API calls to your embedding service (Ollama).
For 116K relationships, this will take significant time.
"""

import asyncio
import sys
import os
import json

# Add paths
sys.path.insert(0, '/Users/ken/clawd_workspace/projects/KG_RAG/proj_ph2/source/postgres')
sys.path.insert(0, '/Users/ken/clawd_workspace/projects/KG_RAG/KG_RAG_v2.0-beta/backend')

from client import PostgresClient, init_postgres_client


async def generate_embeddings_batch(
    client: PostgresClient,
    batch_size: int = 100,
    max_relationships: int = None
):
    """
    Generate embeddings for relationships in batches.
    
    Args:
        client: PostgreSQL client
        batch_size: Number of relationships to process per batch
        max_relationships: Maximum total to process (None = all)
    """
    
    # Get relationships without embeddings
    query = """
    SELECT relationship_id, source_id, target_id, relationship_type, properties
    FROM relationships
    WHERE embedding IS NULL
    AND (description IS NOT NULL OR relationship_type IS NOT NULL)
    LIMIT $1
    """
    
    # Import Ollama embedding function
    from pgvector_api import get_ollama_embedding
    
    total_processed = 0
    total_success = 0
    total_failed = 0
    
    while True:
        # Get batch of relationships
        rows = await client.fetch(query, batch_size)
        
        if not rows:
            print("✅ No more relationships to process")
            break
            
        if max_relationships and total_processed >= max_relationships:
            print(f"✅ Reached limit of {max_relationships} relationships")
            break
        
        print(f"\n📦 Processing batch of {len(rows)} relationships...")
        
        for row in rows:
            rel_id = row['relationship_id']
            source_id = row['source_id']
            target_id = row['target_id']
            rel_type = row['relationship_type']
            properties = row['properties'] or {}
            
            try:
                # Create description from available data
                description = f"{source_id} {rel_type} {target_id}"
                
                # Add properties if available
                if isinstance(properties, str):
                    properties = json.loads(properties)
                
                if properties.get('description'):
                    description = properties['description']
                elif properties.get('keywords'):
                    description = f"{description}: {properties['keywords']}"
                
                # Generate embedding
                embedding = get_ollama_embedding(description)
                
                if embedding:
                    # Update relationship with embedding
                    update_query = """
                    UPDATE relationships
                    SET embedding = $1::vector,
                        description = $2,
                        keywords = $3
                    WHERE relationship_id = $4
                    """
                    
                    keywords = properties.get('keywords', rel_type)
                    
                    await client.execute(
                        update_query,
                        json.dumps(embedding),
                        description,
                        keywords,
                        rel_id
                    )
                    
                    total_success += 1
                else:
                    total_failed += 1
                    
            except Exception as e:
                print(f"❌ Failed to process {rel_id}: {e}")
                total_failed += 1
            
            total_processed += 1
            
            # Progress update every 10
            if total_processed % 10 == 0:
                print(f"  Progress: {total_processed} processed, {total_success} success, {total_failed} failed")
        
        print(f"📊 Batch complete. Total: {total_processed}, Success: {total_success}, Failed: {total_failed}")
    
    return total_processed, total_success, total_failed


async def main():
    """Main migration function."""
    print("=" * 60)
    print("Relationship Embedding Generation")
    print("=" * 60)
    print("\n⚠️  WARNING: This will generate embeddings for ALL relationships")
    print("   using Ollama (nomic-embed-text model).")
    print("   For 116K relationships, this will take several hours.")
    print("\n   Options:")
    print("   1. Full migration (all relationships)")
    print("   2. Test run (100 relationships)")
    print("   3. Custom limit")
    print("   4. Cancel")
    print()
    
    choice = input("Select option (1-4): ").strip()
    
    if choice == "4":
        print("❌ Cancelled")
        return
    
    max_rels = None
    if choice == "2":
        max_rels = 100
        print("\n🧪 Test mode: Processing 100 relationships")
    elif choice == "3":
        max_rels = int(input("Enter number of relationships to process: ").strip())
        print(f"\n📊 Processing {max_rels} relationships")
    else:
        confirm = input("\n⚠️  Process ALL relationships? This will take hours. (yes/no): ").strip()
        if confirm.lower() != "yes":
            print("❌ Cancelled")
            return
        print("\n🚀 Full migration mode")
    
    # Initialize client
    print("\n🔌 Connecting to database...")
    client = await init_postgres_client()
    
    try:
        # Check current stats
        result = await client.fetch(
            "SELECT COUNT(*) as cnt FROM relationships WHERE embedding IS NULL"
        )
        pending = result[0]["cnt"] if result else 0
        
        result = await client.fetch(
            "SELECT COUNT(*) as cnt FROM relationships WHERE embedding IS NOT NULL"
        )
        completed = result[0]["cnt"] if result else 0
        
        print(f"\n📊 Current Status:")
        print(f"   - Pending: {pending}")
        print(f"   - Completed: {completed}")
        print(f"   - Total: {pending + completed}")
        
        if pending == 0:
            print("\n✅ All relationships already have embeddings!")
            return
        
        # Process
        print(f"\n🚀 Starting embedding generation...")
        total, success, failed = await generate_embeddings_batch(
            client,
            batch_size=50,
            max_relationships=max_rels
        )
        
        print("\n" + "=" * 60)
        print("Migration Complete!")
        print("=" * 60)
        print(f"📊 Total processed: {total}")
        print(f"✅ Successful: {success}")
        print(f"❌ Failed: {failed}")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
