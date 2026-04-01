#!/usr/bin/env python3
"""
Unified Embedding Management Script for KG RAG v2.0-beta

Manages both relationship and entity embedding processes.

Usage:
    # Show status of all embeddings
    python3 manage_embeddings.py status
    
    # Manage relationship embeddings
    python3 manage_embeddings.py relationships status
    python3 manage_embeddings.py relationships start
    python3 manage_embeddings.py relationships stop
    
    # Manage entity embeddings
    python3 manage_embeddings.py entities status
    python3 manage_embeddings.py entities start
    python3 manage_embeddings.py entities stop
    
    # Start entity backfill after relationships complete
    python3 manage_embeddings.py entities start --wait
    
    # Start both processes (sequential)
    python3 manage_embeddings.py start-all
"""

import argparse
import sys
import os
import subprocess
import time
from pathlib import Path

# Process PID files
RELATIONSHIP_PID_FILE = "/tmp/kg_rag_processor_robust.pid"
ENTITY_PID_FILE = "/tmp/kg_rag_entity_processor_robust.pid"


def run_command(cmd: list, cwd: str = None) -> tuple:
    """Run a command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def check_process_running(pid_file: str) -> bool:
    """Check if a process is running based on PID file."""
    if not os.path.exists(pid_file):
        return False
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError, ProcessLookupError):
        return False


def show_overall_status():
    """Show overall embedding status."""
    print("=" * 70)
    print("KG RAG v2.0-beta - Embedding Status")
    print("=" * 70)
    
    # Check relationship processor
    rel_running = check_process_running(RELATIONSHIP_PID_FILE)
    print(f"\n📊 Relationship Embeddings:")
    print(f"   Process Status: {'🟢 RUNNING' if rel_running else '🔴 STOPPED'}")
    
    # Get relationship stats
    success, output = run_command([
        sys.executable, "monitor_embeddings.py"
    ], cwd="/Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta")
    
    if success:
        for line in output.split('\n'):
            if 'with embeddings' in line.lower() or 'total' in line.lower():
                print(f"   {line.strip()}")
    
    # Check entity backfill
    ent_running = check_process_running(ENTITY_PID_FILE)
    print(f"\n📊 Entity Embeddings:")
    print(f"   Process Status: {'🟢 RUNNING' if ent_running else '🔴 STOPPED'}")
    
    # Get entity stats
    success, output = run_command([
        sys.executable, "backfill_entity_embeddings.py", "--status"
    ], cwd="/Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta")
    
    if success:
        for line in output.split('\n'):
            if 'with embeds' in line.lower() or 'total' in line.lower():
                print(f"   {line.strip()}")
    
    print("\n" + "=" * 70)
    print("\n💡 Commands:")
    print("   python3 manage_embeddings.py relationships start")
    print("   python3 manage_embeddings.py entities start --wait")
    print("=" * 70)


def manage_relationships(command: str):
    """Manage relationship embedding process."""
    v2_path = "/Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta"
    
    if command == "status":
        running = check_process_running(RELATIONSHIP_PID_FILE)
        print(f"Relationship Processor: {'🟢 RUNNING' if running else '🔴 STOPPED'}")
        
        success, output = run_command([
            sys.executable, "embedding_processor_robust.py", "--status"
        ], cwd=v2_path)
        print(output)
        
    elif command == "start":
        if check_process_running(RELATIONSHIP_PID_FILE):
            print("❌ Relationship processor already running")
            return
            
        print("🚀 Starting relationship embedding processor...")
        success, output = run_command([
            sys.executable, "embedding_processor_robust.py"
        ], cwd=v2_path)
        
        if success:
            print("✅ Relationship processor started")
        else:
            print(f"❌ Failed to start: {output}")
            
    elif command == "stop":
        if not check_process_running(RELATIONSHIP_PID_FILE):
            print("⚠️  Relationship processor not running")
            return
            
        print("🛑 Stopping relationship processor...")
        success, output = run_command([
            sys.executable, "embedding_processor_robust.py", "--stop"
        ], cwd=v2_path)
        print(output)
        
    elif command == "restart":
        manage_relationships("stop")
        time.sleep(2)
        manage_relationships("start")


def manage_entities(command: str, wait_for_relationships: bool = False):
    """Manage entity embedding backfill process."""
    v2_path = "/Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta"
    
    if command == "status":
        running = check_process_running(ENTITY_PID_FILE)
        print(f"Entity Backfill: {'🟢 RUNNING' if running else '🔴 STOPPED'}")
        
        success, output = run_command([
            sys.executable, "backfill_entity_embeddings_robust.py", "--status"
        ], cwd=v2_path)
        print(output)
        
    elif command == "start":
        if check_process_running(ENTITY_PID_FILE):
            print("❌ Entity backfill already running")
            return
        
        cmd = [sys.executable, "backfill_entity_embeddings_robust.py"]
        
        if wait_for_relationships:
            cmd.append("--wait-for-relationships")
            print("⏳ Will wait for relationship embeddings to complete, then start entity backfill...")
        else:
            print("🚀 Starting entity embedding backfill...")
        
        # Run in background with nohup-style behavior
        log_file = "/tmp/entity_processor.log"
        with open(log_file, 'a') as log:
            subprocess.Popen(
                cmd,
                cwd=v2_path,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        
        time.sleep(2)
        
        if check_process_running(ENTITY_PID_FILE):
            print("✅ Entity backfill started")
            print("   Log: tail -f /tmp/entity_backfill.log")
        else:
            print("❌ Failed to start entity backfill")
            
    elif command == "stop":
        if not check_process_running(ENTITY_PID_FILE):
            print("⚠️  Entity backfill not running")
            return
            
        print("🛑 Stopping entity backfill...")
        # Read PID and kill
        try:
            with open(ENTITY_PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            print("✅ Entity backfill stopped")
        except Exception as e:
            print(f"❌ Error stopping: {e}")
            
    elif command == "single":
        print("📦 Running entity processor (will process until complete)...")
        print("   To run in background: nohup python3 backfill_entity_embeddings_robust.py > entity_processor.log 2>&1 &")
        success, output = run_command([
            sys.executable, "backfill_entity_embeddings_robust.py"
        ], cwd=v2_path)
        print(output)


def start_all():
    """Start relationship processor, then entity backfill."""
    print("=" * 70)
    print("Starting All Embedding Processes (Sequential)")
    print("=" * 70)
    
    # Step 1: Start relationship processor
    print("\n📌 Step 1: Relationship Embeddings")
    manage_relationships("start")
    
    # Step 2: Wait for relationships to complete, then start entities
    print("\n📌 Step 2: Entity Embeddings (will start after relationships complete)")
    manage_entities("start", wait_for_relationships=True)
    
    print("\n" + "=" * 70)
    print("✅ Both processes started!")
    print("\nMonitor progress:")
    print("   python3 manage_embeddings.py status")
    print("   tail -f /tmp/kg_rag_processor_robust.log")
    print("   tail -f /tmp/entity_backfill.log")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Manage KG RAG v2.0-beta embedding processes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show overall status
  python3 manage_embeddings.py status
  
  # Relationship embeddings
  python3 manage_embeddings.py relationships status
  python3 manage_embeddings.py relationships start
  python3 manage_embeddings.py relationships stop
  python3 manage_embeddings.py relationships restart
  
  # Entity embeddings
  python3 manage_embeddings.py entities status
  python3 manage_embeddings.py entities start        # Start immediately
  python3 manage_embeddings.py entities start --wait # Wait for relationships
  python3 manage_embeddings.py entities stop
  python3 manage_embeddings.py entities single       # One batch only
  
  # Start everything (relationships first, then entities)
  python3 manage_embeddings.py start-all
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Status command
    subparsers.add_parser('status', help='Show overall embedding status')
    
    # Relationships subcommand
    rel_parser = subparsers.add_parser('relationships', help='Manage relationship embeddings')
    rel_parser.add_argument('action', choices=['status', 'start', 'stop', 'restart'],
                           help='Action to perform')
    
    # Entities subcommand
    ent_parser = subparsers.add_parser('entities', help='Manage entity embeddings')
    ent_parser.add_argument('action', choices=['status', 'start', 'stop', 'single'],
                           help='Action to perform')
    ent_parser.add_argument('--wait', action='store_true',
                           help='Wait for relationship embeddings to complete first')
    
    # Start-all command
    subparsers.add_parser('start-all', help='Start relationships then entities')
    
    args = parser.parse_args()
    
    if args.command == 'status' or args.command is None:
        show_overall_status()
    elif args.command == 'relationships':
        manage_relationships(args.action)
    elif args.command == 'entities':
        manage_entities(args.action, wait_for_relationships=args.wait)
    elif args.command == 'start-all':
        start_all()


if __name__ == "__main__":
    import signal
    main()
