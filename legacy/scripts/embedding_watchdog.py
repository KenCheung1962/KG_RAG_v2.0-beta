#!/usr/bin/env python3
"""
Watchdog for Embedding Processor

Monitors the heartbeat file and restarts the processor if it becomes stale.
Can be run as a cron job or daemon.

Usage:
    # Run once (check and restart if needed)
    python3 embedding_watchdog.py
    
    # Run continuously
    python3 embedding_watchdog.py --daemon
    
    # Add to crontab (check every 2 minutes)
    */2 * * * * cd /Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta && python3 embedding_watchdog.py >> /tmp/kg_rag_watchdog.log 2>&1
"""

import os
import sys
import json
import subprocess
import argparse
import time
from datetime import datetime
from pathlib import Path

HEARTBEAT_FILE = '/tmp/kg_rag_processor_heartbeat'
PID_FILE = '/tmp/kg_rag_processor_robust.pid'
PROCESSOR_SCRIPT = '/Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta/embedding_processor_robust.py'
LOG_FILE = '/tmp/kg_rag_watchdog.log'
STALE_THRESHOLD = 180  # seconds (3 minutes)


def log(message):
    """Log with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')


def is_process_running(pid):
    """Check if a process is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def check_processor():
    """Check if processor is healthy."""
    # Check heartbeat file
    if not os.path.exists(HEARTBEAT_FILE):
        log("🔴 No heartbeat file found")
        return False, "no_heartbeat_file"
    
    try:
        with open(HEARTBEAT_FILE, 'r') as f:
            heartbeat = json.load(f)
        
        hb_time = datetime.fromisoformat(heartbeat['timestamp'])
        age = (datetime.now() - hb_time).total_seconds()
        
        # Check if heartbeat is stale
        if age > STALE_THRESHOLD:
            log(f"🔴 Heartbeat stale: {age:.1f}s old (threshold: {STALE_THRESHOLD}s)")
            return False, "stale_heartbeat"
        
        # Check if process exists
        pid = heartbeat.get('pid')
        if pid and not is_process_running(pid):
            log(f"🔴 Process {pid} not running (but heartbeat is fresh)")
            return False, "process_dead"
        
        log(f"🟢 Processor healthy (PID: {pid}, heartbeat: {age:.1f}s ago)")
        return True, "healthy"
        
    except Exception as e:
        log(f"🔴 Error reading heartbeat: {e}")
        return False, "heartbeat_error"


def stop_processor():
    """Stop any running processor."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            if is_process_running(pid):
                log(f"Stopping processor (PID: {pid})...")
                os.kill(pid, 15)  # SIGTERM
                
                # Wait for stop
                for i in range(10):
                    if not is_process_running(pid):
                        log("Processor stopped")
                        return True
                    time.sleep(0.5)
                
                # Force kill
                log("Force killing processor...")
                os.kill(pid, 9)
                time.sleep(0.5)
        except Exception as e:
            log(f"Error stopping processor: {e}")
    
    # Clean up stale files
    for f in [PID_FILE, HEARTBEAT_FILE]:
        if os.path.exists(f):
            os.remove(f)
    
    return True


def start_processor():
    """Start the processor."""
    log("Starting processor...")
    
    try:
        # Use nohup to keep running after logout
        proc = subprocess.Popen(
            ['nohup', 'python3', PROCESSOR_SCRIPT],
            stdout=open('/tmp/kg_rag_processor.out', 'a'),
            stderr=open('/tmp/kg_rag_processor.err', 'a'),
            start_new_session=True  # Detach from parent
        )
        
        log(f"Processor started (PID: {proc.pid})")
        
        # Wait a moment and verify
        time.sleep(2)
        
        if is_process_running(proc.pid):
            log("✅ Processor verified running")
            return True
        else:
            log("❌ Processor failed to start")
            return False
            
    except Exception as e:
        log(f"❌ Error starting processor: {e}")
        return False


def restart_processor():
    """Restart the processor."""
    log("=" * 50)
    log("RESTARTING PROCESSOR")
    log("=" * 50)
    
    stop_processor()
    time.sleep(1)
    return start_processor()


def run_watchdog_cycle():
    """Run one watchdog check cycle."""
    healthy, reason = check_processor()
    
    if not healthy:
        restart_processor()
        return False
    
    return True


def run_daemon():
    """Run watchdog in daemon mode."""
    log("=" * 50)
    log("WATCHDOG DAEMON STARTED")
    log(f"Check interval: 60 seconds")
    log(f"Stale threshold: {STALE_THRESHOLD} seconds")
    log("=" * 50)
    
    while True:
        try:
            run_watchdog_cycle()
            time.sleep(60)
        except KeyboardInterrupt:
            log("Daemon stopped by user")
            break
        except Exception as e:
            log(f"Error in daemon: {e}")
            time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description='Embedding Processor Watchdog')
    parser.add_argument('--daemon', action='store_true', help='Run continuously')
    parser.add_argument('--stop', action='store_true', help='Stop processor')
    parser.add_argument('--start', action='store_true', help='Start processor')
    parser.add_argument('--restart', action='store_true', help='Restart processor')
    args = parser.parse_args()
    
    if args.stop:
        stop_processor()
        return
    
    if args.start:
        start_processor()
        return
    
    if args.restart:
        restart_processor()
        return
    
    if args.daemon:
        run_daemon()
    else:
        # Single check
        healthy, reason = check_processor()
        if not healthy:
            restart_processor()
        sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    main()
