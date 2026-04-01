# Relationship Embeddings in KG RAG

## Overview

Relationship embeddings enable semantic search over the knowledge graph's relationships, powering the **Graph-traversal** search mode. This document explains the 3-phase embedding strategy and how to manage it.

## Why Relationship Embeddings?

Without embeddings, relationship search relies only on:
- Exact keyword matching
- Graph traversal via entity connections

With embeddings, you get:
- **Semantic matching**: "innovation" matches "technology advancement"
- **Better Graph-traversal mode**: Direct relationship vector search
- **Improved relevance**: Embeddings capture relationship meaning

## 3-Phase Embedding Strategy

### Phase 1: Upload-Time Generation ⬆️
**When**: Every time a file is uploaded
**What**: Generate embeddings immediately for new relationships

**Implementation**:
```python
# In upload_document_json() and process_single_file()
if embedding_service:
    await embedding_service.create_relationship_with_embedding(
        relationship_id=f"{from_id}_{to_id}",
        source_id=from_id,
        target_id=to_id,
        relationship_type=rel_type,
        properties={...},
        storage=storage
    )
```

**Benefits**:
- ✅ New relationships always have embeddings
- ✅ No backfill needed for new data
- ✅ Transparent to users

---

### Phase 2: Lazy/On-Demand Generation 🔄
**When**: When relationships are queried but lack embeddings
**What**: Generate embedding on-the-fly and cache it

**Implementation**:
```python
# In lazy_generate_relationship_embeddings()
embedding = await embedding_service.ensure_embedding(
    relationship_id=rel_id,
    storage=storage
)
```

**Usage**:
```bash
# Pre-generate embeddings for specific relationships
curl -X POST http://localhost:8002/api/v1/admin/relationship-embeddings/ensure \
  -H "Content-Type: application/json" \
  -d '{"relationship_ids": ["rel_123", "rel_456"]}'
```

**Benefits**:
- ✅ Relationships get embeddings when needed
- ✅ No wasted computation on unused relationships
- ✅ Automatically caches for future use

---

### Phase 3: Batch Backfill 🚀
**When**: Background processing or manual migration
**What**: Generate embeddings for all existing relationships without them

**Implementation**:
```python
# In batch_generate_embeddings()
result = await embedding_service.batch_generate_embeddings(
    limit=100,
    storage=storage
)
```

**Usage**:
```bash
# Check status
python backend/manage_embeddings.py status

# Generate batch of 100
python backend/manage_embeddings.py generate --limit 100

# Start background processor
python backend/manage_embeddings.py background --start --interval 60

# Run full migration
python backend/manage_embeddings.py full-migration --batch-size 50

# Run test migration (500 relationships)
python backend/manage_embeddings.py full-migration --batch-size 50 --max-total 500
```

**Benefits**:
- ✅ Processes existing data in background
- ✅ Configurable batch sizes
- ✅ Resumable and idempotent

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Upload Pipeline                          │
│  File → Extract Text → Entities/Relations → Phase 1 Embed   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   PostgreSQL Database                       │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────┐   │
│  │  entities   │  │  relationships   │  │    chunks    │   │
│  │             │  │  - embedding     │  │              │   │
│  │             │  │  - description   │  │              │   │
│  │             │  │  - keywords      │  │              │   │
│  └─────────────┘  └──────────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌─────────────────┐    ┌──────────────┐
│  Phase 2      │    │   Phase 3       │    │   Search     │
│  Lazy Gen     │    │   Batch Backfill│    │   Usage      │
│               │    │                 │    │              │
│ On query:     │    │ Background:     │    │ Vector sim   │
│ Check → Gen   │    │ Process batches │    │ on embed     │
│ → Store       │    │ → Store         │    │ → Results    │
└───────────────┘    └─────────────────┘    └──────────────┘
```

---

## API Endpoints

### Get Status
```http
GET /api/v1/admin/relationship-embeddings/status
```

Response:
```json
{
  "success": true,
  "database": {
    "total_relationships": 116550,
    "with_embeddings": 5234,
    "without_embeddings": 111316,
    "percentage_complete": 4.49,
    "status": "in_progress"
  },
  "service": {
    "generated": 234,
    "failed": 12,
    "cache_size": 150
  },
  "background_processor_running": false
}
```

### Generate Batch
```http
POST /api/v1/admin/relationship-embeddings/generate
Content-Type: application/json

{
  "limit": 100,
  "relationship_ids": ["rel_1", "rel_2"]  // optional, specific IDs
}
```

### Start Background Processor
```http
POST /api/v1/admin/relationship-embeddings/background/start
Content-Type: application/json

{
  "interval_seconds": 60
}
```

### Stop Background Processor
```http
POST /api/v1/admin/relationship-embeddings/background/stop
```

### Ensure Specific Embeddings (Lazy)
```http
POST /api/v1/admin/relationship-embeddings/ensure
Content-Type: application/json

{
  "relationship_ids": ["rel_123", "rel_456"]
}
```

---

## Management Script

The `manage_embeddings.py` script provides a convenient CLI:

```bash
# Check status
python backend/manage_embeddings.py status

# Generate 100 embeddings
python backend/manage_embeddings.py generate --limit 100

# Start background processor
python backend/manage_embeddings.py background --start --interval 60

# Stop background processor
python backend/manage_embeddings.py background --stop

# Full migration
python backend/manage_embeddings.py full-migration --batch-size 50

# Test migration (500 relationships)
python backend/manage_embeddings.py full-migration --batch-size 50 --max-total 500
```

---

## Configuration

### Embedding Model
Currently uses Ollama with `nomic-embed-text` (768 dimensions):

```python
# In pgvector_api.py
EMBEDDING_DIMENSION = 768

def get_ollama_embedding(text: str) -> List[float]:
    # Uses ThreadPoolExecutor for async compatibility
    # 30 second timeout per embedding
    # Returns zero vector on failure
```

### Batch Processing
```python
# Default settings in RelationshipEmbeddingService
batch_size = 50          # Relationships per batch
max_concurrent = 5       # Concurrent generations
interval_seconds = 60    # Background processor interval
cache_max_size = 1000    # In-memory embedding cache
```

---

## Performance Considerations

### Time Estimates
- **Per embedding**: ~50-100ms (local Ollama)
- **Batch of 50**: ~3-5 seconds
- **116K relationships**: ~2-3 hours (full migration)

### Resource Usage
- **CPU**: Moderate (embedding generation)
- **Memory**: Low (caching ~1000 embeddings = ~3MB)
- **Database**: Minimal (single UPDATE per relationship)

### Optimization Tips
1. **Use background processor** for gradual backfill
2. **Start with test migration** (500 relationships) to estimate time
3. **Monitor with status endpoint** to track progress
4. **Adjust batch size** based on your Ollama performance

---

## Fallback Behavior

If embedding generation fails:

1. **Upload**: Relationship created without embedding (will be generated later via Phase 2 or 3)
2. **Search**: Falls back to keyword-only matching
3. **Lazy generation**: Retries on next query
4. **Batch backfill**: Continues with next batch

The system is resilient - missing embeddings don't break functionality, they just reduce semantic search quality.

---

## Migration Guide

### For New Installations
Nothing needed - Phase 1 handles all new uploads automatically.

### For Existing Databases

**Option A: Gradual (Recommended)**
```bash
# Start background processor and let it run
python backend/manage_embeddings.py background --start --interval 60

# Check progress periodically
python backend/manage_embeddings.py status
```

**Option B: Immediate (Faster but resource-intensive)**
```bash
# Run full migration in one go
python backend/manage_embeddings.py full-migration --batch-size 100
```

**Option C: Test First**
```bash
# Process 500 relationships to estimate time
python backend/manage_embeddings.py full-migration --batch-size 50 --max-total 500
```

---

## Troubleshooting

### No embeddings being generated
Check Ollama is running:
```bash
curl http://localhost:11434/api/tags
```

### Slow generation
- Reduce batch size: `--batch-size 25`
- Check Ollama GPU acceleration
- Consider running during off-peak hours

### High failure rate
Check logs in pgvector_api.py output. Common issues:
- Ollama timeout (increase timeout or reduce batch size)
- Database connection issues
- Memory constraints

### Background processor not running
```bash
# Check status
python backend/manage_embeddings.py status

# Restart if needed
python backend/manage_embeddings.py background --stop
python backend/manage_embeddings.py background --start
```

---

## Future Improvements

- [ ] **Parallel Ollama requests**: Use multiple Ollama instances
- [ ] **Priority queue**: Prioritize relationships from recent queries
- [ ] **Incremental updates**: Regenerate embeddings when relationships change
- [ ] **Alternative models**: Support for OpenAI, Cohere embeddings
- [ ] **Compression**: Quantize embeddings to reduce storage

---

## Summary

| Phase | When | Method | Use Case |
|-------|------|--------|----------|
| **1** | Upload | Immediate | All new relationships |
| **2** | Query | On-demand | Hot relationships |
| **3** | Background | Batch | Cold relationships |

The 3-phase strategy ensures:
- ✅ **New data** always has embeddings
- ✅ **Hot data** gets embeddings when needed
- ✅ **Cold data** is processed efficiently in background
- ✅ **Zero downtime** during migration
- ✅ **Graceful degradation** if generation fails
