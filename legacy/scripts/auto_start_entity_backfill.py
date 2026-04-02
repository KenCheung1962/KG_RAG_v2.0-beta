#!/usr/bin/env python3
"""
Auto-start Entity Embedding Backfill

Monitors relationship embedding progress and automatically starts
the entity embedding backfill when relationships reach the threshold.

Usage:
    # Run in foreground (recommended for testing)
    python3 auto_start_entity_backfill.py
    
    # Run in background
    nohup python3 auto_start_entity_backfill.py > auto_backfill.log 2>&1 &
    
    # Check status
    python3 auto_start_entity_backfill.py --status
    
    # Stop monitoring
    python3 auto_start_entity_backfill.py --stop
"""

import asyncio
import asyncpg
import os
import signal
import sys
import subprocess
import time
from datetime import datetime

# Configuration
CHECK_INTERVAL = 900   # seconds (15 minutes)
THRESHOLD_PERCENT = 99.0  # Start entity backfill at 99%
PID_FILE = "/tmp/kg_rag_auto_backfill.pid"
LOG_FILE = "/tmp/kg_rag_auto_backfill.log"

# Database config (match your setup)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'kg_rag',
    'user': 'postgres',
    'password': 'postgres'
}


def log_message(msg: str):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    
    # Also write to log file
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')


def write_pid():
    """Write PID file"""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))


def remove_pid():
    """Remove PID file"""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def check_pid():
    """Check if already running"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)  # Check if process exists
            return pid
        except (ValueError, OSError, ProcessLookupError):
            remove_pid()
    return None


async def get_relationship_stats():
    """Get current relationship embedding stats"""
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        try:
            total = await conn.fetchval('SELECT COUNT(*) FROM relationships')
            with_emb = await conn.fetchval(
                'SELECT COUNT(*) FROM relationships WHERE embedding IS NOT NULL'
            )
            percentage = (with_emb / total * 100) if total > 0 else 0
            return total, with_emb, percentage
        finally:
            await conn.close()
    except Exception as e:
        log_message(f"❌ Database error: {e}")
        return None, None, None


def start_entity_backfill():
    """Start the entity embedding backfill process"""
    log_message("🚀 Starting entity embedding backfill...")
    
    try:
        # Start in background using nohup
        process = subprocess.Popen(
            ['python3', 'backfill_entity_embeddings_robust.py'],
            stdout=open('/tmp/entity_backfill.log', 'w'),
            stderr=subprocess.STDOUT,
            cwd='/Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta'
        )
        
        log_message(f"✅ Entity backfill started (PID: {process.pid})")
        log_message(f"📝 Log file: /tmp/entity_backfill.log")
        return True
        
    except Exception as e:
        log_message(f"❌ Failed to start entity backfill: {e}")
        return False


async def monitor_and_start():
    """Main monitoring loop"""
    log_message("=" * 60)
    log_message("Auto-Start Entity Backfill Monitor")
    log_message("=" * 60)
    log_message(f"Threshold: {THRESHOLD_PERCENT}%")
    log_message(f"Check interval: {CHECK_INTERVAL} seconds")
    log_message("=" * 60)
    
    entity_started = False
    
    while True:
        try:
            total, with_emb, percentage = await get_relationship_stats()
            
            if total is None:
                log_message("⚠️ Failed to get stats, retrying...")
                await asyncio.sleep(CHECK_INTERVAL)
                continue
            
            remaining = total - with_emb
            
            log_message(
                f"📊 Relationships: {with_emb:,}/{total:,} "
                f"({percentage:.2f}%) | Remaining: {remaining:,}"
            )
            
            # Check if threshold reached
            if percentage >= THRESHOLD_PERCENT and not entity_started:
                log_message("🎯 Threshold reached! Starting entity backfill...")
                
                if start_entity_backfill():
                    entity_started = True
                    log_message("✅ Entity backfill started successfully!")
                    log_message("⏳ Continuing to monitor relationship processor...")
                else:
                    log_message("❌ Failed to start entity backfill, will retry...")
            
            # If entity started and relationships complete, we can exit
            if entity_started and percentage >= 99.9:
                log_message("✅ Relationships complete and entity backfill started!")
                log_message("📝 Entity backfill is running in background.")
                log_message("👋 Exiting monitor.")
                break
            
            # Calculate ETA
            if remaining > 0:
                rate = 700  # Estimated rate
                eta_min = remaining / rate
                log_message(f"⏱️  ETA to {THRESHOLD_PERCENT}%: ~{eta_min:.0f} min")
            
            await asyncio.sleep(CHECK_INTERVAL)
            
        except asyncio.CancelledError:
            log_message("🛑 Monitor stopped by user")
            break
        except Exception as e:
            log_message(f"❌ Error: {e}")
            await asyncio.sleep(CHECK_INTERVAL)


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    log_message("🛑 Received shutdown signal")
    remove_pid()
    sys.exit(0)


def main():
    """Main entry point"""
    # Check command line args
    if len(sys.argv) > 1:
        if sys.argv[1] == '--status':
            pid = check_pid()
            if pid:
                print(f"✅ Monitor is running (PID: {pid})")
                print(f"📝 Log file: {LOG_FILE}")
            else:
                print("❌ Monitor is not running")
            return
        
        elif sys.argv[1] == '--stop':
            pid = check_pid()
            if pid:
                try:
                    os.kill(pid, signal.SIGTERM)
                    print(f"🛑 Stopped monitor (PID: {pid})")
                except ProcessLookupError:
                    print("❌ Process not found")
                    remove_pid()
            else:
                print("❌ Monitor is not running")
            return
    
    # Check if already running
    existing_pid = check_pid()
    if existing_pid:
        print(f"❌ Monitor already running (PID: {existing_pid})")
        print(f"📝 Check status: python3 auto_start_entity_backfill.py --status")
        print(f"🛑 Stop first: python3 auto_start_entity_backfill.py --stop")
        sys.exit(1)
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Write PID file
    write_pid()
    
    try:
        # Start monitoring
        asyncio.run(monitor_and_start())
    finally:
        remove_pid()


if __name__ == "__main__":
    main()
