# Robust Embedding Processor Upgrade Guide

## Problem with Old Processor

The original `background_embedding_processor.py` had several issues that could cause it to hang:

1. **Fork + Asyncio deadlock** - Uses `os.fork()` which is unsafe with asyncio event loops
2. **Nested event loops** - Uses `asyncio.run()` inside threads, causing potential deadlocks
3. **No timeout on HTTP requests** - Ollama calls could hang indefinitely
4. **No health monitoring** - No way to detect if processor is stuck
5. **No retry logic** - Single failure could stop processing

## New Robust Processor Features

### `embedding_processor_robust.py`

- ✅ **Pure asyncio** - No fork, no threading issues
- ✅ **Proper timeouts** - All operations have timeouts (HTTP: 30s, DB: 30s)
- ✅ **Automatic retry** - Exponential backoff for failures
- ✅ **Circuit breaker** - Stops hammering Ollama if it's down
- ✅ **Health heartbeat** - Writes status file every 60s
- ✅ **Graceful shutdown** - Handles SIGTERM/SIGINT properly
- ✅ **Connection pooling** - Efficient PostgreSQL connection reuse
- ✅ **Structured logging** - Detailed logs with timestamps

### `embedding_watchdog.py`

- Monitors heartbeat file and restarts processor if stale
- Can run as cron job: `*/2 * * * * python3 embedding_watchdog.py`
- Detects: stale heartbeats, dead processes, missing files

### `manage_processor.sh`

Simple management commands:
```bash
./manage_processor.sh start          # Start processor
./manage_processor.sh stop           # Stop processor
./manage_processor.sh restart        # Restart processor
./manage_processor.sh status         # Check status
./manage_processor.sh logs           # Tail logs
./manage_processor.sh stats          # Show embedding stats
./manage_processor.sh watchdog-start # Start watchdog daemon
./manage_processor.sh check          # Run health check
```

## Migration Steps

### 1. Stop the Old Processor

```bash
cd /Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta

# Stop old processor
python3 background_embedding_processor.py stop

# Or kill it manually if stuck
ps aux | grep background_embedding_processor
kill -9 <PID>
```

### 2. Verify Dependencies

```bash
# Check aiohttp is installed (required by new processor)
python3 -c "import aiohttp; print(aiohttp.__version__)"

# If not installed:
pip install aiohttp
```

### 3. Start the New Robust Processor

```bash
# Option 1: Using the management script
chmod +x manage_processor.sh
./manage_processor.sh start

# Option 2: Using nohup directly
nohup python3 embedding_processor_robust.py > /tmp/kg_rag_processor.out 2>&1 &

# Option 3: Run in screen/tmux
screen -S embeddings
python3 embedding_processor_robust.py
# Ctrl+A, D to detach
```

### 4. Check Status

```bash
./manage_processor.sh status
# or
python3 embedding_processor_robust.py --status
```

### 5. (Optional) Set Up Watchdog

For automatic restart if processor gets stuck:

```bash
# Option 1: Run watchdog daemon
./manage_processor.sh watchdog-start

# Option 2: Add to crontab (runs every 2 minutes)
crontab -e
# Add line:
*/2 * * * * cd /Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta && python3 embedding_watchdog.py >> /tmp/kg_rag_watchdog.log 2>&1
```

## Configuration

Edit `Config` class in `embedding_processor_robust.py`:

```python
@dataclass
class Config:
    BATCH_SIZE: int = 100              # Relationships per batch
    INTERVAL_SECONDS: int = 60         # Wait between batches
    MAX_RETRIES: int = 3               # Retry attempts per embedding
    HTTP_TIMEOUT: float = 30.0         # Ollama timeout
    DB_TIMEOUT: float = 30.0           # Database timeout
    HEARTBEAT_INTERVAL: int = 60       # Health check write interval
    CIRCUIT_BREAKER_THRESHOLD: int = 5  # Failures before circuit opens
    CIRCUIT_BREAKER_TIMEOUT: int = 300  # Seconds before retry after open
```

## Monitoring

### View Logs

```bash
# Processor logs
tail -f /tmp/kg_rag_processor_robust.log

# Watchdog logs
tail -f /tmp/kg_rag_watchdog.log

# Processor output
tail -f /tmp/kg_rag_processor.out
```

### Check Progress

```bash
./manage_processor.sh stats
```

### Manual Health Check

```bash
# Check heartbeat file
cat /tmp/kg_rag_processor_heartbeat

# Check if process is responsive
python3 embedding_watchdog.py
```

## Troubleshooting

### Processor Won't Start

```bash
# Check if already running
python3 embedding_processor_robust.py --status

# Check for port conflicts or DB connection issues
python3 -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/kg_rag')
    print('DB connected')
    await conn.close()
asyncio.run(test())
"
```

### Processor Stops After Starting

```bash
# Check logs for errors
tail -50 /tmp/kg_rag_processor_robust.log

# Check Ollama is running
curl http://127.0.0.1:11434/api/tags
```

### Watchdog Keeps Restarting

```bash
# Check circuit breaker status
tail -f /tmp/kg_rag_processor_robust.log | grep -i circuit

# Check Ollama health
curl -X POST http://127.0.0.1:11434/api/embed \
  -H 'Content-Type: application/json' \
  -d '{"model": "nomic-embed-text", "input": "test"}'
```

## Performance Tuning

### Increase Throughput

```python
# Config adjustments for faster processing
BATCH_SIZE: int = 200           # Larger batches (if Ollama can handle it)
INTERVAL_SECONDS: int = 30      # Less wait time between batches
```

### Reduce DB Load

```python
# Larger batches, longer intervals
BATCH_SIZE: int = 500
INTERVAL_SECONDS: int = 120
```

## Files Reference

| File | Purpose |
|------|---------|
| `embedding_processor_robust.py` | Main robust processor |
| `embedding_watchdog.py` | Health monitoring & auto-restart |
| `manage_processor.sh` | Simple management commands |
| `/tmp/kg_rag_processor_robust.log` | Structured logs |
| `/tmp/kg_rag_processor_heartbeat` | Health status JSON |
| `/tmp/kg_rag_processor_robust.pid` | Process ID file |
| `/tmp/kg_rag_watchdog.log` | Watchdog logs |

## Comparison

| Feature | Old Processor | New Robust Processor |
|---------|---------------|----------------------|
| Architecture | Fork + threading | Pure asyncio |
| Deadlock risk | High (fork+asyncio) | None |
| HTTP timeouts | ❌ None | ✅ 30s default |
| DB timeouts | ❌ None | ✅ 30s default |
| Retry logic | ❌ None | ✅ Exponential backoff |
| Circuit breaker | ❌ No | ✅ Yes |
| Health monitoring | ❌ No | ✅ Heartbeat file |
| Graceful shutdown | ⚠️ Partial | ✅ Full signal handling |
| Connection pooling | ❌ No | ✅ Yes |
| Watchdog support | ❌ No | ✅ Yes |

## Current Progress

As of last check:
- Total Relationships: 116,796
- With Embeddings: ~22,427 (19.2%)
- Target (50%): 58,398
- Remaining: ~35,971
- Current Rate: ~90-100/min
- ETA to 50%: ~6 hours
