# Source Relevance Fix

## Problem
The system was returning completely irrelevant sources in the Reference section. For example:
- Query: "How to realise thermal compression bonding for COWOS package"
- Sources returned: Math books, statistics textbooks, software engineering docs

These sources had NO relevant content about COWOS, thermal compression bonding, or semiconductor packaging.

## Solution
Added content-based relevance filtering to verify that retrieved chunks actually contain query-related content.

### Changes Made

#### 1. Added `is_chunk_content_relevant()` Function
```python
def is_chunk_content_relevant(content: str, query: str, min_matches: int = 2) -> bool:
    """
    Check if chunk content actually contains relevant keywords from query.
    Returns True if content has at least min_matches query keywords.
    """
```

This function:
- Extracts keywords from the query (4+ characters, excluding stop words)
- Counts how many query keywords appear in the chunk content
- Returns True only if at least 2 keywords match (configurable)
- Logs debug information when content is filtered out

#### 2. Modified Chunk Filtering
In the chat endpoint, added content relevance check after box-character filtering:

```python
for r in result:
    content = r.get("content", "")
    # ... existing box-char filtering ...
    
    # NEW: Check if content is actually relevant to query
    is_rel, match_count, matched_terms = is_chunk_content_relevant(content, query, min_matches=2)
    if not is_rel:
        print(f"[FILTER] Skipping chunk from {r.get('source', 'unknown')} - content not relevant")
        continue
    
    filtered_result.append(r)
```

#### 3. Added Debug Logging
The system now logs:
- Which sources are being retrieved
- Which sources are filtered out as irrelevant
- Keyword matching details

#### 4. Source Relevance Warning
If all retrieved sources are irrelevant, the response includes a warning:
```
**Note:** The retrieved source documents may not be highly relevant to your query. 
Consider uploading documents specifically about this topic.
```

## Result

### Before Fix
```
References

1. 2015_Book_Object-OrientedAnalysisDesignA.txt
2. INTRODUCTION TO PROBABILITY AND STATISTICS FOR ENGINEERS AND SCIENTISTS.txt
3. Graph Theory with Applications - BondyMurty.txt
4. ... (math books, etc.)
```

### After Fix
```
References

1. COWOS_Packaging_Technology.pdf        ✓ Relevant
2. Thermal_Compression_Bonding_2023.txt  ✓ Relevant

OR if no relevant documents exist:

References

(No relevant sources found)
```

## Restart Required

To apply the fix:

```bash
# 1. Kill existing backend
kill $(lsof -t -i:8002)

# 2. Start updated backend
cd /Users/ken/clawd_workspace/projects/KG_RAG/v1.2-beta/backend
python pgvector_api.py
```

## How It Works

1. User queries: "thermal compression bonding for COWOS package"
2. System extracts keywords: `["thermal", "compression", "bonding", "cowos", "package"]`
3. Vector search retrieves candidate chunks
4. For each chunk:
   - Check if chunk content contains at least 2 query keywords
   - If yes: include in filtered_result
   - If no: skip (log the skip reason)
5. Only sources with relevant chunks are included in References section

## Important Note

If your database doesn't contain any documents about COWOS, thermal compression bonding, or semiconductor packaging, the system will now return:
- Either no sources (clean)
- Or a message saying no relevant information found

This is the **correct behavior** - it's better to admit no relevant data exists than to cite irrelevant math textbooks!
