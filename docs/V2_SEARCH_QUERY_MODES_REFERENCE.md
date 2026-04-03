# V2.0-Beta: Search & Query Modes Complete Reference

> **Version**: 2.0-beta  
> **Last Updated**: 2026-04-01  
> **Scope**: All search modes, query modes, and reference generation

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Search Modes](#2-search-modes)
3. [Query/Response Modes](#3-queryresponse-modes)
4. [Reference Generation](#4-reference-generation)
5. [Citation System](#5-citation-system)
6. [API Reference](#6-api-reference)
7. [Configuration](#7-configuration)

---

## 1. Architecture Overview

### 1.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER QUERY                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SEARCH MODE SELECTION                                   │
│   (Smart | Semantic | Entity-Lookup | Graph-Traversal)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      RETRIEVAL PIPELINE                                      │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  Vector Search  │  │  Entity Search  │  │ Graph Traversal │              │
│  │    (Chunks)     │  │   (Entities)    │  │ (Relationships) │              │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│           │                    │                    │                       │
│           └────────────────────┴────────────────────┘                       │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              RELATIONSHIP EMBEDDING ENHANCEMENT                      │   │
│  │   • Boost results from connected entities                            │   │
│  │   • Add new results from relationship matches                        │   │
│  │   • Include relationship descriptions                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      QUERY MODE PROCESSING                                   │
│   (Quick | Balanced | Comprehensive | Ultra-Deep)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      RESPONSE GENERATION                                     │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              REFERENCE GENERATION LAYER                              │   │
│  │                                                                      │   │
│  │   Database Sources (up to 10, similarity > 0.7)                      │   │
│  │   [1], [2], [3] ... [N]  →  Actual source documents                 │   │
│  │                                                                      │   │
│  │   LLM Academic References (mode-specific count)                      │   │
│  │   [N+1] ... [N+X]  →  APA format academic papers                    │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FORMATTED RESPONSE                                      │
│   • Structured content with sections                                        │
│   • In-text citations [N]                                                   │
│   • References section (DB + Academic)                                      │
│   • Source metadata                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Components

| Component | Description | File |
|-----------|-------------|------|
| **Search Pipeline** | Multi-layer retrieval with relationship enhancement | `backend/pgvector_api.py` |
| **Query Processor** | Mode-specific generation strategies | `backend/pgvector_api.py` |
| **Reference Generator** | Dual-source reference generation | `backend/pgvector_api.py` |
| **Citation Formatter** | In-text citation and reference formatting | `backend/pgvector_api.py` |
| **Response Renderer** | Frontend display with citation support | `frontend/src/components/tabs/QueryTab.ts` |

---

## 2. Search Modes

Search modes determine **how information is retrieved** from the knowledge graph and document store.

### 2.1 SMART Mode (Recommended Default)

**Purpose**: Intelligent multi-strategy search that adapts to the query automatically.

**Implementation Layers**:

```
Layer 1: Semantic Vector Search
├── Query embedding (nomic-embed-text, 768-dim)
├── Chunk similarity search (top 40)
└── Initial similarity filtering (≥ 0.5)

Layer 2: High-Level Keyword Extraction
├── LLM extracts key concepts from query
├── Keyword matching against chunk content
└── Boost factor: +0.05 to matching chunks

Layer 3: Entity Discovery
├── Named entity recognition
├── Entity embedding search
├── Relationship traversal (up to 8 entities)
└── Chunk collection from entity contexts (max 5 per entity)

Layer 4: Relationship Embedding Enhancement
├── Relationship vector search
├── Boost connected entities (factor: 0.12)
├── Add new entities from relationship matches
└── Include relationship descriptions

Layer 5: Multi-Layer Fusion
├── Re-rank by combined score
├── Deduplication
└── Final filtering (similarity ≥ 0.7)
```

**Parameters**:
```python
{
    "mode": "smart",
    "top_k": 10,                    # Final results to return
    "similarity_threshold": 0.7,    # Strict quality filter
    "entity_boost_factor": 0.12,    # Relationship boost
    "max_entities": 8,              # Entity expansion limit
    "max_relationships": 15         # Relationship descriptions
}
```

**When to Use**: 
- Default choice for all queries
- When query intent is unclear
- For best overall results

---

### 2.2 SEMANTIC Mode

**Purpose**: Pure vector similarity search with relationship enhancement.

**Implementation**:
```
1. Query → Embedding (Ollama nomic-embed-text)
2. Vector search on chunks (cosine similarity)
3. Relationship embedding enhancement
4. Re-ranking by combined score
5. Strict filtering (similarity ≥ 0.7)
```

**Parameters**:
```python
{
    "mode": "semantic",
    "top_k": 10,
    "similarity_threshold": 0.7,
    "entity_boost_factor": 0.10,
    "max_entities": 5,
    "max_relationships": 12
}
```

**When to Use**:
- General knowledge questions
- Conceptual queries
- When entity names are unknown

---

### 2.3 SEMANTIC-HYBRID Mode

**Purpose**: Combines vector similarity with keyword matching.

**Implementation**:
```
1. Vector search (same as semantic)
2. High-level keyword extraction
3. Keyword boosting (+0.05 to matches)
4. Relationship enhancement
5. Combined ranking
```

**Parameters**:
```python
{
    "mode": "semantic-hybrid",
    "top_k": 10,
    "similarity_threshold": 0.7,
    "entity_boost_factor": 0.10,
    "max_entities": 6,
    "keyword_boost": 0.05
}
```

**When to Use**:
- Queries with important concept keywords
- When specific terminology matters
- Technical questions

---

### 2.4 ENTITY-LOOKUP Mode

**Purpose**: Entity-centric search with aggressive relationship expansion.

**Implementation**:
```
1. Entity name extraction from query
2. Entity embedding search
3. Collect chunks from entity contexts (max 5 per entity)
4. Relationship traversal (up to 8 entities)
5. Include relationship descriptions
6. Re-ranking
```

**Parameters**:
```python
{
    "mode": "entity-lookup",
    "top_k": 10,
    "similarity_threshold": 0.7,
    "entity_boost_factor": 0.12,
    "max_entities": 8,              # Higher expansion
    "chunks_per_entity": 5          # Reduced from 12
}
```

**When to Use**:
- Entity-focused questions ("What products does Tesla make?")
- When specific entities are known
- Relationship exploration

---

### 2.5 GRAPH-TRAVERSAL Mode

**Purpose**: Deep graph exploration using BFS traversal.

**Implementation**:
```
1. Seed entity identification
2. BFS traversal (max_depth: 2-3)
3. Collect all connected entities
4. Relationship embedding parallel search
5. Chunk collection from all discovered entities
6. Include relationship paths
```

**Parameters**:
```python
{
    "mode": "graph-traversal",
    "top_k": 10,
    "max_depth": 2,                 # Traversal depth
    "similarity_threshold": 0.7,
    "entity_boost_factor": 0.08,
    "max_relationships": 8
}
```

**When to Use**:
- Relationship questions ("How do companies compete?")
- Network analysis queries
- Overview questions requiring breadth

---

### 2.6 Search Mode Comparison

| Mode | Primary Strategy | Relationship Boost | Entity Expansion | Best For |
|------|-----------------|-------------------|------------------|----------|
| **Smart** | Multi-layer fusion | 0.12 | 8 entities | Default/all queries |
| **Semantic** | Vector similarity | 0.10 | 5 entities | General questions |
| **Semantic-Hybrid** | Vector + Keywords | 0.10 | 6 entities | Technical queries |
| **Entity-Lookup** | Entity-centric | 0.12 | 8 entities | Entity-focused queries |
| **Graph-Traversal** | BFS traversal | 0.08 | Variable | Relationship queries |

---

## 3. Query/Response Modes

Query modes determine **how the response is generated** after information retrieval.

### 3.1 QUICK Mode

**Purpose**: Fast, concise answers for simple questions.

**Implementation**:
```python
{
    "target_words": "600-1200",
    "num_sections": 3,
    "num_subsections": 2,
    "max_tokens": 8192,
    "streaming": True,
    "num_academic_refs": 6,         # 5-8 range
    "system_prompt": "You are a knowledgeable research assistant."
}
```

**Structure**:
```
1. Executive Summary (150+ words)
2. Section 1 (with 2 subsections)
3. Section 2 (with 2 subsections)
4. Section 3 (with 2 subsections)
5. Conclusion (200+ words)
6. References (DB sources + 6 academic refs)
```

**When to Use**:
- Simple factual questions
- Quick lookups
- Time-sensitive queries

---

### 3.2 BALANCED Mode

**Purpose**: Detailed but focused answers (default mode).

**Implementation**:
```python
{
    "target_words": "1500-2000",
    "num_sections": 4,
    "num_subsections": 3,
    "max_tokens": 8192,
    "streaming": True,
    "num_academic_refs": 10,        # 8-12 range
    "system_prompt": "You are a research scientist. Write detailed content."
}
```

**Structure**:
```
1. Executive Summary (300+ words)
2. Section 1 (with 3 subsections)
3. Section 2 (with 3 subsections)
4. Section 3 (with 3 subsections)
5. Section 4 (with 3 subsections)
6. Conclusion (400+ words)
7. References (DB sources + 10 academic refs)
```

**When to Use**:
- Standard research questions
- Most general queries
- Default choice

---

### 3.3 COMPREHENSIVE Mode

**Purpose**: In-depth analysis with extensive coverage.

**Implementation**:
```python
{
    "target_words": "1800-2500",
    "num_sections": 5,
    "num_subsections": 3,
    "max_tokens": 8192,
    "streaming": True,
    "num_academic_refs": 14,        # 12-16 range
    "system_prompt": "You are a senior research scientist writing academic survey papers."
}
```

**Structure**:
```
1. Executive Summary (400+ words)
2. Section 1-5 (each with 3 subsections)
3. Conclusion (500+ words)
4. References (DB sources + 14 academic refs)
```

**When to Use**:
- Complex research questions
- Literature review style queries
- When thoroughness is critical

---

### 3.4 ULTRA-DEEP Mode

**Purpose**: Maximum detail, exhaustive coverage.

**Implementation**:
```python
{
    "target_words": "2500-3500",
    "num_sections": 7,
    "num_subsections": 3,
    "max_tokens": 8192,
    "streaming": True,
    "num_academic_refs": 18,        # 16-20 range
    "system_prompt": "You are a senior research scientist writing academic survey papers."
}
```

**Structure**:
```
1. Executive Summary (500+ words)
2. Section 1-7 (each with 3 subsections)
3. Conclusion (600+ words)
4. References (DB sources + 18 academic refs)
```

**When to Use**:
- Academic research
- Survey paper style responses
- Maximum detail required

---

### 3.5 Query Mode Comparison

| Mode | Target Words | Sections | Academic Refs | Generation Time | Best For |
|------|-------------|----------|---------------|-----------------|----------|
| **Quick** | 600-1200 | 3 | 6 | ~30s | Simple questions |
| **Balanced** | 1500-2000 | 4 | 10 | ~60s | Standard queries |
| **Comprehensive** | 1800-2500 | 5 | 14 | ~90s | Deep research |
| **Ultra-Deep** | 2500-3500 | 7 | 18 | ~120s | Academic papers |

---

## 4. Reference Generation

### 4.1 Dual-Source Reference System

The system generates references from **two distinct sources**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    REFERENCE SOURCES                             │
├───────────────────────────┬─────────────────────────────────────┤
│   DATABASE SOURCES        │   LLM ACADEMIC REFERENCES           │
│   (Actual Documents)      │   (Generated from LLM Knowledge)    │
├───────────────────────────┼─────────────────────────────────────┤
│ • [1] Source A.txt        │ • [N+1] Smith, J. (2023)...         │
│ • [2] Source B.pdf        │ • [N+2] Chen, W. & Liu, Y. (2024)..│
│ • [3] Source C.html       │ • [N+3] Johnson et al. (2022)...    │
│ ... up to 10 sources      │ ... mode-specific count (6-18)      │
├───────────────────────────┼─────────────────────────────────────┤
│ Strict similarity > 0.7   │ APA 7th edition format              │
│ Real document chunks      │ LLM's training knowledge            │
│ Verifiable sources        │ Academic credibility                │
└───────────────────────────┴─────────────────────────────────────┘
```

### 4.2 Database Source Selection

**Quality Criteria**:
```python
# Strict filtering pipeline
1. Vector search at similarity ≥ 0.5 (initial collection)
2. Re-ranking with cross-encoder
3. Final filtering: similarity ≥ 0.7 (strict quality)
4. Deduplication by source name
5. Limit: Maximum 10 sources
```

**Source Properties**:
- Each source must have `similarity >= 0.7`
- Sources are deduplicated by filename
- Up to 10 highest-quality sources are included
- Source format: `[N] filename.txt` or `[N] Author (Year). Title.`

### 4.3 LLM Academic Reference Generation

**Mode-Specific Counts**:

| Query Mode | Academic Refs Range | Actual Count | Numbering |
|------------|-------------------|--------------|-----------|
| Quick | 5-8 | 6 | [N+1] to [N+6] |
| Balanced | 8-12 | 10 | [N+1] to [N+10] |
| Comprehensive | 12-16 | 14 | [N+1] to [N+14] |
| Ultra-Deep | 16-20 | 18 | [N+1] to [N+18] |

**Generation Process**:

```python
async def generate_llm_academic_references(
    query: str,
    num_db_sources: int,
    num_academic_refs: int,  # Mode-specific (6, 10, 14, or 18)
    provider: str = "deepseek"
) -> List[str]:
    """
    Generate APA 7th edition references from LLM knowledge.
    """
    prompt = f"""
    Generate {num_academic_refs} academic references in APA 7th edition format.
    
    Requirements:
    - Start numbering from [{num_db_sources + 1}]
    - Use proper APA format: Author, A. A. (Year). Title. Source. DOI
    - Mix of classic and recent publications (2010-2024)
    - Include peer-reviewed journals, books, conference papers
    - Italicize journal names and book titles
    
    Output format:
    <div class="reference-item">
        <span class="ref-number">[{num_db_sources + 1}]</span>
        Author, A. A. (Year). <i>Title</i>. <i>Journal</i>, Vol(Issue), pp. DOI
    </div>
    """
    
    references = await llm_complete(prompt)
    return parse_references(references)
```

**APA 7th Edition Format**:
```
Journal Article:
Smith, J. D., & Jones, M. A. (2023). Title of article. <i>Journal Name</i>, 15(2), 45-67. https://doi.org/xx.xxx

Book:
Chen, W. (2024). <i>Book Title: Subtitle</i> (2nd ed.). Publisher.

Conference Paper:
Johnson, R. et al. (2022). Paper title. In <i>Conference Proceedings</i> (pp. 123-145). IEEE.
```

### 4.4 Reference Section Assembly

**Complete Reference Section Structure**:

```html
<query-h2>📚 References</query-h2>

<div class="references-list">
    <!-- Database Sources -->
    <div class="reference-item">
        <span class="ref-number">[1]</span> 
        <span class="ref-source">cybersecurity_threats.txt</span>
    </div>
    <div class="reference-item">
        <span class="ref-number">[2]</span> 
        <span class="ref-source">HBM_Industry_Report.pdf</span>
    </div>
    <!-- ... up to 10 DB sources -->
    
    <!-- LLM Academic References -->
    <div class="reference-item">
        <span class="ref-number">[3]</span> 
        Smith, J. D. (2023). <i>Advanced Memory Architecture</i>. <i>IEEE Computer</i>, 45(3), 78-92.
    </div>
    <div class="reference-item">
        <span class="ref-number">[4]</span> 
        Chen, W., & Liu, Y. (2024). High-bandwidth memory systems. <i>Nature Electronics</i>, 7(1), 23-35.
    </div>
    <!-- ... mode-specific count (6-18) -->
</div>
```

---

## 5. Citation System

### 5.1 In-Text Citation Format

**Standard Format**:
```html
<span class="citation-ref">[N]</span>
```

**Example in Content**:
```html
<p>Research indicates that high-bandwidth memory significantly 
improves AI training performance <span class="citation-ref">[1]</span>. 
Academic studies have shown similar improvements in data center 
applications <span class="citation-ref">[3]</span>.</p>
```

### 5.2 Citation Requirements by Section

| Section | Min Citations | Source Mix Required |
|---------|--------------|---------------------|
| Executive Summary | 8+ | Both DB + Academic |
| Each Subsection | 3-5 | Varied sources |
| Conclusion | 8+ | Both DB + Academic |

### 5.3 Citation Post-Processing

To prevent repeated citations, the system applies post-processing:

```python
def post_process_citations(content: str, num_db_sources: int, num_academic_refs: int) -> str:
    """
    Fix repeated citations by alternating between DB and academic sources.
    """
    # Pattern: Find consecutive same citations
    # Replace with alternating DB/academic sources
    
    # Example transformation:
    # Input:  "...[1]... [1]... [1]..."
    # Output: "...[1]... [N+1]... [2]..."
```

### 5.4 Citation Consistency Rules

1. **No Consecutive Repeats**: Same source cannot be cited twice in a row
2. **Mixed Sources**: Must alternate between DB sources [1-N] and academic refs [N+1 onwards]
3. **Minimum Variety**: At least 8 different sources in Executive Summary and Conclusion
4. **Format Compliance**: Must use exact `<span class="citation-ref">[N]</span>` format

---

## 6. API Reference

### 6.1 Chat Endpoint

**Endpoint**: `POST /api/v1/chat`

**Request Body**:
```json
{
    "query": "What are the benefits of renewable energy?",
    "mode": "smart",
    "detail_level": "balanced",
    "top_k": 10,
    "similarity_threshold": 0.7,
    "use_llm_references": true,
    "stream": true
}
```

**Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | User query text |
| `mode` | string | "smart" | Search mode: smart, semantic, semantic-hybrid, entity-lookup, graph-traversal |
| `detail_level` | string | "balanced" | Query mode: quick, balanced, comprehensive, ultra-deep |
| `top_k` | integer | 10 | Number of results to return |
| `similarity_threshold` | float | 0.7 | Minimum similarity score (0.0-1.0) |
| `use_llm_references` | boolean | true | Include LLM-generated academic references |
| `stream` | boolean | true | Enable streaming response |

**Streaming Response Format**:
```json
{"type": "status", "stage": "outline", "message": "Creating outline...", "progress": 0}
{"type": "content", "section": "title", "content": "<query-h1>Query Text</query-h1>", "progress": 5}
{"type": "content", "section": "executive_summary", "content": "...", "progress": 15}
{"type": "content", "section": "section_1", "content": "...", "progress": 30}
...
{"type": "content", "section": "references", "content": "...", "progress": 95}
{"type": "complete", "word_count": 1850, "sections": 5}
```

### 6.2 Search Endpoint

**Endpoint**: `POST /api/v1/search`

**Request Body**:
```json
{
    "query": "machine learning applications",
    "mode": "smart",
    "top_k": 10,
    "similarity_threshold": 0.7
}
```

**Response**:
```json
{
    "results": [
        {
            "chunk_id": "doc_123_45",
            "content": "...",
            "similarity": 0.87,
            "source": "ml_research.pdf",
            "metadata": {
                "smart_layer": "semantic",
                "relationship_enhanced": true,
                "relationship_boost": 0.10
            }
        }
    ],
    "total_found": 45,
    "layers_used": ["semantic", "entity", "relationship"]
}
```

---

## 7. Configuration

### 7.1 Backend Configuration

**File**: `backend/pgvector_api.py`

**Search Configuration**:
```python
# Similarity thresholds
SIMILARITY_THRESHOLD_INITIAL = 0.5      # Initial collection
SIMILARITY_THRESHOLD_STRICT = 0.7       # Final filtering
SIMILARITY_THRESHOLD_ENTITY_CHUNK = 0.65 # Entity chunk minimum

# Source limits
MAX_DB_SOURCES = 10                     # Max database sources in references
MAX_SOURCES_STRICT = 15                 # Hard limit during processing

# Relationship enhancement
RELATIONSHIP_BOOST_FACTOR = {
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
```

**Query Mode Configuration**:
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

### 7.2 Frontend Configuration

**File**: `frontend/src/components/tabs/QueryTab.ts`

**Citation Rendering**:
```typescript
// Convert HTML citations to markdown for display
content.replace(/<span class="citation-ref">\[(\d+)\]<\/span>/gi, '[$1]');

// Convert markdown italics for display
cleaned.replace(/<i>([\s\S]*?)<\/i>/gi, '*$1*');

// Convert markdown to HTML for print
processedText.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<i>$1</i>');
```

---

## 8. Best Practices

### 8.1 Search Mode Selection

| Query Type | Recommended Mode | Rationale |
|------------|-----------------|-----------|
| General knowledge | `smart` | Automatic strategy selection |
| Entity-focused | `entity-lookup` | Aggressive entity expansion |
| Relationship questions | `graph-traversal` | Deep graph exploration |
| Conceptual queries | `semantic` | Pure semantic matching |
| Technical terms | `semantic-hybrid` | Keyword + semantic boost |

### 8.2 Query Mode Selection

| Use Case | Recommended Mode | Expected Time |
|----------|-----------------|---------------|
| Quick lookup | `quick` | ~30 seconds |
| Standard research | `balanced` | ~60 seconds |
| Deep analysis | `comprehensive` | ~90 seconds |
| Academic paper | `ultra-deep` | ~120 seconds |

### 8.3 Citation Best Practices

1. **Always Enable LLM References**: `use_llm_references: true` for academic credibility
2. **Use Strict Similarity**: Keep `similarity_threshold: 0.7` for quality
3. **Mix Source Types**: Citations should alternate between DB and academic sources
4. **Verify Citations**: Check that citations in text match references section

---

## 9. Troubleshooting

### 9.1 Common Issues

**Issue**: Too few sources in references
- **Cause**: Similarity threshold too strict
- **Solution**: Lower threshold to 0.65 (not recommended) or improve source documents

**Issue**: Repeated citations
- **Cause**: LLM not following citation instructions
- **Solution**: Post-processing automatically fixes this; check `post_process_citations()`

**Issue**: Missing academic references
- **Cause**: `use_llm_references` set to false
- **Solution**: Set `use_llm_references: true` in request

**Issue**: Truncated responses
- **Cause**: Token limit reached
- **Solution**: All modes now use 8192 tokens (DeepSeek max); check for infinite loops

### 9.2 Performance Optimization

```python
# For faster responses:
{
    "mode": "semantic",           # Faster than smart
    "detail_level": "quick",       # Fewer sections
    "top_k": 5,                   # Fewer sources
    "stream": True                # Progressive display
}

# For better quality:
{
    "mode": "smart",              # Multi-layer search
    "detail_level": "comprehensive", # More detailed
    "similarity_threshold": 0.7,  # Strict quality
    "use_llm_references": True
}
```

---

## 10. Migration Guide

### From v1.x to v2.0-beta

**Breaking Changes**: None

**New Features**:
- `smart` search mode (recommended default)
- Relationship embedding enhancement on all modes
- Mode-specific academic reference counts
- Streaming for all query modes
- Strict similarity filtering (≥ 0.7)

**Deprecated**: None

**Recommended Updates**:
```python
# Old (still works)
{"query": "...", "mode": "semantic"}

# New (recommended)
{"query": "...", "mode": "smart", "detail_level": "balanced"}
```

---

## Appendix A: Complete Example

### Request
```bash
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the latest developments in high-bandwidth memory?",
    "mode": "smart",
    "detail_level": "comprehensive",
    "top_k": 10,
    "similarity_threshold": 0.7,
    "use_llm_references": true,
    "stream": true
  }'
```

### Response Structure
```html
<query-h1>What are the latest developments in high-bandwidth memory?</query-h1>

<query-h2>Executive Summary</query-h2>
<p>High-bandwidth memory (HBM) has emerged as a critical technology... 
<span class="citation-ref">[1]</span>. Recent advances in 3D stacking... 
<span class="citation-ref">[5]</span>. Academic research indicates... 
<span class="citation-ref">[11]</span>.</p>

<query-h2>1. Fundamental Concepts</query-h2>
<p>Introduction to HBM technology... <span class="citation-ref">[2]</span>.</p>

<query-h3>1.1 Architecture Overview</query-h3>
<p>HBM uses through-silicon vias (TSVs)... <span class="citation-ref">[1]</span> 
and <span class="citation-ref">[12]</span>.</p>

<!-- ... more sections ... -->

<query-h2>📚 References</query-h2>
<div class="references-list">
    <div class="reference-item"><span class="ref-number">[1]</span> HBM_Industry_Report_2024.pdf</div>
    <div class="reference-item"><span class="ref-number">[2]</span> Memory_Architecture_Survey.txt</div>
    <div class="reference-item"><span class="ref-number">[3]</span> JEDEC_HBM3_Specification.html</div>
    <!-- ... up to 10 DB sources -->
    
    <div class="reference-item"><span class="ref-number">[4]</span> Smith, J. D. (2023). <i>Advanced Memory Systems for AI</i>. <i>IEEE Computer Architecture Letters</i>, 22(4), 156-169.</div>
    <div class="reference-item"><span class="ref-number">[5]</span> Chen, W., Liu, Y., & Wang, M. (2024). High-bandwidth memory: A comprehensive survey. <i>ACM Computing Surveys</i>, 56(3), 1-35.</div>
    <!-- ... 14 academic references for comprehensive mode -->
</div>
```

---

*End of Documentation*
