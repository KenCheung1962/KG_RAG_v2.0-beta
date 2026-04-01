#!/usr/bin/env python3
"""
Relationship Embedding Management Script

A command-line tool for managing relationship embeddings in KG RAG.

Usage:
    python manage_embeddings.py status              # Check embedding status
    python manage_embeddings.py generate --limit 100 # Generate batch of embeddings
    python manage_embeddings.py background --start  # Start background processor
    python manage_embeddings.py background --stop   # Stop background processor
    python manage_embeddings.py full-migration      # Run full batch backfill

The script supports the 3-phase embedding strategy:
- Phase 1: Upload-time generation (automatic during file upload)
- Phase 2: Lazy generation (on-demand when queried)
- Phase 3: Batch backfill (this script)
"""

import argparse
import asyncio
import json
import sys
import os
from typing import Optional

# Add backend directory to path for local imports
sys.path.insert(0, '/Users/ken/clawd_workspace/projects/KG_RAG/KG_RAG_v2.0-beta/backend')

from client import PostgresClient, init_postgres_client
from storage import KGStorage


API_BASE_URL = "http://127.0.0.1:8002"


async def get_status():
    """Get current embedding status."""
    import httpx
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE_URL}/api/v1/admin/relationship-embeddings/status")
        return resp.json()


async def generate_batch(limit: int = 100, relationship_ids: Optional[list] = None):
    """Generate a batch of embeddings."""
    import httpx
    
    payload = {"limit": limit}
    if relationship_ids:
        payload["relationship_ids"] = relationship_ids
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE_URL}/api/v1/admin/relationship-embeddings/generate",
            json=payload
        )
        return resp.json()


async def start_background(interval_seconds: int = 60):
    """Start background processor."""
    import httpx
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE_URL}/api/v1/admin/relationship-embeddings/background/start",
            json={"interval_seconds": interval_seconds}
        )
        return resp.json()


async def stop_background():
    """Stop background processor."""
    import httpx
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE_URL}/api/v1/admin/relationship-embeddings/background/stop"
        )
        return resp.json()


async def full_migration(batch_size: int = 100, max_total: Optional[int] = None):
    """
    Run full migration - generate embeddings for all relationships.
    
    This processes relationships in batches until all have embeddings
    or max_total is reached.
    """
    print("=" * 60)
    print("FULL RELATIONSHIP EMBEDDING MIGRATION")
    print("=" * 60)
    print()
    
    # Get initial status
    print("📊 Getting initial status...")
    status = await get_status()
    
    if not status.get("success"):
        print(f"❌ Failed to get status: {status.get('error')}")
        return
    
    db_stats = status.get("database", {})
    total = db_stats.get("total_relationships", 0)
    with_emb = db_stats.get("with_embeddings", 0)
    without_emb = db_stats.get("without_embeddings", 0)
    
    print(f"\nInitial State:")
    print(f"  Total relationships: {total:,}")
    print(f"  With embeddings: {with_emb:,} ({db_stats.get('percentage_complete', 0)}%)")
    print(f"  Without embeddings: {without_emb:,}")
    
    if without_emb == 0:
        print("\n✅ All relationships already have embeddings!")
        return
    
    # Confirm
    target = min(max_total or without_emb, without_emb)
    print(f"\n🚀 About to generate embeddings for {target:,} relationships")
    print(f"   Batch size: {batch_size}")
    print(f"   Estimated batches: {(target // batch_size) + 1}")
    confirm = input("\nProceed? (yes/no): ").strip().lower()
    
    if confirm != "yes":
        print("❌ Cancelled")
        return
    
    # Process batches
    total_processed = 0
    total_generated = 0
    total_failed = 0
    batch_num = 0
    
    while total_processed < target:
        batch_num += 1
        remaining = target - total_processed
        current_batch_size = min(batch_size, remaining)
        
        print(f"\n📦 Batch {batch_num}: Processing {current_batch_size} relationships...")
        
        result = await generate_batch(limit=current_batch_size)
        
        if result.get("success"):
            stats = result.get("stats", {})
            processed = stats.get("processed", 0)
            generated = stats.get("generated", 0)
            failed = stats.get("failed", 0)
            skipped = stats.get("skipped", 0)
            
            total_processed += processed
            total_generated += generated
            total_failed += failed
            
            print(f"   ✓ Processed: {processed}")
            print(f"   ✓ Generated: {generated}")
            print(f"   ⚠ Failed: {failed}")
            print(f"   ⏭ Skipped: {skipped}")
            print(f"   📊 Progress: {total_processed}/{target} ({100*total_processed//target}%)")
            
            # Check if we're making progress
            if processed == 0:
                print("\n✅ No more relationships to process")
                break
        else:
            print(f"   ❌ Batch failed: {result.get('error')}")
            break
        
        # Small delay between batches
        await asyncio.sleep(0.5)
    
    # Final status
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)
    print(f"\nFinal Stats:")
    print(f"  Total processed: {total_processed:,}")
    print(f"  Embeddings generated: {total_generated:,}")
    print(f"  Failed: {total_failed:,}")
    
    # Get updated status
    final_status = await get_status()
    if final_status.get("success"):
        final_db = final_status.get("database", {})
        print(f"\nUpdated State:")
        print(f"  Total relationships: {final_db.get('total_relationships', 0):,}")
        print(f"  With embeddings: {final_db.get('with_embeddings', 0):,} ({final_db.get('percentage_complete', 0)}%)")
        print(f"  Without embeddings: {final_db.get('without_embeddings', 0):,}")


def print_status(status: dict):
    """Pretty print status information."""
    if not status.get("success"):
        print(f"❌ Error: {status.get('error', 'Unknown error')}")
        return
    
    db = status.get("database", {})
    svc = status.get("service", {})
    
    print("\n" + "=" * 60)
    print("RELATIONSHIP EMBEDDING STATUS")
    print("=" * 60)
    
    print("\n📊 Database Statistics:")
    print(f"  Total relationships: {db.get('total_relationships', 0):,}")
    print(f"  With embeddings: {db.get('with_embeddings', 0):,}")
    print(f"  Without embeddings: {db.get('without_embeddings', 0):,}")
    print(f"  Completion: {db.get('percentage_complete', 0)}%")
    print(f"  Status: {db.get('status', 'unknown')}")
    
    if svc:
        print("\n⚙️  Service Statistics:")
        print(f"  Generated (session): {svc.get('generated', 0):,}")
        print(f"  Failed (session): {svc.get('failed', 0):,}")
        print(f"  Skipped (session): {svc.get('skipped', 0):,}")
        print(f"  Cache size: {svc.get('cache_size', 0)}")
    
    bg_status = "running" if status.get("background_processor_running") else "stopped"
    print(f"\n🔄 Background Processor: {bg_status}")
    print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(
        description="Manage relationship embeddings for KG RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check current status
  python manage_embeddings.py status
  
  # Generate embeddings for 100 relationships
  python manage_embeddings.py generate --limit 100
  
  # Start background processor
  python manage_embeddings.py background --start --interval 60
  
  # Stop background processor
  python manage_embeddings.py background --stop
  
  # Run full migration (process all relationships)
  python manage_embeddings.py full-migration --batch-size 50
  
  # Run test migration (process 500 relationships)
  python manage_embeddings.py full-migration --batch-size 50 --max-total 500
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Status command
    subparsers.add_parser("status", help="Check embedding status")
    
    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate a batch of embeddings")
    gen_parser.add_argument("--limit", type=int, default=100, help="Number of relationships to process")
    
    # Background command
    bg_parser = subparsers.add_parser("background", help="Control background processor")
    bg_parser.add_argument("--start", action="store_true", help="Start background processor")
    bg_parser.add_argument("--stop", action="store_true", help="Stop background processor")
    bg_parser.add_argument("--interval", type=int, default=60, help="Seconds between batches")
    
    # Full migration command
    mig_parser = subparsers.add_parser("full-migration", help="Run full batch backfill")
    mig_parser.add_argument("--batch-size", type=int, default=100, help="Batch size")
    mig_parser.add_argument("--max-total", type=int, help="Maximum total to process")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "status":
            status = await get_status()
            print_status(status)
            
        elif args.command == "generate":
            print(f"Generating embeddings for up to {args.limit} relationships...")
            result = await generate_batch(limit=args.limit)
            if result.get("success"):
                stats = result.get("stats", {})
                print(f"\n✅ Batch complete!")
                print(f"   Processed: {stats.get('processed', 0)}")
                print(f"   Generated: {stats.get('generated', 0)}")
                print(f"   Failed: {stats.get('failed', 0)}")
            else:
                print(f"❌ Failed: {result.get('error')}")
                
        elif args.command == "background":
            if args.start:
                print(f"Starting background processor (interval: {args.interval}s)...")
                result = await start_background(interval_seconds=args.interval)
                if result.get("success"):
                    print(f"✅ {result.get('message')}")
                else:
                    print(f"❌ Failed: {result.get('error')}")
            elif args.stop:
                print("Stopping background processor...")
                result = await stop_background()
                if result.get("success"):
                    print(f"✅ {result.get('message')}")
                else:
                    print(f"❌ Failed: {result.get('error')}")
            else:
                print("Use --start or --stop")
                
        elif args.command == "full-migration":
            await full_migration(
                batch_size=args.batch_size,
                max_total=args.max_total
            )
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
