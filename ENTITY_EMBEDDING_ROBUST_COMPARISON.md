# Entity Embedding Script - Robustness Comparison

## Overview
The entity embedding backfill script has been enhanced to match the robustness of the relationship embedding processor.

## Comparison Table

| Feature | Original (`backfill_entity_embeddings.py`) | Robust (`backfill_entity_embeddings_robust.py`) |
|---------|-------------------------------------------|------------------------------------------------|
| **Architecture** | Basic asyncio | Pure asyncio with proper structure |
| **Circuit Breaker** | ❌ No | ✅ Yes (5 failures → open, 5 min recovery) |
| **Retry Logic** | ❌ Basic loop | ✅ Exponential backoff (1s, 2s, 4s) |
| **Health Monitor** | ❌ Simple logging | ✅ Heartbeat file (JSON, 60s interval) |
| **Connection Pool** | ❌ Single connection | ✅ Connection pool (2-10 connections) |
| **HTTP Session** | ❌ New session per request | ✅ Reusable aiohttp session |
| **Graceful Shutdown** | ❌ Basic signal handling | ✅ Full signal handling with cleanup |
| **Timeouts** | ❌ None | ✅ HTTP 30s, DB 30s |
| **Structured Logging** | ❌ Print statements | ✅ Python logging with file output |
| **PID Management** | ✅ Yes | ✅ Yes (same) |
| **Resume Capability** | ✅ Yes | ✅ Yes (same) |
| **Status Command** | ✅ Yes | ✅ Yes (enhanced) |
| **Wait for Relationships** | ✅ Yes | ✅ Yes (same) |

## Key Improvements

### 1. Circuit Breaker Pattern
```python
# Prevents hammering Ollama when it's failing
class CircuitBreaker:
    def __init__(self, threshold=5, timeout=300):
        self.state = 'CLOSED'  # CLOSED → OPEN → HALF_OPEN → CLOSED
        
    async def call(self, func, *args, **kwargs):
        # Opens after 5 failures
        # Prevents cascade failures
        # Auto-recovers after 5 minutes
```

### 2. Health Monitoring
```python
class HealthMonitor:
    # Writes heartbeat every 60 seconds
    # Format: JSON with pid, status, timestamp, batch_count, entity_count
    # File: /tmp/kg_rag_entity_processor_heartbeat
```

### 3. Connection Pooling
```python
# Original: Single connection per batch
self.conn = await asyncpg.connect(...)

# Robust: Connection pool
self.db_pool = await asyncpg.create_pool(
    min_size=2,
    max_size=10,
    command_timeout=30.0
)
```

### 4. Proper HTTP Session Management
```python
# Original: Created new session implicitly
# Robust: Reusable session with timeouts
timeout = aiohttp.ClientTimeout(total=30.0)
self.http_session = aiohttp.ClientSession(timeout=timeout)
```

### 5. Structured Logging
```python
# Original
print(f"[Upload] Processing {entity_id}")

# Robust
logger.info(f"Batch {batch_count}: +{success} embeddings")
logger.error(f"Failed {entity_id}: {error}")
logger.warning(f"Retrying in {delay}s...")
```

## File Locations

| Component | Original | Robust |
|-----------|----------|--------|
| **Script** | `backfill_entity_embeddings.py` | `backfill_entity_embeddings_robust.py` |
| **Log File** | `/tmp/entity_backfill.log` | `/tmp/kg_rag_entity_processor_robust.log` |
| **PID File** | `/tmp/kg_rag_entity_embedding_backfill.pid` | `/tmp/kg_rag_entity_processor_robust.pid` |
| **Heartbeat** | None | `/tmp/kg_rag_entity_processor_heartbeat` |

## Usage Comparison

### Original Script
```bash
# Start
python3 backfill_entity_embeddings.py --continuous

# Stop
kill $(cat /tmp/kg_rag_entity_embedding_backfill.pid)

# Status
python3 backfill_entity_embeddings.py --status
```

### Robust Script
```bash
# Start
python3 backfill_entity_embeddings_robust.py

# Stop (graceful)
python3 backfill_entity_embeddings_robust.py --stop

# Status
python3 backfill_entity_embeddings_robust.py --status
```

## Error Handling Comparison

### Scenario: Ollama Fails

| Aspect | Original | Robust |
|--------|----------|--------|
| **Immediate retry** | 3 attempts | 3 attempts with backoff |
| **Circuit breaker** | No | Opens after 5 failures |
| **Logging** | Print error | Log error with context |
| **Recovery** | Manual restart | Auto after 5 min |

### Scenario: Database Connection Lost

| Aspect | Original | Robust |
|--------|----------|--------|
| **Detection** | Crash | Caught, logged |
| **Recovery** | Manual restart | Pool reconnects |
| **Data loss** | Possible | Batch failed, retry next |

## Configuration Comparison

### Original Config
```python
DEFAULT_BATCH_SIZE = 100
DEFAULT_INTERVAL = 60
PID_FILE = "/tmp/..."
LOG_FILE = "/tmp/..."
```

### Robust Config
```python
@dataclass
class Config:
    BATCH_SIZE: int = 100
    INTERVAL_SECONDS: int = 60
    MAX_RETRIES: int = 3
    RETRY_DELAY_BASE: float = 1.0
    HTTP_TIMEOUT: float = 30.0
    DB_TIMEOUT: float = 30.0
    HEARTBEAT_INTERVAL: int = 60
    CIRCUIT_BREAKER_THRESHOLD: int = 5
    CIRCUIT_BREAKER_TIMEOUT: int = 300
```

## Recommendations

### Use Robust Version When:
- Running for long periods (hours/days)
- Production environment
- Need monitoring/observability
- Want automatic recovery
- Running unattended

### Use Original Version When:
- Quick one-time batch
- Debugging/testing
- Simple use case
- Manual supervision

## Migration Guide

### From Original to Robust
```bash
# 1. Stop original
kill $(cat /tmp/kg_rag_entity_embedding_backfill.pid)

# 2. Start robust
python3 backfill_entity_embeddings_robust.py --wait-for-relationships

# 3. Monitor
python3 backfill_entity_embeddings_robust.py --status
tail -f /tmp/kg_rag_entity_processor_robust.log
```

### Unified Management
```bash
# Both processors now have same interface
python3 manage_embeddings.py relationships start
python3 manage_embeddings.py entities start --wait

# Or start everything
python3 manage_embeddings.py start-all
```

## Testing Robust Features

### Test Circuit Breaker
```bash
# 1. Start processor
python3 backfill_entity_embeddings_robust.py &

# 2. Stop Ollama
killall ollama

# 3. Watch logs - should see circuit breaker open after 5 failures
tail -f /tmp/kg_rag_entity_processor_robust.log

# 4. Restart Ollama - should see circuit breaker close
ollama serve
```

### Test Health Monitor
```bash
# Check heartbeat file
cat /tmp/kg_rag_entity_processor_heartbeat

# Watch updates
watch -n 1 'cat /tmp/kg_rag_entity_processor_heartbeat'
```

### Test Graceful Shutdown
```bash
# Start processor
python3 backfill_entity_embeddings_robust.py &
PID=$!

# Stop gracefully
kill -TERM $PID

# Check log for clean shutdown message
tail /tmp/kg_rag_entity_processor_robust.log
```

## Summary

The robust version provides:
1. **Better reliability** - Circuit breaker prevents cascade failures
2. **Better observability** - Health heartbeats, structured logs
3. **Better resource management** - Connection pooling, reusable sessions
4. **Better error handling** - Timeouts, retries, graceful degradation
5. **Better operations** - Status command, graceful shutdown, PID management

Both versions are kept for flexibility, but the **robust version is recommended** for production use.
