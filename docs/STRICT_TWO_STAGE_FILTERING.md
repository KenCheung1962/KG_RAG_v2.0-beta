# Strict Two-Stage Source Filtering

## Problem Still Occurring

Query: "How to realise the hybrid bonding in advanced packaging process"

Still getting IRRELEVANT references:
1. 2015_Book_Object-OrientedAnalysisDesignA.txt ❌ (Software engineering)
2. Guide to the Software Engineering Body of Knowledge -v4.txt ❌ (Software engineering)
3. EVG's die-to-wafer fusion and hybrid bonding technologies.txt ✓ (RELEVANT)
4. Recess Effect Study and Process Optimization of Sub-10 μm Pitch Die-to-wafer.txt ✓ (RELEVANT)
5. Software-Fundamentals of Software Architecture.txt ❌ (Software engineering)

**3 out of 5 are still software engineering books!**

## The New Fix: Two-Stage Strict Filtering

### Stage 1: Filename Check (NEW)
**Source filename MUST contain at least one query keyword or domain term**

```python
def is_source_filename_relevant(source: str, query: str) -> bool:
    # Extract keywords from query
    query_keywords = ['hybrid', 'bonding', 'packaging', 'advanced', ...]
    
    # Check if ANY keyword appears in filename
    for keyword in query_keywords:
        if keyword in source.lower():
            return True  # PASSED
    
    # Check domain-specific terms
    packaging_terms = ['package', 'chip', 'die', 'wafer', 'hbm', 'cowos', ...]
    bonding_terms = ['bond', 'hybrid', 'thermal', 'fusion', ...]
    
    for term in all_terms:
        if term in source.lower():
            return True  # PASSED
    
    return False  # REJECTED - no match in filename
```

**Example Results:**
- "Object-OrientedAnalysisDesignA.txt" → **REJECTED** (no packaging/bonding keywords)
- "Software Engineering Body of Knowledge.txt" → **REJECTED** (no packaging/bonding keywords)
- "EVG's die-to-wafer fusion and hybrid bonding technologies.txt" → **PASSED** (contains "hybrid", "bonding", "wafer")
- "Recess Effect Study of Die-to-wafer.txt" → **PASSED** (contains "die", "wafer")
- "Software Architecture.txt" → **REJECTED** (no packaging/bonding keywords)

### Stage 2: Content Check (EXISTING)
**Chunk content MUST contain at least 2 critical technical terms**

Already implemented - requires specific technical content matches.

## Filter Flow

```
Retrieved Chunk
      ↓
[Filename Check]
      ↓
Does filename contain query keywords or domain terms?
   YES → Continue to content check
   NO  → REJECT immediately (don't even check content)
      ↓
[Content Check]
      ↓
Does content contain 2+ critical technical terms?
   YES → ACCEPT
   NO  → REJECT
```

## Why This Works

### Software Books Get Rejected at Stage 1

| Source Filename | Query Keywords Found? | Domain Terms Found? | Result |
|----------------|----------------------|---------------------|--------|
| Object-OrientedAnalysisDesignA.txt | "oriented", "analysis", "design" (generic) | NONE | ❌ REJECTED |
| Software Engineering Body of Knowledge.txt | "software", "engineering", "knowledge" (generic) | NONE | ❌ REJECTED |
| Software Architecture.txt | "software", "architecture" (generic) | NONE | ❌ REJECTED |

### Packaging Docs Pass Stage 1

| Source Filename | Keywords Found | Result |
|----------------|----------------|--------|
| EVG's die-to-wafer fusion and hybrid bonding technologies.txt | "die", "wafer", "hybrid", "bonding" | ✓ PASSED |
| Recess Effect Study of Die-to-wafer.txt | "die", "wafer" | ✓ PASSED |
| HBM_Summary.txt | "hbm" | ✓ PASSED |

## Restart Backend

**MUST RESTART for changes to take effect!**

```bash
kill $(lsof -t -i:8002)
cd /Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta/backend
python pgvector_api.py
```

## Expected Log Output

When filtering works, you'll see:

```
[FILENAME FILTER] REJECTED: '2015_Book_Object-OrientedAnalysisDesignA.txt' - no query keywords in filename
[FILENAME FILTER] REJECTED: 'Guide to the Software Engineering Body of Knowledge -v4.txt' - no query keywords in filename
[FILENAME FILTER] PASSED: 'EVG's die-to-wafer fusion and hybrid bonding technologies.txt' - matched keyword: 'hybrid'
[FILENAME FILTER] PASSED: 'Recess Effect Study and Process Optimization of Sub-10 μm Pitch Die-to-wafer .txt' - matched keyword: 'wafer'
[FILENAME FILTER] REJECTED: 'Software-Fundamentals of Software Architecture.txt' - no query keywords in filename
```

## Expected Final References

```
References

1. EVG's die-to-wafer fusion and hybrid bonding technologies.txt
2. Recess Effect Study and Process Optimization of Sub-10 μm Pitch Die-to-wafer.txt
```

**Only 2 relevant sources!** The 3 software books are filtered out.

## Important Notes

### If ALL Sources Get Filtered Out

If after strict filtering you get:
```
References

(No relevant sources found)
```

This means your database has **NO documents** containing packaging/bonding keywords in their filenames.

**Solution: Upload relevant documents with descriptive filenames like:**
- `Semiconductor_Packaging_HBM.txt`
- `Hybrid_Bonding_Thermal_Compression.pdf`
- `COWOS_Integration_Technologies.html`

### Filename Matters!

The system now heavily relies on filenames. Make sure uploaded documents have descriptive names that include:
- Topic keywords ("bonding", "packaging", "hbm", etc.)
- Technical terms ("die", "wafer", "chip", "tsv", etc.)
- NOT generic names like "document1.txt" or "paper.pdf"
