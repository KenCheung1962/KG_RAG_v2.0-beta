#!/usr/bin/env python3
"""
Continuous Background Embedding Processor for KG RAG

This script runs continuously in the background, generating relationship embeddings
in batches. It can be started and stopped gracefully.

Usage:
    python3 background_embedding_processor.py start    # Start the processor
    python3 background_embedding_processor.py stop     # Stop the processor
    python3 background_embedding_processor.py status   # Check status
"""

import asyncio
import asyncpg
import sys
import os
import signal
import time
import json
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, 'backend')

# Configuration
BATCH_SIZE = 100
INTERVAL_SECONDS = 60  # Wait 60 seconds between batches
PID_FILE = "/tmp/kg_rag_embedding_processor.pid"
LOG_FILE = "/tmp/kg_rag_embedding_processor.log"


def log_message(message):
    """Log message to file and console."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')


def is_running():
    """Check if the processor is already running."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Check if process exists
            os.kill(pid, 0)
            return True, pid
        except (ValueError, OSError, ProcessLookupError):
            # Process not running, clean up stale pid file
            os.remove(PID_FILE)
    return False, None


def save_pid():
    """Save current process PID to file."""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def remove_pid():
    """Remove PID file."""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def stop_processor():
    """Stop the running processor."""
    running, pid = is_running()
    if running:
        try:
            os.kill(pid, signal.SIGTERM)
            log_message(f"Sent stop signal to processor (PID: {pid})")
            # Wait for process to stop
            for _ in range(10):
                time.sleep(0.5)
                if not is_running()[0]:
                    log_message("Processor stopped successfully")
                    return True
            log_message("Processor did not stop in time, forcing...")
            os.kill(pid, signal.SIGKILL)
            return True
        except Exception as e:
            log_message(f"Error stopping processor: {e}")
            return False
    else:
        log_message("Processor is not running")
        return True


async def generate_embeddings_batch(conn, batch_size):
    """Generate embeddings for a batch of relationships."""
    from pgvector_api import get_ollama_embedding
    
    # Get relationships without embeddings
    rows = await conn.fetch('''
        SELECT relationship_id, source_id, target_id, relationship_type, properties, description
        FROM relationships
        WHERE embedding IS NULL
        AND (description IS NOT NULL OR relationship_type IS NOT NULL)
        LIMIT $1
    ''', batch_size)
    
    if not rows:
        return 0, 0
    
    success = 0
    failed = 0
    
    for row in rows:
        rel_id = row['relationship_id']
        source_id = row['source_id']
        target_id = row['target_id']
        rel_type = row['relationship_type'] or ''
        description = row['description'] or ''
        
        try:
            # Create description
            if description:
                text = description
            else:
                text = f'{source_id} {rel_type} {target_id}'
            
            # Generate embedding
            embedding_list = get_ollama_embedding(text)
            
            if embedding_list:
                # Convert list to PostgreSQL vector string format
                embedding_str = '[' + ','.join(str(x) for x in embedding_list) + ']'
                
                # Update database
                await conn.execute('''
                    UPDATE relationships
                    SET embedding = $1::vector,
                        description = COALESCE(description, $2),
                        keywords = COALESCE(keywords, $3)
                    WHERE relationship_id = $4
                ''', embedding_str, text, rel_type, rel_id)
                success += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            log_message(f"Error on {rel_id}: {str(e)[:80]}")
    
    return success, failed


async def get_stats(conn):
    """Get current embedding statistics."""
    total = await conn.fetchval('SELECT COUNT(*) FROM relationships')
    with_emb = await conn.fetchval('SELECT COUNT(*) FROM relationships WHERE embedding IS NOT NULL')
    return total, with_emb


async def run_processor():
    """Main processor loop."""
    # Check if already running
    running, pid = is_running()
    if running:
        log_message(f"Processor is already running (PID: {pid})")
        return
    
    # Save PID
    save_pid()
    
    log_message("=" * 60)
    log_message("Background Embedding Processor Started")
    log_message(f"Batch Size: {BATCH_SIZE}")
    log_message(f"Interval: {INTERVAL_SECONDS} seconds")
    log_message("=" * 60)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        log_message("\nShutdown signal received, stopping processor...")
        remove_pid()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            database='kg_rag',
            user='postgres',
            password='postgres'
        )
        
        total_processed = 0
        start_time = time.time()
        
        while True:
            # Get stats before batch
            total, with_emb_before = await get_stats(conn)
            
            # Generate batch
            success, failed = await generate_embeddings_batch(conn, BATCH_SIZE)
            
            # Get stats after batch
            _, with_emb_after = await get_stats(conn)
            
            total_processed += success
            elapsed = time.time() - start_time
            rate = (total_processed / elapsed * 60) if elapsed > 0 else 0
            
            percentage = (with_emb_after / total * 100) if total > 0 else 0
            
            log_message(f"Batch Complete: +{success} embeddings | "
                       f"Total: {with_emb_after:,} ({percentage:.2f}%) | "
                       f"Rate: {rate:.1f}/min")
            
            if success == 0 and failed == 0:
                # No more relationships to process
                log_message("No more relationships without embeddings. Stopping.")
                break
            
            # Wait before next batch
            log_message(f"Waiting {INTERVAL_SECONDS}s before next batch...")
            await asyncio.sleep(INTERVAL_SECONDS)
    
    except Exception as e:
        log_message(f"Error in processor: {e}")
        import traceback
        log_message(traceback.format_exc())
    finally:
        if 'conn' in locals():
            await conn.close()
        remove_pid()
        log_message("Processor stopped")


def show_status():
    """Show current processor status."""
    running, pid = is_running()
    
    print("=" * 60)
    print("Background Embedding Processor Status")
    print("=" * 60)
    
    if running:
        print(f"Status: 🟢 RUNNING (PID: {pid})")
    else:
        print(f"Status: 🔴 STOPPED")
    
    # Show recent log entries
    if os.path.exists(LOG_FILE):
        print("\nRecent Log Entries:")
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()[-10:]
            for line in lines:
                print(f"  {line.rstrip()}")
    
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 background_embedding_processor.py start   # Start processor")
        print("  python3 background_embedding_processor.py stop    # Stop processor")
        print("  python3 background_embedding_processor.py status  # Check status")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        # Check if already running
        running, pid = is_running()
        if running:
            print(f"Processor is already running (PID: {pid})")
            sys.exit(0)
        
        # Clear log file
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        
        print("Starting background embedding processor...")
        
        # Fork to background (Unix-like systems)
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process
                print(f"Processor started in background (PID: {pid})")
                print(f"Log file: {LOG_FILE}")
                print(f"Run 'python3 background_embedding_processor.py status' to check progress")
                sys.exit(0)
        except OSError:
            # Windows or fork not available, run in foreground
            print("Running in foreground mode (close terminal to stop)")
            pass
        
        # Run the processor
        asyncio.run(run_processor())
    
    elif command == 'stop':
        if stop_processor():
            print("Processor stopped successfully")
        else:
            print("Failed to stop processor")
            sys.exit(1)
    
    elif command == 'status':
        show_status()
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: start | stop | status")
        sys.exit(1)


if __name__ == "__main__":
    main()
