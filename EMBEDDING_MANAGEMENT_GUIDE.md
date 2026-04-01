# Embedding Management Guide for KG RAG v2.0-beta

## Current Status (as of check)

| Component | Total | With Embeddings | Percentage | Status |
|-----------|-------|-----------------|------------|--------|
| **Relationships** | 116,796 | 69,327 | **59.36%** | 🟢 Processing (PID 52800) |
| **Entities** | 46,012 | 0 | **0.00%** | 🔴 Waiting |
| **Text Chunks** | ~250,000 | ~250,000 | **100%** | ✅ Complete |

## New Scripts Created

### 1. `backfill_entity_embeddings_robust.py`
Generates embeddings for all entities without them (robust version with circuit breaker, health monitoring, etc.).

**Features:**
- Pure asyncio (no threading issues)
- Circuit breaker for Ollama failures
- Automatic retry with exponential backoff
- Health check heartbeat file
- Graceful shutdown handling
- Connection pooling for PostgreSQL
- Batched processing (default: 100 entities/batch)
- Progress tracking with ETA
- Resume capability (won't re-process)
- Can wait for relationships to complete first

**Usage:**
```bash
# Check status
python3 backfill_entity_embeddings_robust.py --status

# Run (will continue until all entities have embeddings)
python3 backfill_entity_embeddings_robust.py

# Wait for relationships to finish, then start
python3 backfill_entity_embeddings_robust.py --wait-for-relationships

# Custom batch size
python3 backfill_entity_embeddings_robust.py --batch-size 200

# Run as background daemon
nohup python3 backfill_entity_embeddings_robust.py > entity_processor.log 2>&1 &

# Stop gracefully
python3 backfill_entity_embeddings_robust.py --stop
```

### 2. `manage_embeddings.py` (Unified Manager)
Manages both relationship and entity embedding processes.

**Usage:**
```bash
# Show overall status
python3 manage_embeddings.py status

# Relationship embeddings
python3 manage_embeddings.py relationships status
python3 manage_embeddings.py relationships start
python3 manage_embeddings.py relationships stop
python3 manage_embeddings.py relationships restart

# Entity embeddings
python3 manage_embeddings.py entities status
python3 manage_embeddings.py entities start        # Start now
python3 manage_embeddings.py entities start --wait # Wait for relationships
python3 manage_embeddings.py entities stop
python3 manage_embeddings.py entities single       # One batch

# Start everything (sequential)
python3 manage_embeddings.py start-all
```

## Recommended Workflow

### Option 1: Wait for Relationships, Then Entities (Recommended)

```bash
# 1. Let relationship processor continue (it's at 59%)
# PID 52800 is already running

# 2. Monitor relationship progress
watch -n 60 'python3 manage_embeddings.py status'

# 3. When relationships reach ~99%, start entity backfill
python3 manage_embeddings.py entities start --wait

# This will:
# - Wait for relationship embeddings to complete
# - Automatically start entity backfill
# - Run continuously until all entities have embeddings
```

### Option 2: Start Entity Backfill Now (Parallel)

If you want to start entity backfill immediately (parallel with relationships):

```bash
# Start entity backfill now (independent of relationships)
python3 backfill_entity_embeddings.py --continuous

# Monitor both processes
python3 manage_embeddings.py status
```

**Note:** Running both processes in parallel will share Ollama resources, which may slow down both processes.

### Option 3: Sequential with Unified Manager

```bash
# Start relationship processor, then automatically start entities when done
python3 manage_embeddings.py start-all

# This will:
# 1. Start relationship processor (if not running)
# 2. Wait for it to reach ~99% complete
# 3. Start entity backfill automatically
```

## Estimated Completion Times

### Relationship Embeddings
- **Current:** 69,327 / 116,796 (59.36%)
- **Remaining:** 47,469 embeddings
- **Rate:** ~800/minute
- **ETA:** ~60 minutes

### Entity Embeddings
- **Total:** 46,012 entities
- **Rate:** ~800/minute (estimated)
- **ETA:** ~58 minutes

### Total Time Remaining
- **Relationships:** ~60 minutes
- **Entities:** ~58 minutes
- **Sequential Total:** ~2 hours
- **Parallel Total:** ~1 hour (if run together)

## Monitoring

### Watch Both Processes
```bash
# Auto-refresh every 60 seconds
watch -n 60 'python3 manage_embeddings.py status'
```

### View Logs
```bash
# Relationship processor
tail -f /tmp/kg_rag_processor_robust.log

# Entity processor
tail -f /tmp/kg_rag_entity_processor_robust.log
tail -f /tmp/entity_processor.log
```

### Check Individual Status
```bash
# Relationship processor
python3 embedding_processor_robust.py --status

# Entity backfill
python3 backfill_entity_embeddings.py --status
```

## Safety Features

### Resume Capability
Both scripts track progress and won't re-process items that already have embeddings:
- Relationship processor queries `WHERE embedding IS NULL`
- Entity processor queries `WHERE embedding IS NULL`

### PID File Management
Prevents multiple instances:
- `/tmp/kg_rag_processor_robust.pid` (relationships)
- `/tmp/kg_rag_entity_processor_robust.pid` (entities)

### Circuit Breaker
Protects against cascading failures:
- Opens after 5 consecutive Ollama failures
- Prevents hammering the Ollama service
- Auto-recovery after 5 minutes

### Health Monitoring
Both processors write heartbeat files:
- `/tmp/kg_rag_processor_heartbeat` (relationships)
- `/tmp/kg_rag_entity_processor_heartbeat` (entities)

### Graceful Shutdown
Send SIGTERM (Ctrl+C or kill) for clean shutdown:
```bash
# Stop relationship processor
python3 embedding_processor_robust.py --stop

# Stop entity processor
python3 backfill_entity_embeddings_robust.py --stop

# Or use unified manager
python3 manage_embeddings.py relationships stop
python3 manage_embeddings.py entities stop
```

## Embedding Text Formats

### Entities
```
"{name} ({entity_type}) - {description}"

Example:
"Apple Inc. (company) - Technology company founded in 1976"
```

### Relationships
```
"{source_id} {relationship_type} {target_id}"

Example:
"Apple Inc. founded_by Steve Jobs"
```

### Text Chunks
```
Raw chunk content (first 8000 characters)
```

## Troubleshooting

### Ollama Not Responding
```bash
# Check Ollama status
curl http://127.0.0.1:11434/api/tags

# Restart Ollama if needed
killall ollama
ollama serve
```

### Database Connection Issues
```bash
# Test connection
python3 -c "import asyncpg; asyncio.run(asyncpg.connect('postgresql://postgres:postgres@localhost:5432/kg_rag'))"

# Check PostgreSQL
docker-compose ps
```

### Process Stuck
```bash
# Check if process is responsive
ps aux | grep embedding

# Kill and restart
kill -9 <PID>
python3 manage_embeddings.py relationships restart
```

## Completion Checklist

When both processes complete, you should see:

```
📊 Relationship Embeddings:
   Process Status: 🔴 STOPPED
   With Embeddings: 116,796 / 116,796 (100.00%)

📊 Entity Embeddings:
   Process Status: 🔴 STOPPED
   With Embeddings: 46,012 / 46,012 (100.00%)
```

All quantities will then have embeddings:
- ✅ Text Chunks: 100%
- ✅ Relationships: 100%
- ✅ Entities: 100%

## Summary

You now have **three options** for completing the embeddings:

1. **Wait & Start** (Recommended): Let relationships finish (~60 min), then start entities
2. **Parallel**: Start entities now, run both simultaneously (~60 min total)
3. **Unified**: Use `manage_embeddings.py start-all` for hands-off operation

Choose based on your preference for:
- **Speed**: Option 2 (parallel) is fastest
- **Simplicity**: Option 3 (unified manager)
- **Resource Management**: Option 1 (sequential, less Ollama contention)

## Robust Features Comparison

| Feature | Relationship Processor | Entity Processor (NEW) |
|---------|----------------------|----------------------|
| Pure asyncio | ✅ | ✅ |
| Circuit breaker | ✅ | ✅ |
| Retry with backoff | ✅ | ✅ |
| Health heartbeat | ✅ | ✅ |
| Graceful shutdown | ✅ | ✅ |
| Connection pooling | ✅ | ✅ |
| Structured logging | ✅ | ✅ |
| PID file management | ✅ | ✅ |
| Resume capability | ✅ | ✅ |
