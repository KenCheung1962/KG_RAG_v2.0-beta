# V2.0-Beta Quick Reference Guide

## Search Modes (How to Retrieve)

| Mode | Key Feature | Use When |
|------|-------------|----------|
| `smart` | Multi-layer fusion (default) | All queries - automatic selection |
| `semantic` | Pure vector similarity | General conceptual questions |
| `semantic-hybrid` | Vector + keywords | Technical terms matter |
| `entity-lookup` | Entity-centric + expansion | Query mentions specific entities |
| `graph-traversal` | BFS graph exploration | Relationship/network questions |

## Query Modes (How to Respond)

| Mode | Words | Sections | Academic Refs | Time |
|------|-------|----------|---------------|------|
| `quick` | 600-1200 | 3 | 6 (5-8 range) | ~30s |
| `balanced` | 1500-2000 | 4 | 10 (8-12 range) | ~60s |
| `comprehensive` | 1800-2500 | 5 | 14 (12-16 range) | ~90s |
| `ultra-deep` | 2500-3500 | 7 | 18 (16-20 range) | ~120s |

## Key Thresholds

```python
# Similarity thresholds
INITIAL_COLLECTION = 0.5      # First pass collection
STRICT_FILTERING = 0.7        # Final quality filter
ENTITY_CHUNK_MIN = 0.65       # Entity context chunks

# Source limits
MAX_DB_SOURCES = 10           # Database sources in refs
MAX_PROCESSING = 15           # Internal processing limit

# Entity expansion
SMART_MAX_ENTITIES = 8        # Smart mode expansion
ENTITY_MAX_ENTITIES = 8       # Entity-lookup expansion
SEMANTIC_MAX_ENTITIES = 5     # Semantic mode expansion
```

## API Quick Start

```bash
# Default search (smart + balanced)
curl -X POST http://localhost:8002/api/v1/chat \
  -d '{"query": "your question here"}'

# Specific modes
curl -X POST http://localhost:8002/api/v1/chat \
  -d '{
    "query": "your question",
    "mode": "smart",
    "detail_level": "comprehensive",
    "top_k": 10,
    "similarity_threshold": 0.7,
    "use_llm_references": true
  }'
```

## Reference Generation

```
Total References = DB Sources (≤10) + Academic Refs (mode-specific)

Numbering:
[1] to [N]          → Database sources (actual documents)
[N+1] to [N+X]      → LLM academic references (APA format)

Example (Balanced mode with 3 DB sources):
[1] Document_A.txt
[2] Document_B.pdf
[3] Document_C.html
[4] Smith, J. (2023). <i>Title</i>. <i>Journal</i>.
[5] Chen, W. et al. (2024). <i>Title</i>. <i>Journal</i>.
...
[13] Academic reference #10
```

## Citation Format

```html
<!-- In-text citation -->
<span class="citation-ref">[N]</span>

<!-- Example -->
<p>Research shows HBM improves performance <span class="citation-ref">[1]</span>. 
Academic studies confirm <span class="citation-ref">[4]</span>.</p>
```

## Common Configurations

```python
# Fastest response
{
    "mode": "semantic",
    "detail_level": "quick",
    "top_k": 5
}

# Best quality (default)
{
    "mode": "smart",
    "detail_level": "balanced",
    "similarity_threshold": 0.7,
    "use_llm_references": true
}

# Maximum detail
{
    "mode": "smart",
    "detail_level": "ultra-deep",
    "similarity_threshold": 0.7,
    "use_llm_references": true
}
```

## Response Structure

```json
{
  "type": "content",
  "section": "executive_summary|section_N|conclusion|references",
  "content": "<query-h2>Title</query-h2><p>Content...</p>",
  "progress": 15
}
```

## File Locations

| Component | File |
|-----------|------|
| Search pipeline | `backend/pgvector_api.py` |
| Query processing | `backend/pgvector_api.py` |
| Reference generation | `backend/pgvector_api.py` |
| Frontend display | `frontend/src/components/tabs/QueryTab.ts` |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Too few sources | Check similarity_threshold (default 0.7) |
| Missing academic refs | Set use_llm_references: true |
| Repeated citations | Post-processing auto-fixes this |
| Slow responses | Use quick mode or semantic mode |
| Truncated output | All modes use 8192 tokens (DeepSeek max) |
