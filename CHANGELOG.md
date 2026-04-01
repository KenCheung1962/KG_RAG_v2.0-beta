# KG RAG v2.0-beta Changelog

## Overview

This document tracks all major changes and additions to KG RAG v2.0-beta, including new search modes, embedding implementations, and API updates.

---

## Recent Changes (April 2026)

### 🎯 Search Modes Implementation

#### 1. Smart Mode (NEW) ⭐
- **File:** `backend/pgvector_api.py`
- **Function:** `search_smart()`
- **Description:** Multi-layer unified search combining all embedding types
- **Layers:**
  1. Semantic chunk search (foundation)
  2. Entity discovery (entity embeddings)
  3. Relationship enhancement (relationship embeddings)
  4. Keyword boosting (keyword extraction)
  5. Entity chunk collection
  6. Intelligent fusion & ranking
- **Default:** Yes (recommended for all queries)
- **API:** `POST /api/v1/chat` with `"mode": "smart"`

#### 2. Entity-Lookup Mode (ENHANCED)
- **File:** `backend/pgvector_api.py`
- **Function:** `search_entity_lookup()`
- **Description:** Comprehensive entity-based search using ALL embedding types
- **Features:**
  - Entity embedding search (primary)
  - Keyword extraction and boosting (HL + LL keywords)
  - Relationship embedding search for related entities
  - Chunk embedding search (direct + entity-linked)
  - Relationship content as context
- **API:** `POST /api/v1/chat` with `"mode": "entity-lookup"`

#### 3. Graph-Traversal Mode (ENHANCED)
- **File:** `backend/pgvector_api.py`
- **Function:** `search_graph_traversal()`
- **Description:** Comprehensive graph-based search with path finding
- **Features:**
  - Relationship embeddings as PRIMARY mechanism
  - Entity embeddings for seed finding
  - 2-hop BFS graph traversal
  - Full path tracking and reconstruction
  - Depth-based scoring
  - Graph reasoning (hub detection, centrality analysis)
  - Chunk embeddings (direct + graph-entity)
- **API:** `POST /api/v1/chat` with `"mode": "graph-traversal"`, `"max_depth": 2`

#### 4. Semantic Mode (EXISTING)
- **File:** `backend/pgvector_api.py` (in `chat()` endpoint)
- **Description:** Direct vector search on chunks
- **Features:** Simple, fast chunk embedding search
- **API:** `POST /api/v1/chat` with `"mode": "semantic"` (or default)

### 🔧 Supporting Functions

#### Keyword Extraction
- **File:** `backend/pgvector_api.py`
- **Function:** `extract_keywords_for_search()`
- **Description:** Regex-based keyword extraction for search enhancement
- **Output:** High-level keywords (concepts), Low-level keywords (entities)
- **Used in:** Entity-lookup mode, Smart mode

### 📡 API Updates

#### Chat Endpoint
- **Endpoint:** `POST /api/v1/chat`
- **Modes Supported:** `smart` (default), `semantic`, `entity-lookup`, `graph-traversal`
- **New Parameters:**
  - `mode`: Search mode selection
  - `max_depth`: For graph-traversal mode (default: 2)

#### Query+File Endpoint
- **Endpoint:** `POST /api/v1/chat/with-doc`
- **Modes Supported:** All four modes
- **New Parameters:**
  - `mode`: Search mode selection
  - `max_depth`: For graph-traversal mode

### 📊 Embedding Usage

| Mode | Chunk Embeddings | Entity Embeddings | Relationship Embeddings | Keywords |
|------|------------------|-------------------|------------------------|----------|
| Smart | ✅ | ✅ | ✅ | ✅ |
| Semantic | ✅ | ❌ | ❌ | ❌ |
| Entity-lookup | ✅ | ✅ | ✅ | ✅ |
| Graph-traversal | ✅ | ✅ | ✅ | ❌ |

---

## Previous Changes (March 2026)

### 🔗 Relationship Embedding Processor

#### Robust Background Processor
- **File:** `backend/embedding_processor_robust.py`
- **Features:**
  - Pure asyncio (no threading issues)
  - Circuit breaker pattern for Ollama failures
  - Exponential backoff retry logic
  - Health monitoring with heartbeat file
  - Connection pooling (2-10 PostgreSQL connections)
  - Graceful shutdown handling
- **Performance:** ~800 embeddings/minute
- **Status:** Running in background

#### Entity Embedding Backfill
- **File:** `backend/backfill_entity_embeddings_robust.py`
- **Features:**
  - Same robustness as relationship processor
  - Can wait for relationships to complete first (`--wait-for-relationships`)
  - Configurable batch size and interval
- **Status:** Ready to run when relationships complete

### 💾 Schema & Storage

#### Schema Self-Containment
- **File:** `backend/schema.sql` (copied from `init.sql`)
- **Purpose:** Self-contained schema for v2.0-beta
- **Added:** `backend/init_database.py` for local database initialization

#### Storage Functions
- **File:** `backend/storage.py`
- **Functions Added:**
  - `search_entities()` - Entity vector search
  - `search_relationships()` - Relationship vector search
  - `get_related_entities()` - Graph traversal with recursive CTE
  - `get_chunks_by_entity()` - Entity chunk retrieval

### 🔌 Upload Endpoints

#### LLM Provider Configuration
- **Files:** `backend/pgvector_api.py`, `frontend/src/api/client.ts`
- **Change:** Upload endpoints now accept `llm_config` from frontend
- **Effect:** Entity extraction uses configurable DeepSeek/MiniMax instead of hardcoded MiniMax

#### Entity Embedding on Upload
- **Change:** New uploads now generate embeddings for:
  1. Document chunks (100% - each chunk)
  2. Document entity (filename embedding)
  3. Extracted entities (name + type + description)
- **Note:** Relationship embeddings added to background queue

---

## System Architecture

### Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────────────┐ │
│  │  Query Tab   │ │ Query+File   │ │     Config Tab      │ │
│  │  (4 modes)   │ │  (4 modes)   │ │ (LLM Provider Sel)  │ │
│  └──────────────┘ └──────────────┘ └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Port 8002)                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Search Mode Router                        │  │
│  │  smart / semantic / entity-lookup / graph-traversal   │  │
│  └───────────────────────────────────────────────────────┘  │
│                              │                               │
│  ┌───────────────────────────┼───────────────────────────┐  │
│  ▼                           ▼                           ▼  │
│ ┌──────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│ │    Smart     │  │  Entity-Lookup   │  │ Graph-Traversal│ │
│ │  (5 layers)  │  │    (5 layers)    │  │   (5 layers)   │ │
│ └──────┬───────┘  └────────┬─────────┘  └───────┬────────┘ │
│        │                   │                    │          │
│        └───────────────────┼────────────────────┘          │
│                            ▼                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Unified Storage Layer (storage.py)          │  │
│  │  • search_chunks()       - Chunk embeddings          │  │
│  │  • search_entities()     - Entity embeddings         │  │
│  │  • search_relationships() - Relationship embeddings   │  │
│  │  • get_related_entities() - Graph traversal          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL + pgvector (Port 5432)              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐ │
│  │    chunks    │ │   entities   │ │    relationships     │ │
│  │  (100% emb)  │ │  (backfill)  │ │ (background proc)    │ │
│  └──────────────┘ └──────────────┘ └──────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Ollama (Port 11434) - nomic-embed-text         │
│                    (768-dimensional embeddings)             │
└─────────────────────────────────────────────────────────────┘
```

---

## Documentation Updates

### New/Updated Documentation

| File | Description | Status |
|------|-------------|--------|
| `SEARCH_MODES_IMPLEMENTATION.md` | Implementation details for all search modes | ✅ Updated |
| `docs/SEARCH_MODES_SUMMARY.md` | User-facing search mode guide | ✅ Updated |
| `KEYWORD_EXTRACTION_IMPLEMENTATION.md` | Keyword extraction details | ✅ Updated |
| `CHANGELOG.md` | This file - all changes tracked | ✅ New |

---

## Migration Guide

### For Existing Users

No migration needed - all changes are backward compatible:
- Default mode is now "smart" (previously "semantic")
- Old API calls without `mode` parameter will use "smart"
- Explicit `mode: "semantic"` still works as expected

### For Developers

New mode support in frontend:
```typescript
// Frontend already supports all modes in config.ts
export type QueryMode = 'smart' | 'semantic' | 'entity-lookup' | 'graph-traversal';
```

---

## Performance Summary

| Mode | Typical Results | Latency | Embedding Coverage |
|------|----------------|---------|-------------------|
| Smart | 40-60 chunks | ~2-3s | All three types |
| Semantic | 35-45 chunks | ~1s | Chunks only |
| Entity-lookup | 35-50 chunks | ~1.5-2s | All three types |
| Graph-traversal | 40-60 chunks | ~2-4s | All three types |

---

## Known Issues & Limitations

1. **Relationship Embeddings Incomplete**
   - Current: ~62% of relationships have embeddings
   - Background processor running to complete
   - All modes work but with reduced quality until complete

2. **Entity Embeddings Partial**
   - New uploads: 100% have embeddings
   - Existing entities: Backfill pending
   - Can start backfill when relationships complete

3. **Graph-Traversal Latency**
   - Higher latency (~2-4s) due to 2-hop traversal
   - Consider for complex queries only

---

## Future Enhancements

### Planned
1. **LLM-Based Keyword Extraction**
   - Replace regex with LLM for better accuracy
   - Trade-off: Accuracy vs. Speed

2. **Query Intent Classification**
   - Auto-select mode based on query analysis
   - "What is X?" → Semantic
   - "Tell me about Company Y" → Entity-lookup
   - "How do X and Y relate?" → Graph-traversal

3. **Caching Layer**
   - Cache keyword extraction results
   - Cache entity/relationship lookups

### Under Consideration
1. **Multi-hop Query Resolution**
   - Answer questions requiring multiple hops
   - "What companies supply Tesla's batteries?"

2. **Graph Visualization API**
   - Export graph structure for visualization
   - Show entity connections

---

## Contributors

- System architecture and implementation: Development Team
- Documentation: Development Team

---

**Last Updated:** April 2026  
**Version:** v2.0-beta  
**Status:** Production Ready
