# KG RAG Search Modes: Complete Summary

## Overview

KG RAG v2.0-beta provides **four implemented search modes**, all leveraging **three embedding types** (chunk, entity, relationship) to provide comprehensive search capabilities.

---

## Search Mode Comparison

| Mode | Backend Name | Primary Strategy | Embedding Types | Best For |
|------|-------------|------------------|-----------------|----------|
| **Smart** ⭐ | `smart` | Multi-layer unified | All three | All queries (Recommended) |
| **Semantic** | `semantic` / `semantic-hybrid` | Vector similarity | Chunk only | Simple queries |
| **Entity-Lookup** | `entity-lookup` | Entity-centric + keywords | All three | Entity-focused queries |
| **Graph-Traversal** | `graph-traversal` | Graph BFS + reasoning | All three | Relationship queries |

---

## Detailed Mode Descriptions

### 1. SMART Mode (Recommended) ⭐

**Backend Mode:** `smart`  
**Default:** Yes  
**Complexity:** High (automated)

**What it does:**
Intelligently combines ALL search strategies in 5 layers:

```
Layer 1: Semantic Chunk Search (Foundation)
    └── Direct vector search on chunks

Layer 2: Entity Discovery
    └── Entity embedding search → find relevant entities

Layer 3: Relationship Enhancement
    ├── Relationship embedding search
    ├── Extract entities from matching relationships
    └── Graph traversal from discovered entities

Layer 4: Keyword Boosting
    └── Extract HL/LL keywords → boost matching chunks

Layer 5: Entity Chunk Collection
    └── Get chunks from all discovered entities

Final: Intelligent Fusion
    ├── Deduplicate across all sources
    ├── Apply layer-specific boosting
    └── Rank by composite similarity score
```

**Best for:**
- General knowledge questions
- Complex queries with multiple aspects
- When you're unsure which mode to use
- Maximum recall and relevance

**Example Queries:**
- "What are the economic benefits of renewable energy in developing countries?"
- "How do tech companies approach AI ethics?"
- "Explain the relationship between blockchain and supply chain management"

**Performance:**
- Typical results: 40-60 chunks
- Latency: ~2-3 seconds
- Coverage: Highest (combines all sources)

---

### 2. SEMANTIC Mode

**Backend Mode:** `semantic` / `semantic-hybrid`  
**WebUI Button:** Semantic  
**Complexity:** Low

**What it does:**
Direct vector similarity search on chunks:

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

**Example Queries:**
- "How does machine learning work?"
- "What is blockchain technology?"
- "Explain quantum computing principles"

**Performance:**
- Typical results: 35-45 chunks
- Latency: ~1 second
- Coverage: Good (chunks only)

---

### 3. ENTITY-LOOKUP Mode

**Backend Mode:** `entity-lookup`  
**Complexity:** Medium

**What it does:**
Comprehensive entity-based search using ALL embedding types:

```
Query ─┬─► Entity Embeddings ─► Find Entities ─┬─► Keyword Boost ─┐
       │                                       │                  │
       ├─► Relationship Embeddings ─► Find Related Entities ◄────┤
       │                                                          │
       ├─► Chunk Embeddings ─► Direct Semantic Search ─┬─► Collect Chunks
       │                                                │
       └───────────────────────────────────────────────┘
                            │
                            ▼
                    Deduplicate & Rank ─► Return Top K
```

**Layers:**
1. **Entity Embeddings** - Primary search to find matching entities
2. **Keyword Extraction** - Extract and match HL/LL keywords for boosting
3. **Relationship Embeddings** - Find related entities via vector search + graph
4. **Chunk Embeddings** - Direct semantic search + entity-linked chunks
5. **Relationship Content** - Add relationship descriptions as context

**Best for:**
- Specific entity-focused questions
- Questions about companies, people, products
- When entity relationships matter

**Example Queries:**
- "What products does Tesla manufacture?"
- "Who is the CEO of Microsoft?"
- "What are Apple's main suppliers?"

**Performance:**
- Typical results: 35-50 chunks
- Latency: ~1.5-2 seconds
- Coverage: Good (entity focus + relationship expansion)

---

### 4. GRAPH-TRAVERSAL Mode

**Backend Mode:** `graph-traversal`  
**Complexity:** High

**What it does:**
Comprehensive graph-based search with path finding:

```
Query ─┬─► Relationship Embeddings ─► Find Matching Relationships ─┐
       │                            (Primary mechanism)           │
       ├─► Entity Embeddings ─► Seed Entities ─┬─► Graph BFS ─────┤
       │                                       │    (2-hop)       │
       │                                       ▼                  │
       │                              Traverse & Track Paths     │
       │                                       │                  │
       ├─► Chunk Embeddings ─► Direct Search ◄─┘                  │
       │                                                          │
       └─► Collect All Chunks ─► Graph Reasoning (Hub Detection) ─┘
                                          │
                                          ▼
                              Deduplicate & Rank ─► Return Top K
```

**Layers:**
1. **Relationship Embeddings** - **PRIMARY** mechanism for relationship-based retrieval
2. **Entity Embeddings** - Find seed entities for graph expansion
3. **Graph Traversal** - 2-hop BFS with path tracking and depth scoring
4. **Chunk Embeddings** - Direct search + graph-entity chunks
5. **Graph Reasoning** - Hub detection, centrality scoring, connectivity analysis

**Key Features:**
- Uses Recursive CTE for graph traversal
- Parallel relationship embedding search
- Full path reconstruction
- Depth-based scoring (closer = higher score)
- Hub entity detection and boosting

**Best for:**
- Overview questions
- Relationship-focused queries
- Questions about connections between entities
- Industry landscape questions

**Example Queries:**
- "How do tech companies compete in the AI space?"
- "What partnerships exist in the EV industry?"
- "Show me the competitive landscape for cloud providers"
- "How are companies connected in the semiconductor supply chain?"

**Performance:**
- Typical results: 40-60 chunks
- Latency: ~2-4 seconds
- Coverage: Highest for relationship queries

---

## Embedding Usage Matrix

| Embedding Type | Smart | Semantic | Entity-Lookup | Graph-Traversal |
|----------------|-------|----------|---------------|-----------------|
| **Chunk Embeddings** | ✅ Primary | ✅ Only | ✅ Yes | ✅ Yes |
| **Entity Embeddings** | ✅ Discovery | ❌ No | ✅ Primary | ✅ Seeds |
| **Relationship Embeddings** | ✅ Enhancement | ❌ No | ✅ Enhancement | ✅ Primary |
| **Keyword Extraction** | ✅ Boosting | ❌ No | ✅ Boosting | ❌ No |
| **Graph Traversal** | ✅ 1-hop | ❌ No | ✅ 1-hop | ✅ 2-hop |
| **Path Tracking** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Graph Reasoning** | ❌ No | ❌ No | ❌ No | ✅ Yes |

---

## Usage Guide

### Quick Selection Guide

| Your Question Type | Recommended Mode |
|-------------------|------------------|
| "What is X?" / "How does Y work?" | **Smart** or Semantic |
| "Tell me about Company X" | **Smart** or Entity-lookup |
| "How do X and Y relate?" | **Smart** or Graph-traversal |
| "What partnerships exist?" | **Smart** or Graph-traversal |
| "What are the benefits of X?" | **Smart** or Semantic |
| Quick/simple lookup | Semantic |
| Deep entity analysis | Entity-lookup |
| Industry overview | Graph-traversal |

### API Usage Examples

```bash
# Smart mode (RECOMMENDED - default)
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the benefits of AI?", "mode": "smart"}'

# Semantic mode (simple vector search)
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How does blockchain work?", "mode": "semantic"}'

# Entity-lookup mode
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What products does Tesla make?", "mode": "entity-lookup"}'

# Graph-traversal mode
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do companies compete in AI?", "mode": "graph-traversal", "max_depth": 2}'

# Query+File with any mode
curl -X POST http://localhost:8002/api/v1/chat/with-doc \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain the supply chain",
    "filenames": ["report.pdf"],
    "mode": "smart"
  }'
```

### WebUI Usage

The WebUI provides 4 buttons:

1. **Smart** ⭐ (default) - Best for most queries
2. **Semantic** - Simple semantic search
3. **Entity-lookup** - Entity-focused search
4. **Graph-traversal** - Relationship exploration

---

## Technical Implementation

### Backend Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Search Mode Router                         │
│  Query → Mode Selection (smart/semantic/entity-lookup/graph)    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────────┐   ┌───────────────────┐
│     Smart     │   │  Entity-Lookup    │   │  Graph-Traversal  │
│  (5 layers)   │   │    (5 layers)     │   │    (5 layers)     │
└───────┬───────┘   └─────────┬─────────┘   └─────────┬─────────┘
        │                     │                       │
        └─────────────────────┼───────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Unified Storage Layer (storage.py)                 │
│                                                                   │
│  • search_chunks()       - Chunk vector search                   │
│  • search_entities()     - Entity vector search                  │
│  • search_relationships() - Relationship vector search           │
│  • get_related_entities() - Graph traversal                      │
│  • get_chunks_by_entity() - Entity chunk retrieval               │
└─────────────────────────────────────────────────────────────────┘
```

### Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `search_smart()` | `pgvector_api.py` | Smart mode - 5-layer unified search |
| `search_entity_lookup()` | `pgvector_api.py` | Entity-lookup mode - entity-centric |
| `search_graph_traversal()` | `pgvector_api.py` | Graph mode - traversal + reasoning |
| `extract_keywords_for_search()` | `pgvector_api.py` | Keyword extraction for boosting |
| `search_chunks()` | `storage.py` | Chunk vector search |
| `search_entities()` | `storage.py` | Entity vector search |
| `search_relationships()` | `storage.py` | Relationship vector search |
| `get_related_entities()` | `storage.py` | Graph traversal using recursive CTE |
| `get_chunks_by_entity()` | `storage.py` | Get chunks by entity ID |

---

## Current Status

### Embedding Status

| Table | Total | With Embeddings | Percentage |
|-------|-------|-----------------|------------|
| Chunks | ~165,000 | ~165,000 | ✅ 100% |
| Entities | 46,012 | ~46,012* | 🟡 Being backfilled |
| Relationships | 116,796 | ~72,000 | 🟡 ~62% (background processing) |

\* New uploads have embeddings; existing being backfilled

### Background Processors

```bash
# Check relationship processor status
python3 embedding_processor_robust.py --status

# Start entity backfill (when relationships complete)
python3 backfill_entity_embeddings_robust.py --wait-for-relationships
```

---

## Performance Summary

| Mode | Typical Results | Latency | Coverage | Use Case |
|------|----------------|---------|----------|----------|
| Smart | 40-60 chunks | ~2-3s | All embeddings | Default, all queries |
| Semantic | 35-45 chunks | ~1s | Chunks only | Simple queries |
| Entity-lookup | 35-50 chunks | ~1.5-2s | All embeddings | Entity questions |
| Graph-traversal | 40-60 chunks | ~2-4s | All embeddings | Relationship questions |

---

## Recommendations

### For Users
1. **Use Smart mode by default** - It automatically combines the best strategies
2. **Use Semantic for quick answers** - Fastest, good for simple questions
3. **Use Entity-lookup for specific entities** - Better entity focus with keywords
4. **Use Graph-traversal for relationships** - Best for "how do X and Y relate"

### For Developers
1. **Smart mode has the best coverage** - Use for maximum recall
2. **All modes use unified storage functions** - Consistent interface
3. **Graceful degradation** - Works even if some embeddings are missing
4. **Easy to extend** - Add new layers to existing modes

---

## Summary

KG RAG provides a **unified search architecture** where:

- **4 modes** cover all search use cases
- **All specialized modes** use all three embedding types
- **Smart mode** automatically combines the best strategies
- **Background processors** continue enhancing embedding coverage
- **Both chat endpoints** (`/chat` and `/chat/with-doc`) support all modes

**The recommended approach:** Use **Smart mode** for all queries unless you have a specific reason to use another mode.
