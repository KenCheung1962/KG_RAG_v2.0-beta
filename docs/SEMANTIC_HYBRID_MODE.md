# Semantic-Hybrid Mode: Vector + Keyword Search

## Overview

**Semantic-Hybrid** is an enhanced version of the default Semantic search that combines:
- **Vector similarity** (semantic understanding)
- **High-level keyword matching** (concept precision)

This creates a powerful hybrid search that understands meaning AND prioritizes specific concepts mentioned in the query.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                      Semantic-Hybrid Flow                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: LLM Keyword Extraction                                  │
│                                                                 │
│ Query: "What are the benefits of renewable energy?"            │
│                                                                 │
│ High-Level Keywords: ["benefits", "renewable energy",           │
│                       "advantages", "sustainability"]           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: Vector Search (Semantic)                                │
│                                                                 │
│ Retrieve top 2× chunks using vector similarity                   │
│ (Standard semantic search on 768-dim embeddings)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: Keyword Boosting                                        │
│                                                                 │
│ For each chunk, check if it contains high-level keywords        │
│                                                                 │
│ Match "benefits" in chunk → +0.15 score                         │
│ Match "renewable" in chunk → +0.15 score                        │
│                                                                 │
│ Boosted chunks re-ranked higher                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: Return Top-K Results                                    │
│                                                                 │
│ Return best chunks combining semantic + keyword relevance       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Comparison of Search Modes

| Mode | Vector Search | Keywords Used | Best For |
|------|--------------|---------------|----------|
| **semantic** (default) | ✅ Pure | ❌ None | General questions where meaning matters most |
| **semantic-hybrid** | ✅ + Boost | ✅ High-level | Questions with important concepts to match |
| **entity-lookup** | ✅ | ✅ Low-level | Specific entity-focused questions |
| **graph-traversal** | ✅ | ✅ Both | Relationship and overview questions |

---

## When to Use Semantic-Hybrid

### ✅ Use Semantic-Hybrid When:

1. **Query contains important concepts**
   - *"What are the **economic benefits** of electric vehicles?"*
   - Keywords: ["economic", "benefits"] boost relevant chunks

2. **Need both meaning AND specific terms**
   - *"How does **machine learning** improve **healthcare diagnostics**?"*
   - Ensures chunks mention both concepts

3. **Precision matters**
   - *"What are **environmental impacts** of **solar power**?"*
   - Boosts chunks specifically about environmental aspects

### ✅ Use Default Semantic When:

1. **Broad conceptual questions**
   - *"Tell me about climate change"*
   - Pure semantic search works well

2. **Conversational queries**
   - *"How does this work?"*
   - No specific concepts to boost

---

## API Usage

### Request

```http
POST /api/v1/chat
Content-Type: application/json

{
  "query": "What are the benefits of renewable energy?",
  "mode": "semantic-hybrid",
  "top_k": 10,
  "llm_config": {
    "provider": "deepseek",
    "fallback_provider": "minimax"
  }
}
```

### Response

```json
{
  "response": "Renewable energy offers several significant benefits...",
  "sources": ["document1.pdf", "document2.pdf"],
  "context": "...",
  "confidence": 0.85
}
```

---

## Implementation Details

### Keyword Extraction

Uses the same LLM-based extraction as other modes:
- **Provider**: DeepSeek (primary), MiniMax (fallback)
- **Temperature**: 0.3 (consistent output)
- **Extracts**: 2-5 high-level keywords

### Boost Formula

```python
# Original score from vector similarity
original_score = chunk.similarity  # 0.0 - 1.0

# Count keyword matches in chunk content
keyword_matches = sum(1 for kw in hl_keywords if kw in content)

# Apply boost (+0.15 per match, capped at 1.0)
boosted_score = min(1.0, original_score + (0.15 * keyword_matches))
```

### Boost Amount

| Matches | Boost | Example |
|---------|-------|---------|
| 1 keyword | +0.15 | 0.72 → 0.87 |
| 2 keywords | +0.30 | 0.65 → 0.95 |
| 3+ keywords | +0.45 (capped) | 0.60 → 1.00 |

---

## Example Walkthrough

### Query: "What are the economic benefits of solar power?"

**Step 1: Extract Keywords**
```python
hl_keywords = ["economic", "benefits", "solar power", "financial"]
```

**Step 2: Vector Search Results**
| Chunk | Vector Score | Content Snippet |
|-------|--------------|-----------------|
| A | 0.82 | "Solar panels convert sunlight to electricity..." |
| B | 0.78 | "The **economic benefits** of **solar power** include..." |
| C | 0.75 | "Installing **solar** systems provides **financial** returns..." |
| D | 0.71 | "Renewable **energy** sources are becoming cheaper..." |

**Step 3: Apply Keyword Boosts**
| Chunk | Original | Matches | Boosted | Change |
|-------|----------|---------|---------|--------|
| A | 0.82 | 0 | 0.82 | - |
| B | 0.78 | 2 ("economic", "solar power") | 1.00 | +0.22 |
| C | 0.75 | 2 ("solar", "financial") | 1.00 | +0.25 |
| D | 0.71 | 0 | 0.71 | - |

**Step 4: Re-ranked Results**
1. Chunk B (1.00) - Most relevant
2. Chunk C (1.00) - Most relevant
3. Chunk A (0.82) - Semantically similar
4. Chunk D (0.71) - General renewable energy

---

## Metadata Tags

Chunks returned by semantic-hybrid include metadata:

```json
{
  "chunk_id": "doc_123_45",
  "content": "...",
  "similarity": 0.95,
  "metadata": {
    "keyword_boosted": true,
    "matched_keywords": ["economic", "benefits"],
    "original_similarity": 0.65
  }
}
```

| Field | Description |
|-------|-------------|
| `keyword_boosted` | True if chunk was boosted |
| `matched_keywords` | List of keywords found in chunk |
| `original_similarity` | Score before boosting |

---

## Performance

| Aspect | Details |
|--------|---------|
| **Latency** | +50-100ms vs pure semantic (LLM extraction) |
| **Quality** | Higher precision for concept-heavy queries |
| **Fallback** | Falls back to pure semantic if LLM fails |
| **Cache** | Keywords cached per query |

---

## Configuration

### Adjust Boost Strength

Edit `search_semantic_hybrid()` in `pgvector_api.py`:

```python
# Default: 0.15 per keyword match
keyword_boost: float = 0.15

# Stronger boost (0.20 = +20% per match)
keyword_boost: float = 0.20

# Weaker boost (0.10 = +10% per match)
keyword_boost: float = 0.10
```

### Disable Keyword Boosting

Use default `semantic` mode instead - no keywords extracted.

---

## Testing

### Test Semantic-Hybrid

```bash
curl -X POST http://localhost:8002/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the environmental impacts of electric vehicles?",
    "mode": "semantic-hybrid",
    "top_k": 5
  }'
```

### Compare Modes

```bash
# Pure semantic
curl -X POST http://localhost:8002/api/v1/chat \
  -d '{"query": "economic benefits of AI", "mode": "semantic"}'

# Hybrid (with keyword boost)
curl -X POST http://localhost:8002/api/v1/chat \
  -d '{"query": "economic benefits of AI", "mode": "semantic-hybrid"}'
```

---

## Summary

**Semantic-Hybrid** gives you the best of both worlds:
- ✅ **Semantic understanding** from vector search
- ✅ **Keyword precision** from high-level concept matching
- ✅ **Configurable boost** strength
- ✅ **Automatic fallback** on errors

Use it when your queries contain important concepts that should be prioritized in the results!
