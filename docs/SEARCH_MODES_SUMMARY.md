# KG RAG Search & Query Modes: Complete Summary

> **Version**: 2.0-beta  
> **Last Updated**: 2026-04-01

## Overview

KG RAG v2.0-beta provides **five search modes** and **four query modes**, all leveraging **three embedding types** (chunk, entity, relationship) to provide comprehensive search and response capabilities.

---

## Quick Reference

### Search Modes (How to Retrieve)

| Mode | Backend Name | Primary Strategy | Best For |
|------|-------------|------------------|----------|
| **Smart** ⭐ | `smart` | Multi-layer unified | All queries (Recommended) |
| **Semantic** | `semantic` | Vector similarity | Conceptual questions |
| **Semantic-Hybrid** | `semantic-hybrid` | Vector + keywords | Technical queries |
| **Entity-Lookup** | `entity-lookup` | Entity-centric + expansion | Entity-focused queries |
| **Graph-Traversal** | `graph-traversal` | Graph BFS + reasoning | Relationship queries |

### Query Modes (How to Respond)

| Mode | Words | Sections | Academic Refs | Best For |
|------|-------|----------|---------------|----------|
| **Quick** | 600-1200 | 3 | 6 (5-8 range) | Fast lookups |
| **Balanced** | 1500-2000 | 4 | 10 (8-12 range) | Standard research |
| **Comprehensive** | 1800-2500 | 5 | 14 (12-16 range) | Deep analysis |
| **Ultra-Deep** | 2500-3500 | 7 | 18 (16-20 range) | Academic papers |

---

## Search Modes Detailed

### 1. SMART Mode (Recommended) ⭐

**Backend Mode:** `smart`  
**Default:** Yes  
**Complexity:** High (automated)

**What it does:**
Intelligently combines ALL search strategies in 5 layers with strict quality filtering:

```
Layer 1: Semantic Chunk Search (Foundation)
    └── Vector search on chunks (initial: similarity ≥ 0.5)

Layer 2: Entity Discovery
    └── Entity embedding search → find relevant entities

Layer 3: Relationship Enhancement
    ├── Relationship embedding search
    ├── Extract entities from matching relationships
    └── Graph traversal from discovered entities

Layer 4: Keyword Boosting
    └── Extract HL/LL keywords → boost matching chunks

Layer 5: Entity Chunk Collection
    └── Get chunks from all discovered entities (max 5 per entity)

Final: Intelligent Fusion + Strict Filtering
    ├── Deduplicate across all sources
    ├── Apply layer-specific boosting
    ├── Rank by composite similarity score
    └── STRICT FILTER: similarity ≥ 0.7
```

**Key Parameters**:
```python
{
    "similarity_threshold": 0.7,    # Strict quality filter
    "entity_boost_factor": 0.12,
    "max_entities": 8,
    "chunks_per_entity": 5,         # Reduced from 12
    "max_db_sources": 10            # In references
}
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
- Typical results: 40-60 chunks → 5-10 sources after strict filtering
- Latency: ~2-3 seconds
- Coverage: Highest (combines all sources)

---

### 2. SEMANTIC Mode

**Backend Mode:** `semantic`  
**Complexity:** Low

**What it does:**
Direct vector similarity search on chunks with relationship enhancement:

```python
# 1. Vector search
vector_results = await storage.search_chunks(
    query_vector=query_embedding,
    limit=40,
    distance_metric=DistanceMetric.COSINE
)

# 2. Relationship enhancement
enhanced_results = await enhance_with_relationships(vector_results)

# 3. Strict filtering
filtered_results = [r for r in enhanced_results if r.similarity >= 0.7]
```

**Key Parameters**:
```python
{
    "similarity_threshold": 0.7,
    "entity_boost_factor": 0.10,
    "max_entities": 5
}
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
- Typical results: 35-45 chunks → 5-10 sources after filtering
- Latency: ~1 second
- Coverage: Good (chunks + relationship boost)

---

### 3. SEMANTIC-HYBRID Mode

**Backend Mode:** `semantic-hybrid`  
**Complexity:** Medium

**What it does:**
Combines vector similarity with keyword matching:

```
1. Vector search (same as semantic)
2. High-level keyword extraction (LLM)
3. Keyword boosting (+0.05 to matching chunks)
4. Relationship enhancement
5. Combined ranking + strict filtering (≥ 0.7)
```

**Key Parameters**:
```python
{
    "similarity_threshold": 0.7,
    "entity_boost_factor": 0.10,
    "max_entities": 6,
    "keyword_boost": 0.05
}
```

**Best for:**
- Queries with important concept keywords
- When specific terminology matters
- Technical questions

---

### 4. ENTITY-LOOKUP Mode

**Backend Mode:** `entity-lookup`  
**Complexity:** Medium

**What it does:**
Comprehensive entity-based search with aggressive expansion:

```
Query ─┬─► Entity Embeddings ─► Find Entities ─┬─► Keyword Boost ─┐
       │                                       │                  │
       ├─► Relationship Embeddings ─► Find Related Entities ◄────┤
       │                                                          │
       ├─► Chunk Embeddings ─► Direct Semantic Search ─┬─► Collect Chunks
       │                                                │     (max 5/entity)
       └───────────────────────────────────────────────┘
                            │
                            ▼
                    Deduplicate & Rank ─► STRICT FILTER (≥ 0.7)
```

**Key Parameters**:
```python
{
    "similarity_threshold": 0.7,
    "entity_boost_factor": 0.12,
    "max_entities": 8,              # Higher expansion
    "chunks_per_entity": 5          # Reduced from 12
}
```

**Best for:**
- Specific entity-focused questions
- Questions about companies, people, products
- When entity relationships matter

**Example Queries:**
- "What products does Tesla manufacture?"
- "Who is the CEO of Microsoft?"
- "What are Apple's main suppliers?"

**Performance:**
- Typical results: 35-50 chunks → 5-10 sources after filtering
- Latency: ~1.5-2 seconds
- Coverage: Good (entity focus + relationship expansion)

---

### 5. GRAPH-TRAVERSAL Mode

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
                              STRICT FILTER (≥ 0.7) ─► Return Top K
```

**Key Parameters**:
```python
{
    "similarity_threshold": 0.7,
    "max_depth": 2,
    "entity_boost_factor": 0.08,
    "max_relationships": 8
}
```

**Best for:**
- Overview questions
- Relationship-focused queries
- Questions about connections between entities
- Industry landscape questions

**Example Queries:**
- "How do tech companies compete in the AI space?"
- "What partnerships exist in the EV industry?"
- "Show me the competitive landscape for cloud providers"

**Performance:**
- Typical results: 40-60 chunks → 5-10 sources after filtering
- Latency: ~2-4 seconds
- Coverage: Highest for relationship queries

---

## Query Modes Detailed

Query modes determine how the response is **generated** after search retrieval.

### Streaming Support

**All query modes now support streaming** for progressive display:

```json
{"type": "status", "stage": "outline", "progress": 0}
{"type": "content", "section": "executive_summary", "progress": 15}
{"type": "content", "section": "section_1", "progress": 30}
...
{"type": "complete", "word_count": 1850}
```

### 1. QUICK Mode

**Purpose**: Fast, concise answers  
**Use for**: Simple factual questions, quick lookups

```python
{
    "detail_level": "quick",
    "target_words": "600-1200",
    "num_sections": 3,
    "num_subsections": 2,
    "num_academic_refs": 6,         # 5-8 range
    "max_tokens": 8192,
    "streaming": True
}
```

**Response Structure**:
```
1. Executive Summary (150+ words)
2. Section 1-3 (each with 2 subsections)
3. Conclusion (200+ words)
4. References (DB sources + 6 academic refs)
```

---

### 2. BALANCED Mode (Default)

**Purpose**: Detailed but focused answers  
**Use for**: Standard research questions

```python
{
    "detail_level": "balanced",
    "target_words": "1500-2000",
    "num_sections": 4,
    "num_subsections": 3,
    "num_academic_refs": 10,        # 8-12 range
    "max_tokens": 8192,
    "streaming": True
}
```

**Response Structure**:
```
1. Executive Summary (300+ words)
2. Section 1-4 (each with 3 subsections)
3. Conclusion (400+ words)
4. References (DB sources + 10 academic refs)
```

---

### 3. COMPREHENSIVE Mode

**Purpose**: In-depth analysis with extensive coverage  
**Use for**: Complex research questions, literature review style

```python
{
    "detail_level": "comprehensive",
    "target_words": "1800-2500",
    "num_sections": 5,
    "num_subsections": 3,
    "num_academic_refs": 14,        # 12-16 range
    "max_tokens": 8192,
    "streaming": True
}
```

**Response Structure**:
```
1. Executive Summary (400+ words)
2. Section 1-5 (each with 3 subsections)
3. Conclusion (500+ words)
4. References (DB sources + 14 academic refs)
```

---

### 4. ULTRA-DEEP Mode

**Purpose**: Maximum detail, exhaustive coverage  
**Use for**: Academic research, survey paper style

```python
{
    "detail_level": "ultra-deep",
    "target_words": "2500-3500",
    "num_sections": 7,
    "num_subsections": 3,
    "num_academic_refs": 18,        # 16-20 range
    "max_tokens": 8192,
    "streaming": True
}
```

**Response Structure**:
```
1. Executive Summary (500+ words)
2. Section 1-7 (each with 3 subsections)
3. Conclusion (600+ words)
4. References (DB sources + 18 academic refs)
```

---

## Embedding Usage Matrix

| Embedding Type | Smart | Semantic | Semantic-Hybrid | Entity-Lookup | Graph-Traversal |
|----------------|-------|----------|-----------------|---------------|-----------------|
| **Chunk Embeddings** | ✅ Primary | ✅ Only | ✅ Primary | ✅ Yes | ✅ Yes |
| **Entity Embeddings** | ✅ Discovery | ❌ No | ❌ No | ✅ Primary | ✅ Seeds |
| **Relationship Embeddings** | ✅ Enhancement | ✅ Enhancement | ✅ Enhancement | ✅ Enhancement | ✅ Primary |
| **Keyword Extraction** | ✅ Boosting | ❌ No | ✅ Boosting | ✅ Boosting | ❌ No |
| **Graph Traversal** | ✅ 1-hop | ❌ No | ❌ No | ✅ 1-hop | ✅ 2-hop |
| **Strict Filtering (≥0.7)** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |

---

## Reference Generation System

### Dual-Source References

All responses include references from **two sources**:

```
┌──────────────────────────────┬─────────────────────────────────┐
│   DATABASE SOURCES           │   LLM ACADEMIC REFERENCES       │
│   (Actual Documents)         │   (Generated from Knowledge)    │
├──────────────────────────────┼─────────────────────────────────┤
│ • Real document chunks       │ • APA 7th edition format        │
│ • Similarity ≥ 0.7           │ • Training knowledge synthesis  │
│ • Up to 10 sources           │ • Mode-specific count (6-18)    │
│ • Numbered [1] to [N]        │ • Numbered [N+1] onwards        │
└──────────────────────────────┴─────────────────────────────────┘
```

### Mode-Specific Academic Reference Counts

| Query Mode | Refs Range | Actual Count | Example Numbering |
|------------|-----------|--------------|-------------------|
| Quick | 5-8 | 6 | [N+1] to [N+6] |
| Balanced | 8-12 | 10 | [N+1] to [N+10] |
| Comprehensive | 12-16 | 14 | [N+1] to [N+14] |
| Ultra-Deep | 16-20 | 18 | [N+1] to [N+18] |

### Citation Format

**In-text citations**:
```html
<span class="citation-ref">[N]</span>

<!-- Example -->
<p>Research shows HBM improves performance <span class="citation-ref">[1]</span>. 
Academic studies confirm <span class="citation-ref">[4]</span>.</p>
```

**Citation requirements**:
- Minimum 8 different sources in Executive Summary and Conclusion
- Must mix database sources [1-N] and academic references [N+1 onwards]
- No consecutive repeats of the same source
- Post-processing automatically fixes repeated citations

---

## Usage Guide

### Quick Selection Guide

| Your Question Type | Recommended Search | Recommended Query |
|-------------------|-------------------|-------------------|
| "What is X?" / "How does Y work?" | **Smart** | Balanced |
| Quick factual lookup | Semantic | Quick |
| "Tell me about Company X" | **Smart** or Entity-lookup | Balanced |
| "How do X and Y relate?" | **Smart** or Graph-traversal | Comprehensive |
| Deep academic research | **Smart** | Ultra-Deep |
| Industry overview | **Smart** or Graph-traversal | Comprehensive |

### API Usage Examples

```bash
# Default (Smart search + Balanced response)
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the benefits of AI?"}'

# Smart search with specific query mode
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the benefits of AI?",
    "mode": "smart",
    "detail_level": "comprehensive"
  }'

# Entity-lookup mode
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What products does Tesla make?",
    "mode": "entity-lookup",
    "detail_level": "balanced"
  }'

# Graph-traversal with streaming
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do companies compete in AI?",
    "mode": "graph-traversal",
    "detail_level": "comprehensive",
    "stream": true
  }'

# Full configuration
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Your question here",
    "mode": "smart",
    "detail_level": "ultra-deep",
    "top_k": 10,
    "similarity_threshold": 0.7,
    "use_llm_references": true,
    "stream": true
  }'
```

---

## Configuration Parameters

### Search Configuration

```python
# Similarity thresholds
SIMILARITY_THRESHOLD_INITIAL = 0.5      # First pass collection
SIMILARITY_THRESHOLD_STRICT = 0.7       # Final filtering (all modes)
SIMILARITY_THRESHOLD_ENTITY_CHUNK = 0.65 # Entity context minimum

# Source limits
MAX_DB_SOURCES = 10                     # Max in reference section
MAX_SOURCES_PROCESSING = 15             # Internal processing limit

# Relationship enhancement
RELATIONSHIP_BOOST_FACTORS = {
    "smart": 0.12,
    "semantic": 0.10,
    "semantic-hybrid": 0.10,
    "entity-lookup": 0.12,
    "graph-traversal": 0.08
}

# Entity expansion limits
MAX_ENTITIES = {
    "smart": 8,
    "semantic": 5,
    "semantic-hybrid": 6,
    "entity-lookup": 8,
    "graph-traversal": 5
}

# Entity chunk collection (reduced from 12)
CHUNKS_PER_ENTITY = 5
```

### Query Mode Configuration

```python
QUERY_MODE_CONFIG = {
    "quick": {
        "target_words": "600-1200",
        "num_sections": 3,
        "num_subsections": 2,
        "num_academic_refs": 6,      # 5-8 range
        "max_tokens": 8192
    },
    "balanced": {
        "target_words": "1500-2000",
        "num_sections": 4,
        "num_subsections": 3,
        "num_academic_refs": 10,     # 8-12 range
        "max_tokens": 8192
    },
    "comprehensive": {
        "target_words": "1800-2500",
        "num_sections": 5,
        "num_subsections": 3,
        "num_academic_refs": 14,     # 12-16 range
        "max_tokens": 8192
    },
    "ultra-deep": {
        "target_words": "2500-3500",
        "num_sections": 7,
        "num_subsections": 3,
        "num_academic_refs": 18,     # 16-20 range
        "max_tokens": 8192
    }
}
```

---

## Performance Summary

### Search Performance

| Mode | Typical Results | After Filtering (≥0.7) | Latency | Coverage |
|------|----------------|----------------------|---------|----------|
| Smart | 40-60 chunks | 5-10 sources | ~2-3s | All embeddings |
| Semantic | 35-45 chunks | 5-10 sources | ~1s | Chunks + rel |
| Semantic-Hybrid | 35-45 chunks | 5-10 sources | ~1.5s | Chunks + rel |
| Entity-lookup | 35-50 chunks | 5-10 sources | ~1.5-2s | All embeddings |
| Graph-traversal | 40-60 chunks | 5-10 sources | ~2-4s | All embeddings |

### Query Performance

| Mode | Target Words | Generation Time | Total References |
|------|-------------|-----------------|------------------|
| Quick | 600-1200 | ~30s | DB + 6 academic |
| Balanced | 1500-2000 | ~60s | DB + 10 academic |
| Comprehensive | 1800-2500 | ~90s | DB + 14 academic |
| Ultra-Deep | 2500-3500 | ~120s | DB + 18 academic |

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
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Query Mode Processor                               │
│                                                                   │
│  • Quick/Balanced/Comprehensive/Ultra-Deep                      │
│  • Streaming generation                                          │
│  • Reference generation (DB + LLM academic)                      │
│  • Citation formatting                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `search_smart()` | `pgvector_api.py` | Smart mode - 5-layer unified search |
| `search_entity_lookup()` | `pgvector_api.py` | Entity-lookup mode |
| `search_graph_traversal()` | `pgvector_api.py` | Graph mode - traversal |
| `chat_stream()` | `pgvector_api.py` | Streaming response handler |
| `generate_ultra_response_streaming()` | `pgvector_api.py` | Multi-step generation |
| `generate_llm_academic_references()` | `pgvector_api.py` | Academic reference generation |
| `post_process_citations()` | `pgvector_api.py` | Fix repeated citations |
| `extract_keywords_for_search()` | `pgvector_api.py` | Keyword extraction |

---

## Current Status

### Embedding Status

| Table | Total | With Embeddings | Percentage |
|-------|-------|-----------------|------------|
| Chunks | 369,004 | 369,004 | ✅ 100% |
| Entities | 46,012 | ~46,012* | ✅ Complete |
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

## Recommendations

### For Users

1. **Use Smart mode by default** - It automatically combines the best strategies
2. **Use Quick mode for fast answers** - Best for simple factual questions
3. **Use Ultra-Deep for academic work** - Maximum detail and references
4. **Enable LLM references** - Adds academic credibility with APA citations
5. **Keep similarity threshold at 0.7** - Ensures high-quality sources

### For Developers

1. **Smart mode has the best coverage** - Use for maximum recall
2. **All modes use strict filtering (≥0.7)** - Ensures quality
3. **Streaming works for all query modes** - Progressive display
4. **Mode-specific reference counts** - Adjust based on response depth needed
5. **Graceful degradation** - Works even if some embeddings are missing

---

## Summary

KG RAG v2.0-beta provides a **unified search and query architecture**:

- **5 search modes** cover all retrieval use cases
- **4 query modes** provide appropriate response depth
- **All modes** use strict similarity filtering (≥ 0.7)
- **Dual-source references** combine database sources + LLM academic references
- **Streaming support** for all query modes
- **Background processors** continue enhancing embedding coverage
- **Both chat endpoints** support all mode combinations

**The recommended approach:**
- **Search**: Use **Smart mode** for all queries
- **Query**: Use **Balanced** for standard queries, **Ultra-Deep** for academic work
- **References**: Always enable `use_llm_references: true` for academic credibility
