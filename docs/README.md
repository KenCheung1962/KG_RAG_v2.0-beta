# V2.0-Beta Documentation

> **Complete documentation for KG RAG v2.0-beta search and query system**

---

## Quick Start

| If you want to... | Read this |
|-------------------|-----------|
| Get up and running quickly | [QUICK_REFERENCE.md](QUICK_REFERENCE.md) |
| Understand all search modes | [SEARCH_MODES_SUMMARY.md](SEARCH_MODES_SUMMARY.md) |
| See complete technical reference | [V2_SEARCH_QUERY_MODES_REFERENCE.md](V2_SEARCH_QUERY_MODES_REFERENCE.md) |
| Check what's changed recently | [CHANGELOG_v2.0.md](CHANGELOG_v2.0.md) |

---

## Documentation Index

### Core Documentation

| Document | Description | Audience |
|----------|-------------|----------|
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | One-page reference card | All users |
| [SEARCH_MODES_SUMMARY.md](SEARCH_MODES_SUMMARY.md) | Search & query modes guide | Users, developers |
| [V2_SEARCH_QUERY_MODES_REFERENCE.md](V2_SEARCH_QUERY_MODES_REFERENCE.md) | Complete technical reference | Developers |
| [CHANGELOG_v2.0.md](CHANGELOG_v2.0.md) | Recent changes and migration guide | Developers |

### Feature-Specific Documentation

| Document | Description |
|----------|-------------|
| [APA_REFERENCES_IMPLEMENTATION.md](APA_REFERENCES_IMPLEMENTATION.md) | APA 7th edition reference formatting |
| [CITATION_VERIFICATION_FIX.md](CITATION_VERIFICATION_FIX.md) | Citation system implementation |
| [CONSOLIDATED_SEARCH_MODES.md](CONSOLIDATED_SEARCH_MODES.md) | Search modes with relationship enhancement |
| [SOURCE_RELEVANCE_FIX.md](SOURCE_RELEVANCE_FIX.md) | Source quality improvements |
| [STRICT_SOURCE_FILTERING.md](STRICT_SOURCE_FILTERING.md) | Similarity threshold implementation |
| [STRICT_TWO_STAGE_FILTERING.md](STRICT_TWO_STAGE_FILTERING.md) | Two-stage filtering pipeline |
| [WEBUI_SEARCH_MODES_UPDATE.md](WEBUI_SEARCH_MODES_UPDATE.md) | Frontend search mode integration |

### Architecture Documentation

| Document | Description |
|----------|-------------|
| [SEMANTIC_HYBRID_MODE.md](SEMANTIC_HYBRID_MODE.md) | Semantic-hybrid mode details |
| [RELATIONSHIP_EMBEDDINGS.md](RELATIONSHIP_EMBEDDINGS.md) | Relationship embedding system |
| [RELATIONSHIP_EMBEDDINGS_SEARCH.md](RELATIONSHIP_EMBEDDINGS_SEARCH.md) | Relationship-enhanced search |
| [POSTGRESQL_VS_LIGHTRAG_REASSESSMENT.md](POSTGRESQL_VS_LIGHTRAG_REASSESSMENT.md) | Architecture decisions |

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER QUERY                                │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     SEARCH MODES                                 │
│  (How to retrieve information)                                   │
│                                                                  │
│  • Smart (recommended)      - Multi-layer unified search        │
│  • Semantic                 - Pure vector similarity            │
│  • Semantic-Hybrid          - Vector + keywords                 │
│  • Entity-Lookup            - Entity-centric + expansion        │
│  • Graph-Traversal          - Graph BFS + reasoning             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     QUERY MODES                                  │
│  (How to generate response)                                      │
│                                                                  │
│  • Quick         - 600-1200 words, 6 academic refs              │
│  • Balanced      - 1500-2000 words, 10 academic refs (default)  │
│  • Comprehensive - 1800-2500 words, 14 academic refs            │
│  • Ultra-Deep    - 2500-3500 words, 18 academic refs            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     REFERENCE SYSTEM                             │
│                                                                  │
│  Database Sources (≤10)          LLM Academic References         │
│  • Similarity ≥ 0.7              • Mode-specific count (6-18)   │
│  • Numbered [1] to [N]           • APA 7th edition format       │
│  • Actual documents              • Numbered [N+1] onwards       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Features

### 1. Five Search Modes

All modes use **strict similarity filtering (≥ 0.7)** for quality:

| Mode | Primary Strategy | Best For |
|------|-----------------|----------|
| **Smart** ⭐ | Multi-layer fusion | All queries (recommended) |
| **Semantic** | Vector similarity | Conceptual questions |
| **Semantic-Hybrid** | Vector + keywords | Technical queries |
| **Entity-Lookup** | Entity-centric | Entity-focused questions |
| **Graph-Traversal** | Graph BFS | Relationship questions |

### 2. Four Query Modes

All modes support **streaming** and **mode-specific academic references**:

| Mode | Words | Sections | Academic Refs |
|------|-------|----------|---------------|
| **Quick** | 600-1200 | 3 | 6 |
| **Balanced** | 1500-2000 | 4 | 10 |
| **Comprehensive** | 1800-2500 | 5 | 14 |
| **Ultra-Deep** | 2500-3500 | 7 | 18 |

### 3. Dual-Source References

Every response includes:
- **Database Sources**: Up to 10 actual documents (similarity ≥ 0.7)
- **LLM Academic References**: Mode-specific count (6-18) in APA 7th edition format

### 4. Citation System

- In-text citations: `<span class="citation-ref">[N]</span>`
- Automatic post-processing prevents repeated citations
- Mix of database and academic sources required

---

## Quick API Examples

### Default Search
```bash
curl -X POST http://localhost:8002/api/v1/chat \
  -d '{"query": "What are the benefits of AI?"}'
```

### Specific Modes
```bash
# Smart search + Comprehensive response
curl -X POST http://localhost:8002/api/v1/chat \
  -d '{
    "query": "What are the benefits of AI?",
    "mode": "smart",
    "detail_level": "comprehensive"
  }'

# Entity-lookup + Quick response
curl -X POST http://localhost:8002/api/v1/chat \
  -d '{
    "query": "What products does Tesla make?",
    "mode": "entity-lookup",
    "detail_level": "quick"
  }'
```

### Full Configuration
```bash
curl -X POST http://localhost:8002/api/v1/chat \
  -d '{
    "query": "Your question here",
    "mode": "smart",
    "detail_level": "ultra-deep",
    "top_k": 10,
    "similarity_threshold": 0.7,
    "use_llm_references": true,
    "stream": true
  }'
```

---

## Configuration Summary

### Similarity Thresholds
```python
INITIAL_COLLECTION = 0.5        # First pass
STRICT_FILTERING = 0.7          # Final quality filter
ENTITY_CHUNK_MIN = 0.65         # Entity context minimum
```

### Source Limits
```python
MAX_DB_SOURCES = 10             # In reference section
MAX_SOURCES_PROCESSING = 15     # Internal processing
CHUNKS_PER_ENTITY = 5           # Per entity (reduced from 12)
```

### Relationship Enhancement
```python
SMART_BOOST = 0.12
SEMANTIC_BOOST = 0.10
ENTITY_LOOKUP_BOOST = 0.12
GRAPH_TRAVERSAL_BOOST = 0.08
```

---

## Recent Changes (v2.0-beta)

1. ✅ **Streaming for all query modes** - Progressive display for Quick, Balanced, Comprehensive, Ultra-Deep
2. ✅ **Strict similarity filtering** - All modes use ≥ 0.7 threshold
3. ✅ **Mode-specific academic references** - 6/10/14/18 refs by query mode
4. ✅ **Reduced entity chunk collection** - 5 per entity (was 12)
5. ✅ **Increased DB source limit** - 10 sources (was 5)
6. ✅ **Citation post-processing** - Automatic fixing of repeated citations
7. ✅ **APA 7th edition formatting** - Proper academic formatting

See [CHANGELOG_v2.0.md](CHANGELOG_v2.0.md) for complete details.

---

## Support

For issues or questions:
1. Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for common solutions
2. Review [SEARCH_MODES_SUMMARY.md](SEARCH_MODES_SUMMARY.md) for mode details
3. See [V2_SEARCH_QUERY_MODES_REFERENCE.md](V2_SEARCH_QUERY_MODES_REFERENCE.md) for technical details

---

*Last updated: 2026-04-01*
