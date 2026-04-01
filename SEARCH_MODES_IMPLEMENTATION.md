# Search Modes Implementation - v2.0-beta

## Overview

KG RAG v2.0-beta implements **four search modes** in `pgvector_api.py` using PostgreSQL + pgvector. Each mode leverages a combination of chunk embeddings, entity embeddings, and relationship embeddings to provide different search capabilities.

| Mode | Description | Embedding Types Used | Best For |
|------|-------------|---------------------|----------|
| **Smart** ⭐ (default) | Multi-layer unified search | All three (chunks + entities + relationships) | All queries |
| **Semantic** | Vector similarity on chunks | Chunk embeddings | Simple semantic queries |
| **Entity-lookup** | Entity-centric with keyword boost | All three + keywords | Entity-focused questions |
| **Graph-traversal** | Graph BFS with path finding | All three + graph reasoning | Relationship questions |

---

## Implementation Details

### 1. SMART Mode (Default) ⭐

**Function:** `search_smart()` in `pgvector_api.py`

**What it does:**
Intelligently combines ALL search strategies in 5 layers:

```python
# Layer 1: Semantic Chunk Search (Foundation)
chunk_results = await storage.search_chunks(
    query_vector=query_embedding,
    limit=top_k * 2,
    distance_metric=DistanceMetric.COSINE,
    match_threshold=0.25
)

# Layer 2: Entity Discovery
entity_results = await storage.search_entities(
    query_vector=query_embedding,
    limit=15,
    distance_metric=DistanceMetric.COSINE
)

# Layer 3: Relationship Enhancement
rel_results = await storage.search_relationships(
    query_vector=query_embedding,
    limit=20,
    distance_metric=DistanceMetric.COSINE,
    match_threshold=0.4
)

# Layer 4: Keyword Extraction & Boosting
high_level, low_level = await extract_keywords_for_search(query, llm_config)
# Apply boosts to matching chunks

# Layer 5: Entity Chunk Collection
chunks = await storage.get_chunks_by_entity(entity_id, limit=12)

# Final: Intelligent Fusion & Ranking
# Deduplicate, apply layer boosts, sort by composite score
```

**Best for:**
- General knowledge questions
- Complex queries with multiple aspects
- When you're unsure which mode to use
- Maximum recall and relevance

---

### 2. Semantic Mode

**Function:** Standard chunk search in `chat()` endpoint

**What it does:**
Direct vector search on chunks table:

```python
vector_results = await storage.search_chunks(
    query_vector=query_embedding,
    limit=initial_k,
    distance_metric=DistanceMetric.COSINE,
    match_threshold=0.2
)
```

**Best for:**
- Simple semantic queries
- When speed is priority
- Conceptual questions

---

### 3. Entity-Lookup Mode

**Function:** `search_entity_lookup()` in `pgvector_api.py`

**What it does:**
Comprehensive entity-based search using ALL embedding types:

```python
# Layer 1: Entity Embeddings - Find matching entities
entity_results = await storage.search_entities(
    query_vector=query_embedding,
    limit=top_k * 3,
    distance_metric=DistanceMetric.COSINE
)

# Layer 2: Keyword Extraction - For entity boosting
high_level, low_level = await extract_keywords_for_search(query, llm_config)
# Boost entity scores based on keyword matches

# Layer 3: Relationship Embeddings - Find related entities
rel_embedding_results = await storage.search_relationships(
    query_vector=query_embedding,
    limit=15,
    distance_metric=DistanceMetric.COSINE,
    match_threshold=0.5
)

# Layer 4: Chunk Embeddings - Multiple strategies
# 4a: Direct chunk vector search
chunk_results = await storage.search_chunks(...)
# 4b: Chunks from entity-based search
chunks = await storage.get_chunks_by_entity(entity_id, limit=15)

# Layer 5: Relationship Content - Add relationship descriptions
```

**Best for:**
- Specific entity-focused questions
- Questions about companies, people, products
- When entity relationships matter

---

### 4. Graph-Traversal Mode

**Function:** `search_graph_traversal()` in `pgvector_api.py`

**What it does:**
Comprehensive graph-based search with path finding:

```python
# Layer 1: Relationship Embeddings - Primary relationship-based retrieval
rel_results = await storage.search_relationships(
    query_vector=query_embedding,
    limit=20,
    distance_metric=DistanceMetric.COSINE,
    match_threshold=0.4
)

# Layer 2: Entity Embeddings - Find seed entities for graph expansion
seed_entities = await storage.search_entities(
    query_vector=query_embedding,
    limit=15,
    distance_metric=DistanceMetric.COSINE
)

# Layer 3: Graph Traversal - BFS with path finding
related = await storage.get_related_entities(
    entity_id=seed_id,
    max_depth=max_depth,  # 2-hop
    limit_per_level=12
)
# Track: entity_depths, entity_paths, entity_connection_scores

# Layer 4: Chunk Embeddings - Multiple retrieval strategies
# 4a: Direct chunk vector search
chunk_results = await storage.search_chunks(...)
# 4b: Chunks from all discovered entities with depth scoring

# Layer 5: Graph Reasoning - Hub detection and connectivity analysis
# Add high-centrality entity summaries
```

**Best for:**
- Overview questions
- Relationship-focused queries
- Questions about connections between entities
- Industry landscape questions

---

## API Usage

### Request Format

```json
{
  "message": "What is Apple's relationship with Samsung?",
  "mode": "smart",              // "smart" (default), "semantic", "entity-lookup", "graph-traversal"
  "top_k": 20,
  "max_depth": 2,               // for graph-traversal mode
  "rerank": true,
  "rerank_method": "semantic",
  "llm_config": {
    "provider": "deepseek",
    "fallback_provider": "minimax"
  }
}
```

### Mode Mapping

| WebUI Display | API Mode Value | Description |
|--------------|----------------|-------------|
| Smart ⭐ | `smart` | Multi-layer unified search (RECOMMENDED) |
| Semantic | `semantic` / `semantic-hybrid` | Vector search on chunks |
| Entity-lookup | `entity-lookup` | Entity-centric with keyword boost |
| Graph-traversal | `graph-traversal` | Graph BFS with path finding |

### Testing

```bash
# Smart mode (RECOMMENDED - default)
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the economic benefits of AI?", "mode": "smart"}'

# Semantic mode
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is machine learning?", "mode": "semantic"}'

# Entity-lookup mode
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What products does Apple make?", "mode": "entity-lookup"}'

# Graph-traversal mode
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do tech companies compete?", "mode": "graph-traversal", "max_depth": 2}'

# Query+File with any mode
curl -X POST http://localhost:8002/api/v1/chat/with-doc \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain the supply chain",
    "filenames": ["report.pdf"],
    "mode": "smart"
  }'
```

---

## Performance Comparison

| Mode | Speed | Typical Results | Use Case |
|------|-------|-----------------|----------|
| Smart | ~2-3s | 40-60 chunks | Default, maximum coverage |
| Semantic | ~1s | 35-45 chunks | Simple, fast queries |
| Entity-lookup | ~1.5-2s | 35-50 chunks | Entity-focused questions |
| Graph-traversal | ~2-4s | 40-60 chunks | Complex relationship queries |

---

## Embedding Usage Summary

| Embedding Type | Smart | Semantic | Entity-Lookup | Graph-Traversal |
|----------------|-------|----------|---------------|-----------------|
| **Chunk Embeddings** | ✅ Primary | ✅ Only | ✅ Yes | ✅ Yes |
| **Entity Embeddings** | ✅ Discovery | ❌ No | ✅ Primary | ✅ Seeds |
| **Relationship Embeddings** | ✅ Enhancement | ❌ No | ✅ Enhancement | ✅ Primary |
| **Keyword Extraction** | ✅ Boosting | ❌ No | ✅ Boosting | ❌ No |
| **Graph Traversal** | ✅ 1-hop | ❌ No | ✅ 1-hop | ✅ 2-hop |
| **Path Tracking** | ❌ No | ❌ No | ❌ No | ✅ Yes |

---

## Files Modified

1. **`backend/pgvector_api.py`** - Main implementation:
   - Added `search_smart()` - Multi-layer unified search
   - Added `search_entity_lookup()` - Entity-centric search
   - Added `search_graph_traversal()` - Graph-based search
   - Added `extract_keywords_for_search()` - Keyword extraction
   - Updated `chat()` endpoint - Mode routing
   - Updated `chat_with_doc()` endpoint - Mode routing

2. **`backend/storage.py`** - Storage layer (already existed):
   - `search_chunks()` - Chunk vector search
   - `search_entities()` - Entity vector search
   - `search_relationships()` - Relationship vector search
   - `get_related_entities()` - Graph traversal
   - `get_chunks_by_entity()` - Entity chunk retrieval

---

## Database Requirements

### Required Embeddings

| Table | Embedding Column | Status |
|-------|------------------|--------|
| `chunks` | `embedding` (768-dim) | ✅ Always populated on upload |
| `entities` | `embedding` (768-dim) | ✅ Populated on new uploads, backfill for existing |
| `relationships` | `embedding` (768-dim) | 🟡 Background processor filling |

### Background Processors

```bash
# Relationship embedding processor (already running)
python3 embedding_processor_robust.py

# Entity embedding backfill (start after relationships complete)
python3 backfill_entity_embeddings_robust.py --wait-for-relationships
```

---

## Notes

- **Backward Compatible**: Default mode is "smart" but all old modes work
- **No Data Loss**: All changes are additive
- **Graceful Fallback**: If a mode fails, falls back to semantic search
- **Embedding Independence**: Modes work even if some embeddings are missing (with reduced quality)
- **Unified Architecture**: All modes benefit from the same storage layer functions
