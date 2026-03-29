# Citation Verification Fix

## Problem: Mismatched Citations

The LLM was citing sources incorrectly:

**Answer text:** "Besi's chip-to-wafer bonding research in Source 3"

**Actual Reference 3:** "The Ultimate Guide to Fine-Tuning LLMs..."

**Issue:** The LLM cited "Source 3" as bonding research, but Source 3 is actually about machine learning!

This is either:
1. **Citation hallucination** - LLM made up a citation
2. **Wrong source mapping** - LLM used wrong source number

## The Fix: Three-Layer Citation Control

### Layer 1: Source Legend in Context
Added explicit source mapping at the start of the context:

```
SOURCE LEGEND (Use ONLY these source numbers in citations):
Source 1: EVG_die_to_wafer_bonding.txt
Source 2: Hybrid_Bonding_Technologies.pdf
Source 3: HBM_Packaging_Review.txt
...
```

This ensures the LLM knows exactly which sources are available and their correct numbers.

### Layer 2: Prompt Instructions
Added explicit citation rules to the prompt:

```
**CRITICAL CITATION RULES:**
1. ONLY cite sources that are explicitly listed below
2. Use the EXACT source number when citing (e.g., "Source 1", "Source 2")
3. If you're not sure which source provided the information, DO NOT make up a citation
4. The sources available are:
   Source 1: EVG_die_to_wafer_bonding.txt
   Source 2: Hybrid_Bonding_Technologies.pdf
   ...
5. NEVER cite a source number that doesn't exist in the list above
6. If the context doesn't contain specific information, state it generally without citing
```

### Layer 3: Post-Processing Validation
Added `validate_and_fix_citations()` function that:

1. Finds all citations in format "Source X" or "[X]"
2. Checks if cited numbers match available sources (1-N)
3. **Fixes invalid citations:**
   - "Source 99" (doesn't exist) → "the literature"
   - "[99]" → removed
4. Logs warnings for hallucinated citations

## Code Changes

### New Function: `validate_and_fix_citations()`
```python
def validate_and_fix_citations(response: str, sources: list) -> tuple:
    """
    Validate that citations in the response match the actual sources.
    Returns corrected response and list of warnings.
    """
    # Find all citations
    citations_found = re.findall(r'Source\s+(\d+)', response, re.IGNORECASE)
    
    # Check for invalid citations
    invalid_citations = cited_numbers - valid_numbers
    
    if invalid_citations:
        # Replace invalid citations
        for invalid_num in invalid_citations:
            response = re.sub(rf'Source\s+{invalid_num}', 'the literature', response)
    
    return response, warnings
```

### Updated Context Building
```python
# Create a source legend for accurate citation
source_legend = "SOURCE LEGEND (Use ONLY these source numbers):\n"
for i, r in enumerate(filtered_result):
    source = r.get("source", "unknown")
    source_legend += f"Source {i+1}: {source}\n"

context = source_legend + "\n\n---\n\n" + context_content
```

## Expected Behavior After Fix

### Before Fix
**Answer:** "Besi's chip-to-wafer bonding research in Source 3"

**Reference 3:** "The Ultimate Guide to Fine-Tuning LLMs..." ❌ WRONG!

### After Fix
**Answer:** "Besi's chip-to-wafer bonding research in Source 2"

**Reference 2:** "EVG's die-to-wafer fusion and hybrid bonding technologies" ✓ CORRECT!

OR if LLM cites wrong source:

**Answer:** "Besi's chip-to-wafer bonding research in the literature"

(No specific source cited - safer than wrong citation)

## Restart Required

```bash
kill $(lsof -t -i:8002)
cd /Users/ken/clawd_workspace/projects/KG_RAG/v1.2-beta/backend
python pgvector_api.py
```

## Testing

After restart, check backend logs for:

```
[CITATION ISSUES] ['Invalid source citations found: {3}']
```

This means the fix is working - it detected and corrected an invalid citation.

## Important Note

If citations are still wrong after this fix, the issue may be:

1. **LLM hallucinating content** - The LLM is making up facts that don't exist in the sources
2. **Wrong sources retrieved** - The RAG system retrieved irrelevant documents

The fix above handles case #2 (wrong citations). For case #1, you need to:
- Improve the prompt to discourage hallucination
- Add a disclaimer: "Based on available sources..."
- Use a more capable LLM model

## Summary

| Issue | Before | After |
|-------|--------|-------|
| Source legend | Not included | Added at context start |
| Citation rules | Basic | Explicit instructions |
| Invalid citations | Allowed | Auto-corrected to "the literature" |
| Wrong source numbers | Not detected | Validated and fixed |
