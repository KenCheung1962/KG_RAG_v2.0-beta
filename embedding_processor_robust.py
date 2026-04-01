#!/usr/bin/env python3
"""
Robust Background Embedding Processor for KG RAG

Features:
- Pure asyncio (no fork, no threading issues)
- Proper timeouts on all operations
- Automatic retry with exponential backoff
- Health check heartbeat file
- Graceful shutdown handling
- Circuit breaker for Ollama failures
- Connection pooling for PostgreSQL

Usage:
    # Start (run in screen/tmux or use nohup)
    python3 embedding_processor_robust.py
    
    # Or with nohup
    nohup python3 embedding_processor_robust.py > processor.log 2>&1 &
    
    # Stop gracefully
    kill -TERM <pid>
    
    # Check status
    python3 embedding_processor_robust.py --status
"""

import asyncio
import asyncpg
import aiohttp
import sys
import os
import signal
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager
import logging

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/kg_rag_processor_robust.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
@dataclass
class Config:
    BATCH_SIZE: int = 100
    INTERVAL_SECONDS: int = 60
    DB_HOST: str = 'localhost'
    DB_PORT: int = 5432
    DB_NAME: str = 'kg_rag'
    DB_USER: str = 'postgres'
    DB_PASSWORD: str = 'postgres'
    OLLAMA_URL: str = 'http://127.0.0.1:11434/api/embed'
    OLLAMA_MODEL: str = 'nomic-embed-text'
    EMBEDDING_DIM: int = 768
    MAX_RETRIES: int = 3
    RETRY_DELAY_BASE: float = 1.0  # seconds
    HTTP_TIMEOUT: float = 30.0
    DB_TIMEOUT: float = 30.0
    HEARTBEAT_INTERVAL: int = 60  # seconds
    HEARTBEAT_FILE: str = '/tmp/kg_rag_processor_heartbeat'
    PID_FILE: str = '/tmp/kg_rag_processor_robust.pid'
    CIRCUIT_BREAKER_THRESHOLD: int = 5  # failures before opening circuit
    CIRCUIT_BREAKER_TIMEOUT: int = 300  # seconds to wait before retry


class CircuitBreaker:
    """Circuit breaker pattern to avoid hammering failing services."""
    
    def __init__(self, threshold: int = 5, timeout: int = 300):
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()
    
    async def call(self, func, *args, **kwargs):
        async with self._lock:
            if self.state == 'OPEN':
                if self.last_failure_time and \
                   (datetime.now() - self.last_failure_time).seconds > self.timeout:
                    self.state = 'HALF_OPEN'
                    logger.info("Circuit breaker entering HALF_OPEN state")
                else:
                    raise Exception(f"Circuit breaker OPEN - Ollama unavailable")
        
        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                if self.state in ('OPEN', 'HALF_OPEN'):
                    self.state = 'CLOSED'
                    self.failures = 0
                    logger.info("Circuit breaker CLOSED - service recovered")
            return result
        except Exception as e:
            async with self._lock:
                self.failures += 1
                self.last_failure_time = datetime.now()
                if self.failures >= self.threshold:
                    self.state = 'OPEN'
                    logger.error(f"Circuit breaker OPEN after {self.failures} failures")
            raise


class HealthMonitor:
    """Health monitor that writes heartbeat files."""
    
    def __init__(self, config: Config):
        self.config = config
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info("Health monitor started")
    
    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Write final heartbeat
        self._write_heartbeat("stopped")
        logger.info("Health monitor stopped")
    
    async def _heartbeat_loop(self):
        while self._running:
            try:
                self._write_heartbeat("running")
                await asyncio.sleep(self.config.HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    def _write_heartbeat(self, status: str):
        data = {
            'pid': os.getpid(),
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'batch_count': getattr(self, 'batch_count', 0)
        }
        try:
            with open(self.config.HEARTBEAT_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to write heartbeat: {e}")


class EmbeddingProcessor:
    """Main embedding processor with robust error handling."""
    
    def __init__(self, config: Config):
        self.config = config
        self.db_pool: Optional[asyncpg.Pool] = None
        self.http_session: Optional[aiohttp.ClientSession] = None
        self.circuit_breaker = CircuitBreaker(
            config.CIRCUIT_BREAKER_THRESHOLD,
            config.CIRCUIT_BREAKER_TIMEOUT
        )
        self.health_monitor = HealthMonitor(config)
        self._shutdown_event = asyncio.Event()
        self.batch_count = 0
        self.total_processed = 0
        self.running = False
    
    async def initialize(self):
        """Initialize database pool and HTTP session."""
        # Create database pool with proper timeouts
        self.db_pool = await asyncpg.create_pool(
            host=self.config.DB_HOST,
            port=self.config.DB_PORT,
            database=self.config.DB_NAME,
            user=self.config.DB_USER,
            password=self.config.DB_PASSWORD,
            min_size=2,
            max_size=10,
            command_timeout=self.config.DB_TIMEOUT,
            server_settings={
                'application_name': 'kg_rag_embedding_processor'
            }
        )
        logger.info("Database pool created")
        
        # Create HTTP session with timeout
        timeout = aiohttp.ClientTimeout(total=self.config.HTTP_TIMEOUT)
        self.http_session = aiohttp.ClientSession(timeout=timeout)
        logger.info("HTTP session created")
        
        # Setup signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(
                sig, lambda: asyncio.create_task(self.shutdown())
            )
        logger.info("Signal handlers registered")
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutdown signal received, initiating graceful shutdown...")
        self.running = False
        self._shutdown_event.set()
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.health_monitor.stop()
        
        if self.http_session:
            await self.http_session.close()
            logger.info("HTTP session closed")
        
        if self.db_pool:
            await self.db_pool.close()
            logger.info("Database pool closed")
        
        # Remove PID file
        try:
            if os.path.exists(self.config.PID_FILE):
                os.remove(self.config.PID_FILE)
        except Exception as e:
            logger.error(f"Failed to remove PID file: {e}")
    
    async def get_ollama_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from Ollama with proper async handling."""
        payload = {
            'model': self.config.OLLAMA_MODEL,
            'input': text[:8000]  # Limit text length
        }
        
        async with self.http_session.post(
            self.config.OLLAMA_URL,
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Ollama HTTP {response.status}: {error_text}")
            
            data = await response.json()
            
            if 'embeddings' in data and len(data['embeddings']) > 0:
                embedding = data['embeddings'][0]
                if len(embedding) == self.config.EMBEDDING_DIM:
                    return embedding
                else:
                    raise Exception(f"Invalid embedding dimension: {len(embedding)}")
            else:
                raise Exception("No embeddings in response")
    
    async def get_ollama_embedding_with_retry(self, text: str) -> Optional[List[float]]:
        """Get embedding with retry logic and circuit breaker."""
        for attempt in range(self.config.MAX_RETRIES):
            try:
                return await self.circuit_breaker.call(
                    self.get_ollama_embedding, text
                )
            except Exception as e:
                if attempt < self.config.MAX_RETRIES - 1:
                    delay = self.config.RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning(f"Embedding attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.config.MAX_RETRIES} embedding attempts failed: {e}")
                    return None
        return None
    
    async def process_batch(self) -> Tuple[int, int]:
        """Process a batch of relationships. Returns (success, failed)."""
        async with self.db_pool.acquire() as conn:
            # Get batch of relationships without embeddings
            rows = await conn.fetch('''
                SELECT relationship_id, source_id, target_id, relationship_type, description
                FROM relationships
                WHERE embedding IS NULL
                AND (description IS NOT NULL OR relationship_type IS NOT NULL)
                LIMIT $1
            ''', self.config.BATCH_SIZE)
            
            if not rows:
                return 0, 0
            
            success = 0
            failed = 0
            
            for row in rows:
                # Check for shutdown signal
                if self._shutdown_event.is_set():
                    logger.info("Shutdown requested, stopping batch processing")
                    break
                
                rel_id = row['relationship_id']
                source_id = row['source_id']
                target_id = row['target_id']
                rel_type = row['relationship_type'] or ''
                description = row['description'] or ''
                
                # Create description text
                if description:
                    text = description
                else:
                    text = f"{source_id} {rel_type} {target_id}"
                
                # Generate embedding
                embedding = await self.get_ollama_embedding_with_retry(text)
                
                if embedding:
                    try:
                        # Convert to PostgreSQL vector format
                        embedding_str = '[' + ','.join(str(x) for x in embedding) + ']'
                        
                        # Update database
                        await conn.execute('''
                            UPDATE relationships
                            SET embedding = $1::vector,
                                description = COALESCE(description, $2)
                            WHERE relationship_id = $3
                        ''', embedding_str, text, rel_id)
                        success += 1
                    except Exception as e:
                        logger.error(f"Database update failed for {rel_id}: {e}")
                        failed += 1
                else:
                    failed += 1
            
            return success, failed
    
    async def get_stats(self) -> Tuple[int, int, float]:
        """Get embedding statistics. Returns (total, with_embeddings, percentage)."""
        async with self.db_pool.acquire() as conn:
            total = await conn.fetchval('SELECT COUNT(*) FROM relationships')
            with_emb = await conn.fetchval('SELECT COUNT(*) FROM relationships WHERE embedding IS NOT NULL')
            percentage = (with_emb / total * 100) if total > 0 else 0
            return total, with_emb, percentage
    
    async def run(self):
        """Main processor loop."""
        self.running = True
        
        # Write PID file
        with open(self.config.PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        # Start health monitor
        await self.health_monitor.start()
        
        logger.info("=" * 60)
        logger.info("Robust Embedding Processor Started")
        logger.info(f"Batch Size: {self.config.BATCH_SIZE}")
        logger.info(f"Interval: {self.config.INTERVAL_SECONDS}s")
        logger.info(f"PID: {os.getpid()}")
        logger.info("=" * 60)
        
        try:
            while self.running and not self._shutdown_event.is_set():
                start_time = datetime.now()
                
                try:
                    # Process batch
                    success, failed = await self.process_batch()
                    self.batch_count += 1
                    self.total_processed += success
                    
                    # Get stats
                    total, with_emb, percentage = await self.get_stats()
                    
                    # Calculate rate
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = (success / elapsed * 60) if elapsed > 0 else 0
                    
                    # Log progress
                    logger.info(
                        f"Batch {self.batch_count}: +{success} embeddings "
                        f"({failed} failed) | Total: {with_emb}/{total} ({percentage:.2f}%) "
                        f"| Rate: {rate:.1f}/min"
                    )
                    
                    # Update health monitor batch count
                    self.health_monitor.batch_count = self.batch_count
                    
                    # Check if all done
                    if success == 0 and failed == 0:
                        logger.info("No more relationships to process. Stopping.")
                        break
                    
                    # Check for shutdown
                    if self._shutdown_event.is_set():
                        break
                    
                    # Wait before next batch
                    logger.debug(f"Waiting {self.config.INTERVAL_SECONDS}s before next batch...")
                    try:
                        await asyncio.wait_for(
                            self._shutdown_event.wait(),
                            timeout=self.config.INTERVAL_SECONDS
                        )
                    except asyncio.TimeoutError:
                        pass  # Normal interval timeout, continue
                    
                except Exception as e:
                    logger.exception(f"Error in processing loop: {e}")
                    await asyncio.sleep(self.config.INTERVAL_SECONDS)
        
        finally:
            await self.cleanup()
            logger.info("Processor stopped")


def check_status():
    """Check processor status from heartbeat file."""
    config = Config()
    
    print("=" * 60)
    print("Robust Embedding Processor Status")
    print("=" * 60)
    
    # Check PID file
    pid = None
    if os.path.exists(config.PID_FILE):
        try:
            with open(config.PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Check if process exists
            os.kill(pid, 0)
            print(f"PID File: 🟢 Found (PID: {pid})")
        except (ValueError, OSError, ProcessLookupError):
            print(f"PID File: 🔴 Stale (PID: {pid} not running)")
            pid = None
    else:
        print("PID File: 🔴 Not found")
    
    # Check heartbeat
    if os.path.exists(config.HEARTBEAT_FILE):
        try:
            with open(config.HEARTBEAT_FILE, 'r') as f:
                heartbeat = json.load(f)
            
            hb_time = datetime.fromisoformat(heartbeat['timestamp'])
            age = (datetime.now() - hb_time).total_seconds()
            
            print(f"\nHeartbeat File: 🟢 Found")
            print(f"  Status: {heartbeat.get('status', 'unknown')}")
            print(f"  PID: {heartbeat.get('pid', 'unknown')}")
            print(f"  Last Update: {age:.1f}s ago")
            print(f"  Batches: {heartbeat.get('batch_count', 0)}")
            
            if age > config.HEARTBEAT_INTERVAL * 2:
                print(f"  ⚠️  WARNING: Heartbeat is stale (> {config.HEARTBEAT_INTERVAL * 2}s)")
        except Exception as e:
            print(f"\nHeartbeat File: 🟡 Error reading: {e}")
    else:
        print(f"\nHeartbeat File: 🔴 Not found")
    
    # Overall status
    print(f"\n{'=' * 60}")
    if pid:
        print("Overall Status: 🟢 RUNNING")
    else:
        print("Overall Status: 🔴 NOT RUNNING")
    print("=" * 60)


def stop_processor():
    """Stop the running processor."""
    config = Config()
    
    if not os.path.exists(config.PID_FILE):
        print("PID file not found. Processor may not be running.")
        return False
    
    try:
        with open(config.PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        
        print(f"Sending TERM signal to PID {pid}...")
        os.kill(pid, signal.SIGTERM)
        
        # Wait for process to stop
        for i in range(20):
            try:
                os.kill(pid, 0)
                print(f"  Waiting... ({i + 1}/20)")
                import time
                time.sleep(0.5)
            except ProcessLookupError:
                print("Process stopped successfully")
                return True
        
        print("Process didn't stop, sending KILL...")
        os.kill(pid, signal.SIGKILL)
        return True
        
    except Exception as e:
        print(f"Error stopping processor: {e}")
        return False


async def main():
    parser = argparse.ArgumentParser(description='Robust Background Embedding Processor')
    parser.add_argument('--status', action='store_true', help='Check processor status')
    parser.add_argument('--stop', action='store_true', help='Stop running processor')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size')
    parser.add_argument('--interval', type=int, default=60, help='Interval between batches (seconds)')
    parser.add_argument('--foreground', action='store_true', help='Run in foreground (default)')
    args = parser.parse_args()
    
    if args.status:
        check_status()
        return
    
    if args.stop:
        stop_processor()
        return
    
    # Check if already running
    config = Config()
    if os.path.exists(config.PID_FILE):
        try:
            with open(config.PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f"Processor is already running (PID: {pid})")
            print("Use --status to check status or --stop to stop it")
            sys.exit(1)
        except (ValueError, OSError, ProcessLookupError):
            # Stale PID file
            os.remove(config.PID_FILE)
    
    # Create and run processor
    config.BATCH_SIZE = args.batch_size
    config.INTERVAL_SECONDS = args.interval
    
    processor = EmbeddingProcessor(config)
    await processor.initialize()
    await processor.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
