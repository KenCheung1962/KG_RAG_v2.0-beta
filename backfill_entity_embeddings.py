#!/usr/bin/env python3
"""
Entity Embedding Backfill Script for KG RAG v2.0-beta

This script generates embeddings for all existing entities that don't have them.
It should be run AFTER the relationship embedding process is complete.

Usage:
    # Check current status
    python3 backfill_entity_embeddings.py --status
    
    # Run backfill (dry-run first)
    python3 backfill_entity_embeddings.py --dry-run
    
    # Run backfill for real
    python3 backfill_entity_embeddings.py
    
    # Run with custom batch size
    python3 backfill_entity_embeddings.py --batch-size 200
    
    # Run continuously until all entities have embeddings
    python3 backfill_entity_embeddings.py --continuous
    
    # Wait for relationship embeddings to complete, then start
    python3 backfill_entity_embeddings.py --wait-for-relationships

Features:
- Batched processing for efficiency
- Progress tracking with ETA
- Resume capability (won't re-process entities with embeddings)
- Dry-run mode for testing
- Can run continuously as background process
"""

import asyncio
import argparse
import sys
import os
import time
import signal
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from pgvector_api import get_ollama_embedding

# Configuration
DEFAULT_BATCH_SIZE = 100
DEFAULT_INTERVAL = 60  # seconds between batches
PID_FILE = "/tmp/kg_rag_entity_embedding_backfill.pid"
LOG_FILE = "/tmp/kg_rag_entity_embedding_backfill.log"


class EntityEmbeddingBackfill:
    """Backfill entity embeddings in batches."""
    
    def __init__(self, config: dict, batch_size: int = DEFAULT_BATCH_SIZE):
        self.config = config
        self.batch_size = batch_size
        self.running = False
        self.processed_count = 0
        self.failed_count = 0
        self.conn = None
        
    async def connect(self):
        """Connect to database."""
        import asyncpg
        self.conn = await asyncpg.connect(
            host=self.config.get('host', 'localhost'),
            port=self.config.get('port', 5432),
            database=self.config.get('database', 'kg_rag'),
            user=self.config.get('user', 'postgres'),
            password=self.config.get('password', 'postgres')
        )
        
    async def disconnect(self):
        """Disconnect from database."""
        if self.conn:
            await self.conn.close()
            self.conn = None
            
    def log(self, message: str):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        with open(LOG_FILE, 'a') as f:
            f.write(log_line + '\n')
            
    async def get_stats(self) -> Dict:
        """Get current entity embedding statistics."""
        result = await self.conn.fetchrow('''
            SELECT 
                COUNT(*) as total,
                COUNT(embedding) as with_embeddings,
                COUNT(*) - COUNT(embedding) as without_embeddings
            FROM entities
        ''')
        
        return {
            'total': result['total'],
            'with_embeddings': result['with_embeddings'],
            'without_embeddings': result['without_embeddings'],
            'percentage': (result['with_embeddings'] / result['total'] * 100) if result['total'] > 0 else 0
        }
        
    async def get_relationship_stats(self) -> Dict:
        """Get relationship embedding statistics."""
        result = await self.conn.fetchrow('''
            SELECT 
                COUNT(*) as total,
                COUNT(embedding) as with_embeddings
            FROM relationships
        ''')
        
        return {
            'total': result['total'],
            'with_embeddings': result['with_embeddings'],
            'percentage': (result['with_embeddings'] / result['total'] * 100) if result['total'] > 0 else 0
        }
        
    async def get_entities_without_embeddings(self, limit: int = None) -> List[Dict]:
        """Get entities that need embeddings."""
        query = '''
            SELECT entity_id, name, entity_type, description
            FROM entities
            WHERE embedding IS NULL
            ORDER BY entity_id
        '''
        if limit:
            query += f' LIMIT {limit}'
            
        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]
        
    def generate_embedding_text(self, entity: Dict) -> str:
        """Generate text for embedding from entity data."""
        name = entity.get('name', '')
        ent_type = entity.get('entity_type', 'concept')
        description = entity.get('description', '')
        
        # Format: "Name (type) - description"
        text = f"{name} ({ent_type})"
        if description and len(description) > 5:
            text += f" - {description}"
            
        return text[:8000]  # Limit length
        
    async def process_entity(self, entity: Dict) -> bool:
        """Process a single entity - generate and store embedding."""
        try:
            # Generate embedding text
            embedding_text = self.generate_embedding_text(entity)
            
            # Generate embedding using Ollama
            embedding = get_ollama_embedding(embedding_text)
            
            if not embedding:
                self.log(f"⚠️  Empty embedding for {entity['entity_id']}")
                return False
                
            # Convert to PostgreSQL vector format
            vector_str = '[' + ','.join(str(v) for v in embedding) + ']'
            
            # Update entity in database
            await self.conn.execute('''
                UPDATE entities
                SET embedding = $1::vector
                WHERE entity_id = $2
            ''', vector_str, entity['entity_id'])
            
            return True
            
        except Exception as e:
            self.log(f"❌ Failed {entity['entity_id']}: {str(e)[:80]}")
            return False
            
    async def process_batch(self, entities: List[Dict]) -> Tuple[int, int]:
        """Process a batch of entities. Returns (success, failed)."""
        success = 0
        failed = 0
        
        for entity in entities:
            if await self.process_entity(entity):
                success += 1
            else:
                failed += 1
                
        return success, failed
        
    async def run_single_pass(self, dry_run: bool = False) -> Dict:
        """Run one pass of backfill. Returns stats."""
        await self.connect()
        
        try:
            # Get stats
            stats = await self.get_stats()
            self.log("=" * 60)
            self.log("Entity Embedding Backfill - Starting Pass")
            self.log("=" * 60)
            self.log(f"Total Entities:          {stats['total']:,}")
            self.log(f"With Embeddings:         {stats['with_embeddings']:,} ({stats['percentage']:.2f}%)")
            self.log(f"Without Embeddings:      {stats['without_embeddings']:,}")
            self.log("=" * 60)
            
            if stats['without_embeddings'] == 0:
                self.log("✅ All entities already have embeddings!")
                return {'success': True, 'processed': 0, 'remaining': 0}
                
            if dry_run:
                self.log("\n🔍 DRY RUN MODE - No changes will be made")
                self.log(f"Would process {stats['without_embeddings']:,} entities")
                return {'success': True, 'processed': 0, 'remaining': stats['without_embeddings']}
                
            # Get entities to process
            self.log(f"\n📦 Fetching batch of {self.batch_size} entities...")
            entities = await self.get_entities_without_embeddings(self.batch_size)
            
            if not entities:
                self.log("✅ No entities to process!")
                return {'success': True, 'processed': 0, 'remaining': 0}
                
            # Process batch
            self.log(f"🚀 Processing {len(entities)} entities...")
            start_time = time.time()
            
            success, failed = await self.process_batch(entities)
            
            elapsed = time.time() - start_time
            rate = len(entities) / elapsed * 60 if elapsed > 0 else 0
            
            self.log(f"✅ Batch complete: {success} success, {failed} failed")
            self.log(f"⏱️  Rate: {rate:.1f}/min, Time: {elapsed:.1f}s")
            
            # Get updated stats
            new_stats = await self.get_stats()
            remaining = new_stats['without_embeddings']
            
            if remaining > 0:
                eta_minutes = remaining / rate if rate > 0 else 0
                self.log(f"📊 Remaining: {remaining:,} entities")
                self.log(f"⏱️  ETA: {eta_minutes:.1f} minutes ({eta_minutes/60:.1f} hours)")
                
            return {
                'success': True,
                'processed': success,
                'failed': failed,
                'remaining': remaining
            }
            
        finally:
            await self.disconnect()
            
    async def run_continuous(self, interval: int = DEFAULT_INTERVAL):
        """Run continuously until all entities have embeddings."""
        self.log("=" * 60)
        self.log("Entity Embedding Backfill - Continuous Mode")
        self.log("=" * 60)
        self.log(f"Batch Size: {self.batch_size}")
        self.log(f"Interval: {interval}s")
        self.log("Press Ctrl+C to stop")
        self.log("=" * 60)
        
        self.running = True
        batch_num = 0
        total_processed = 0
        
        while self.running:
            batch_num += 1
            self.log(f"\n📦 Batch #{batch_num}")
            
            result = await self.run_single_pass()
            
            if not result['success']:
                self.log("❌ Batch failed, retrying...")
                await asyncio.sleep(5)
                continue
                
            total_processed += result['processed']
            
            if result['remaining'] == 0:
                self.log("\n" + "=" * 60)
                self.log("🎉 ALL ENTITIES HAVE EMBEDDINGS!")
                self.log(f"Total processed: {total_processed:,}")
                self.log("=" * 60)
                break
                
            # Wait before next batch
            self.log(f"⏳ Waiting {interval}s before next batch...")
            await asyncio.sleep(interval)
            
    def stop(self):
        """Stop the continuous process."""
        self.running = False
        self.log("🛑 Stopping backfill process...")
        
    async def wait_for_relationships(self, threshold: float = 99.0, check_interval: int = 60):
        """Wait for relationship embeddings to reach threshold."""
        self.log("=" * 60)
        self.log("Waiting for Relationship Embeddings to Complete")
        self.log("=" * 60)
        self.log(f"Target: {threshold}% complete")
        self.log(f"Check interval: {check_interval}s")
        self.log("=" * 60)
        
        await self.connect()
        
        try:
            while True:
                rel_stats = await self.get_relationship_stats()
                
                self.log(f"\n📊 Relationship Progress: {rel_stats['percentage']:.2f}%")
                self.log(f"   With Embeddings: {rel_stats['with_embeddings']:,} / {rel_stats['total']:,}")
                
                if rel_stats['percentage'] >= threshold:
                    self.log(f"\n✅ Relationship embeddings reached {rel_stats['percentage']:.2f}%!")
                    self.log("🚀 Starting entity embedding backfill...")
                    return True
                    
                self.log(f"⏳ Waiting... (checking again in {check_interval}s)")
                await asyncio.sleep(check_interval)
                
        finally:
            await self.disconnect()


def check_pid_file() -> Optional[int]:
    """Check if another instance is running."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Check if process exists
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError, ProcessLookupError):
            # Stale PID file
            os.remove(PID_FILE)
    return None


def save_pid_file():
    """Save current PID to file."""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def remove_pid_file():
    """Remove PID file."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def show_status():
    """Show current entity embedding status."""
    import asyncpg
    
    async def _show():
        try:
            conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                database='kg_rag',
                user='postgres',
                password='postgres'
            )
            
            # Entity stats
            ent_result = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(embedding) as with_embeddings
                FROM entities
            ''')
            
            # Relationship stats
            rel_result = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(embedding) as with_embeddings
                FROM relationships
            ''')
            
            print("=" * 60)
            print("KG RAG Embedding Status")
            print("=" * 60)
            print("\n📊 Entities:")
            print(f"   Total:        {ent_result['total']:,}")
            print(f"   With Embeds:  {ent_result['with_embeddings']:,} ({ent_result['with_embeddings']/ent_result['total']*100:.2f}%)")
            print(f"   Remaining:    {ent_result['total'] - ent_result['with_embeddings']:,}")
            
            print("\n📊 Relationships:")
            print(f"   Total:        {rel_result['total']:,}")
            print(f"   With Embeds:  {rel_result['with_embeddings']:,} ({rel_result['with_embeddings']/rel_result['total']*100:.2f}%)")
            print(f"   Remaining:    {rel_result['total'] - rel_result['with_embeddings']:,}")
            
            # Check if backfill process is running
            pid = check_pid_file()
            if pid:
                print(f"\n🔄 Entity Backfill Process: Running (PID: {pid})")
            else:
                print("\n🔄 Entity Backfill Process: Not running")
                
            print("=" * 60)
            
            await conn.close()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            
    asyncio.run(_show())


def main():
    parser = argparse.ArgumentParser(
        description='Backfill entity embeddings for KG RAG v2.0-beta',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show current status
  python3 backfill_entity_embeddings.py --status
  
  # Run single batch (100 entities)
  python3 backfill_entity_embeddings.py
  
  # Dry run (don't actually update)
  python3 backfill_entity_embeddings.py --dry-run
  
  # Run continuously until complete
  python3 backfill_entity_embeddings.py --continuous
  
  # Wait for relationships to finish, then start
  python3 backfill_entity_embeddings.py --wait-for-relationships --continuous
  
  # Custom batch size
  python3 backfill_entity_embeddings.py --batch-size 200
  
  # Run as daemon (background)
  nohup python3 backfill_entity_embeddings.py --continuous > backfill.log 2>&1 &
        """
    )
    
    parser.add_argument('--status', action='store_true',
                        help='Show current embedding status')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate without making changes')
    parser.add_argument('--continuous', action='store_true',
                        help='Run continuously until complete')
    parser.add_argument('--wait-for-relationships', action='store_true',
                        help='Wait for relationship embeddings to complete first')
    parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE,
                        help=f'Number of entities per batch (default: {DEFAULT_BATCH_SIZE})')
    parser.add_argument('--interval', type=int, default=DEFAULT_INTERVAL,
                        help=f'Seconds between batches (default: {DEFAULT_INTERVAL})')
    parser.add_argument('--host', default='localhost',
                        help='PostgreSQL host (default: localhost)')
    parser.add_argument('--port', type=int, default=5432,
                        help='PostgreSQL port (default: 5432)')
    parser.add_argument('--database', default='kg_rag',
                        help='Database name (default: kg_rag)')
    parser.add_argument('--user', default='postgres',
                        help='PostgreSQL user (default: postgres)')
    parser.add_argument('--password', default='postgres',
                        help='PostgreSQL password (default: postgres)')
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
        return
        
    # Check if already running
    existing_pid = check_pid_file()
    if existing_pid and args.continuous:
        print(f"❌ Backfill process already running (PID: {existing_pid})")
        print("   Use 'kill {existing_pid}' to stop it first")
        return
        
    config = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': args.password
    }
    
    backfill = EntityEmbeddingBackfill(config, batch_size=args.batch_size)
    
    # Handle signals for graceful shutdown
    def signal_handler(signum, frame):
        backfill.stop()
        remove_pid_file()
        sys.exit(0)
        
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        save_pid_file()
        
        if args.wait_for_relationships:
            asyncio.run(backfill.wait_for_relationships())
            
        if args.continuous:
            asyncio.run(backfill.run_continuous(interval=args.interval))
        else:
            result = asyncio.run(backfill.run_single_pass(dry_run=args.dry_run))
            
            if result['remaining'] > 0 and not args.dry_run:
                print(f"\n💡 {result['remaining']:,} entities remaining")
                print("   Run with --continuous to process all")
                
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
    finally:
        remove_pid_file()


if __name__ == "__main__":
    main()
