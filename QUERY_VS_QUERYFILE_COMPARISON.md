# Query Mode vs Query+File Mode - Detailed Comparison

## Overview

| Aspect | Query Mode | Query+File Mode |
|--------|-----------|-----------------|
| **Endpoint** | `POST /api/v1/chat` | `POST /api/v1/chat/with-doc` |
| **Data Source** | Entire Knowledge Graph database | Uploaded files + Knowledge Graph database |
| **Use Case** | General knowledge queries | Document-specific questions with KG context |
| **File Upload** | Not required | Required (1+ files) |

---

## Workflow Comparison

### Query Mode Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         QUERY MODE WORKFLOW                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. USER INPUT                                                          │
│     ┌─────────────────────────────────────────┐                        │
│     │  Enter question in Query tab            │                        │
│     │  Example: "What is HBM?"                │                        │
│     └─────────────────────────────────────────┘                        │
│                          │                                              │
│                          ▼                                              │
│  2. SEARCH KNOWLEDGE GRAPH ONLY                                         │
│     ┌─────────────────────────────────────────┐                        │
│     │  • Generate query embedding             │                        │
│     │  • Vector search on ALL chunks          │                        │
│     │  • Rerank results                       │                        │
│     │  • Filter by relevance                  │                        │
│     └─────────────────────────────────────────┘                        │
│                          │                                              │
│                          ▼                                              │
│  3. BUILD CONTEXT                                                       │
│     ┌─────────────────────────────────────────┐                        │
│     │  Use top-k chunks from database         │                        │
│     │  (default: 15 chunks)                   │                        │
│     └─────────────────────────────────────────┘                        │
│                          │                                              │
│                          ▼                                              │
│  4. GENERATE RESPONSE                                                   │
│     ┌─────────────────────────────────────────┐                        │
│     │  LLM generates answer based on          │                        │
│     │  retrieved context from database        │                        │
│     └─────────────────────────────────────────┘                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Query+File Mode Workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      QUERY+FILE MODE WORKFLOW                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. USER INPUT                                                          │
│     ┌─────────────────────────────────────────┐                        │
│     │  Upload file(s) in Query+File tab       │                        │
│     │  Enter question about the file(s)       │                        │
│     │  Example: "Summarize this report"       │                        │
│     └─────────────────────────────────────────┘                        │
│                          │                                              │
│                          ▼                                              │
│  2. TWO-PHASE SEARCH                                                    │
│     ┌─────────────────────────────────────────┐                        │
│     │  PHASE 1: Search Uploaded Files         │                        │
│     │  ────────────────────────────────       │                        │
│     │  • Generate query embedding             │                        │
│     │  • Vector search on uploaded file       │
│     │    chunks ONLY                          │                        │
│     │  • Mark results as "source: uploaded"   │                        │
│     │  • Fallback: Direct SQL query if        │                        │
│     │    vector returns < 5 results           │                        │
│     └─────────────────────────────────────────┘                        │
│                          │                                              │
│                          ▼                                              │
│     ┌─────────────────────────────────────────┐                        │
│     │  PHASE 2: Search Knowledge Graph        │                        │
│     │  ────────────────────────────────       │                        │
│     │  • Vector search on entire database     │                        │
│     │  • Fill remaining context slots         │
│     │  • Mark results as "source: database"   │                        │
│     │  • Skip duplicates                      │                        │
│     └─────────────────────────────────────────┘                        │
│                          │                                              │
│                          ▼                                              │
│  3. COMBINED CONTEXT BUILDING                                           │
│     ┌─────────────────────────────────────────┐                        │
│     │  Merge results from BOTH sources:       │                        │
│     │  • Uploaded files (highest priority)    │                        │
│     │  • Knowledge graph (additional context) │                        │
│     │  Total: up to 50 chunks (Ultra mode)    │                        │
│     └─────────────────────────────────────────┘                        │
│                          │                                              │
│                          ▼                                              │
│  4. GENERATE RESPONSE                                                   │
│     ┌─────────────────────────────────────────┐                        │
│     │  LLM generates answer with context      │                        │
│     │  from both uploaded files AND           │                        │
│     │  existing knowledge base                │                        │
│     └─────────────────────────────────────────┘                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technical Differences

### Search Scope

| Aspect | Query Mode | Query+File Mode |
|--------|-----------|-----------------|
| **Primary Search** | Entire `chunks` table | Uploaded file chunks first |
| **Secondary Search** | Keyword fallback if no results | Knowledge graph fills remaining slots |
| **Chunk Limit** | 15-40 chunks (based on mode) | Up to 50 chunks (combined) |
| **Vector Threshold** | 0.2 (cosine similarity) | 0.2 for files, 0.3 for database |
| **Source Tracking** | Not applicable | Tracks "uploaded" vs "database" |

### Backend Implementation

#### Query Mode (`/api/v1/chat`)

```python
# Single-phase search
async def chat(request: dict):
    query = request.get("query") or request.get("message", "")
    
    # Generate embedding
    query_embedding = get_ollama_embedding(query)
    
    # Search ENTIRE database
    vector_results = await storage.search_chunks(
        query_vector=query_embedding,
        limit=initial_k,  # 40 chunks
        distance_metric=DistanceMetric.COSINE,
        match_threshold=0.2
    )
    
    # Rerank and filter
    result = await rerank_chunks(query, vector_results, ...)
    
    # Generate response
    return generate_llm_response(query, context, ...)
```

#### Query+File Mode (`/api/v1/chat/with-doc`)

```python
# Two-phase search
async def chat_with_doc(request: dict):
    message = request.get("message", "")
    filenames = request.get("filenames", [])  # Key difference!
    doc_ids = [hashlib.md5(f.encode()).hexdigest()[:12] for f in filenames]
    
    # PHASE 1: Search uploaded files
    file_results = []
    vector_results = await storage.search_chunks(
        query_vector=query_embedding,
        limit=30,
        distance_metric=DistanceMetric.COSINE
    )
    
    # Filter to only uploaded file chunks
    for r in vector_results:
        if r.metadata.get('doc_id') in doc_ids:
            file_results.append({"content": r.content, "source": "uploaded"})
    
    # Fallback: Direct SQL if few results
    if len(file_results) < 5:
        file_chunks = await storage.client.fetch(
            "SELECT content FROM chunks WHERE entity_id IN ($1, $2, ...)",
            *doc_ids
        )
    
    # PHASE 2: Search knowledge graph (fill remaining slots)
    remaining_slots = max_context_chunks - len(file_results)
    db_results = await storage.search_chunks(
        query_vector=query_embedding,
        limit=remaining_slots,
        match_threshold=0.3  # Higher threshold for DB
    )
    
    # Combine and deduplicate
    all_results = file_results + [{"content": r.content, "source": "database"} 
                                   for r in db_results]
    
    # Generate response
    return generate_llm_response(message, all_results, ...)
```

---

## Frontend Differences

### User Interface

| Aspect | Query Tab | Query+File Tab |
|--------|-----------|----------------|
| **File Upload** | ❌ No | ✅ Yes (required) |
| **Search Modes** | Semantic, Entity-lookup, Graph-traversal | Same modes |
| **Detail Levels** | Quick, Balanced, Comprehensive, Ultra | Same levels |
| **Default Action** | Search database immediately | Upload then search |
| **Duplicate Handling** | N/A | Prompt to overwrite or use existing |

### API Client Functions

```typescript
// Query Mode - client.ts
export async function sendQuery(request: QueryRequest): Promise<QueryResponse> {
  const resp = await fetchWithTimeout(
    buildUrl('/api/v1/chat'),  // <-- Different endpoint
    {
      method: 'POST',
      body: JSON.stringify(enhancedRequest)
    }
  );
}

// Query+File Mode - client.ts
export async function sendQueryWithFiles(
  request: QueryWithFilesRequest
): Promise<QueryResponse> {
  const resp = await fetchWithTimeout(
    buildUrl('/api/v1/chat/with-doc'),  // <-- Different endpoint
    {
      method: 'POST',
      body: JSON.stringify({
        ...enhancedRequest,
        filenames: request.filenames  // <-- Extra parameter
      })
    }
  );
}
```

---

## Context Building Comparison

### Query Mode Context

```
[Query: "What is HBM?"]

Context from Knowledge Graph (15 chunks):
[1] Source: memory_technology.pdf
    Content: "High Bandwidth Memory (HBM) is a..."
    
[2] Source: samsung_report_2024.pdf
    Content: "HBM3E offers 1.2 TB/s bandwidth..."
    
[3] Source: industry_overview.docx
    Content: "Compared to traditional DDR..."
    
    ... (12 more chunks from database)
```

### Query+File Mode Context

```
[Query: "Summarize this report"]
[Files: quarterly_report.pdf]

Context from TWO sources:

=== FROM UPLOADED FILE (Priority) ===
[1] Source: uploaded (quarterly_report.pdf)
    Content: "Q4 revenue increased by 25%..."
    
[2] Source: uploaded (quarterly_report.pdf)
    Content: "New product line launched..."
    
    ... (more chunks from uploaded file)

=== FROM KNOWLEDGE GRAPH (Additional Context) ===
[15] Source: database (market_analysis_2023.pdf)
     Content: "Industry trends show..."
     
[16] Source: database (competitor_report.pdf)
     Content: "Competitor X also reported..."
     
    ... (fills remaining slots with KG data)
```

---

## When to Use Each Mode

### Use Query Mode When:

✅ You want to search **all indexed documents** in the knowledge graph

✅ Your question is **general** and not tied to a specific document

✅ You want the **broadest possible context** from the entire database

✅ You haven't uploaded any new files recently

✅ You want **fastest response** (single-phase search)

**Example Questions:**
- "What is High Bandwidth Memory?"
- "Compare DDR5 and HBM3"
- "What companies manufacture AI chips?"

---

### Use Query+File Mode When:

✅ You have **specific documents** you want to query

✅ Your question relates to **content in uploaded files**

✅ You want **file-specific answers** with KG as supplementary context

✅ You need to analyze **new documents** not yet in the main database

✅ You want **cross-reference** between uploaded files and existing knowledge

**Example Questions:**
- "Summarize the key findings in this quarterly report"
- "What does this contract say about payment terms?"
- "Compare this product spec with our existing database"

---

## Performance Comparison

| Metric | Query Mode | Query+File Mode |
|--------|-----------|-----------------|
| **Search Time** | ~100-500ms | ~200-1000ms (two searches) |
| **Context Size** | 15-40 chunks | Up to 50 chunks (combined) |
| **Upload Overhead** | None | File upload time required |
| **Database Load** | Single query | Two queries + filtering |
| **Memory Usage** | Lower | Higher (tracks file sources) |

---

## Error Handling Differences

### Query Mode

```python
if not result:
    return {
        "response": "I couldn't find any information related to '{query}'. "
                    "Please try a different search term or upload relevant documents.",
        "sources": []
    }
```

### Query+File Mode

```python
if not result:
    if file_list:
        msg = (f"I couldn't find any information related to '{message}'. "
               f"Tried searching in uploaded files and database. "
               f"Try a different search term.")
    else:
        msg = (f"I couldn't find any information. "
               f"Please try a different search term or upload relevant documents.")
    return {
        "response": msg,
        "sources": []
    }
```

---

## Summary

| | Query Mode | Query+File Mode |
|---|---|---|
| **Best For** | General knowledge queries | Document-specific questions |
| **Data Source** | Knowledge graph only | Uploaded files + Knowledge graph |
| **Search Phases** | 1 phase | 2 phases (files first, then KG) |
| **File Upload** | Not needed | Required |
| **Context Priority** | All equal | Uploaded files prioritized |
| **Use Case** | "Tell me about X" | "What does this file say about X?" |

Both modes support the same **detail levels** (Quick, Balanced, Comprehensive, Ultra Deep) and **search modes** (Semantic, Entity-lookup, Graph-traversal), but Query+File mode provides **file-specific context** with **knowledge graph supplementation**.
