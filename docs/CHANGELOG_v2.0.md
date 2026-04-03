# V2.0-Beta Changelog

> **Version**: 2.0-beta  
> **Release Date**: 2026-04-01  
> **Status**: Active Development

---

## Table of Contents

1. [Major Changes](#major-changes)
2. [Search Mode Updates](#search-mode-updates)
3. [Query Mode Updates](#query-mode-updates)
4. [Reference System Updates](#reference-system-updates)
5. [Citation System Updates](#citation-system-updates)
6. [Bug Fixes](#bug-fixes)
7. [Configuration Changes](#configuration-changes)
8. [Migration Guide](#migration-guide)

---

## Major Changes

### 1. Streaming Support for All Query Modes

**Change**: All query modes (Quick, Balanced, Comprehensive, Ultra-Deep) now support streaming responses.

**Before**:
- Quick/Balanced: Non-streaming, single response
- Comprehensive/Ultra-Deep: Streaming only

**After**:
- All modes: Full streaming support with progressive display

**Files Modified**:
- `backend/pgvector_api.py`
- `frontend/src/components/tabs/QueryTab.ts`

**API Impact**: None (backwards compatible)

---

### 2. Strict Similarity Filtering (≥ 0.7)

**Change**: All search modes now apply strict similarity filtering (≥ 0.7) for final source selection.

**Before**:
- Initial collection at ≥ 0.5
- No strict final filtering
- Source quality varied

**After**:
- Initial collection at ≥ 0.5
- Final strict filtering at ≥ 0.7
- Higher quality sources guaranteed

**Files Modified**:
- `backend/pgvector_api.py`

**Configuration**:
```python
SIMILARITY_THRESHOLD_STRICT = 0.7
```

---

### 3. Mode-Specific Academic Reference Counts

**Change**: Academic reference generation now varies by query mode.

**Before**:
- All modes: Fixed 12 academic references

**After**:
| Query Mode | Academic Refs |
|------------|--------------|
| Quick | 6 (5-8 range) |
| Balanced | 10 (8-12 range) |
| Comprehensive | 14 (12-16 range) |
| Ultra-Deep | 18 (16-20 range) |

**Files Modified**:
- `backend/pgvector_api.py`
  - `generate_ultra_response()` - Added `num_academic_refs` parameter
  - `generate_ultra_response_streaming()` - Added `num_academic_refs` parameter
  - All callers updated with mode-specific values

---

### 4. Reduced Entity Chunk Collection

**Change**: Reduced chunks collected per entity to improve relevance.

**Before**:
- `chunks_per_entity = 12`

**After**:
- `chunks_per_entity = 5`

**Rationale**: Prevents low-relevance entity chunks from diluting results.

**Files Modified**:
- `backend/pgvector_api.py`

---

### 5. Increased Database Source Limit

**Change**: Maximum database sources in references increased from 5 to 10.

**Before**:
- Max DB sources: 5

**After**:
- Max DB sources: 10

**Note**: Still requires similarity ≥ 0.7

**Files Modified**:
- `backend/pgvector_api.py`
  - Source list slicing changed from `[:5]` to `[:10]`

---

## Search Mode Updates

### SMART Mode Enhancements

**Changes**:
1. Added strict similarity filtering (≥ 0.7)
2. Reduced entity chunk collection (12 → 5 per entity)
3. Enhanced relationship embedding integration
4. Improved keyword boosting

**Configuration**:
```python
{
    "similarity_threshold": 0.7,
    "entity_boost_factor": 0.12,
    "max_entities": 8,
    "chunks_per_entity": 5
}
```

---

### SEMANTIC Mode Enhancements

**Changes**:
1. Strict similarity filtering (≥ 0.7)
2. Relationship embedding enhancement
3. Improved re-ranking

**Configuration**:
```python
{
    "similarity_threshold": 0.7,
    "entity_boost_factor": 0.10,
    "max_entities": 5
}
```

---

### SEMANTIC-HYBRID Mode

**New Mode**: Added as distinct mode from Semantic.

**Features**:
1. Vector similarity base
2. Keyword extraction and boosting
3. Relationship enhancement

**Configuration**:
```python
{
    "similarity_threshold": 0.7,
    "entity_boost_factor": 0.10,
    "max_entities": 6,
    "keyword_boost": 0.05
}
```

---

### ENTITY-LOOKUP Mode Enhancements

**Changes**:
1. Strict similarity filtering (≥ 0.7)
2. Reduced chunk collection per entity (12 → 5)
3. Aggressive entity expansion (max 8 entities)

**Configuration**:
```python
{
    "similarity_threshold": 0.7,
    "entity_boost_factor": 0.12,
    "max_entities": 8,
    "chunks_per_entity": 5
}
```

---

### GRAPH-TRAVERSAL Mode Enhancements

**Changes**:
1. Strict similarity filtering (≥ 0.7)
2. Relationship embedding as primary mechanism
3. Improved path tracking

**Configuration**:
```python
{
    "similarity_threshold": 0.7,
    "max_depth": 2,
    "entity_boost_factor": 0.08,
    "max_relationships": 8
}
```

---

## Query Mode Updates

### All Query Modes

**Changes**:
1. Streaming support for all modes
2. Mode-specific academic reference counts
3. Consistent 8192 token limit (DeepSeek max)
4. APA 7th edition reference formatting

---

### QUICK Mode

**Configuration**:
```python
{
    "target_words": "600-1200",
    "num_sections": 3,
    "num_subsections": 2,
    "num_academic_refs": 6,      # NEW: Mode-specific
    "max_tokens": 8192,
    "streaming": True            # NEW: Streaming support
}
```

---

### BALANCED Mode

**Configuration**:
```python
{
    "target_words": "1500-2000",
    "num_sections": 4,
    "num_subsections": 3,
    "num_academic_refs": 10,     # NEW: Mode-specific
    "max_tokens": 8192,
    "streaming": True            # NEW: Streaming support
}
```

---

### COMPREHENSIVE Mode

**Configuration**:
```python
{
    "target_words": "1800-2500",
    "num_sections": 5,
    "num_subsections": 3,
    "num_academic_refs": 14,     # NEW: Mode-specific
    "max_tokens": 8192,
    "streaming": True            # Existing
}
```

---

### ULTRA-DEEP Mode

**Configuration**:
```python
{
    "target_words": "2500-3500",
    "num_sections": 7,
    "num_subsections": 3,
    "num_academic_refs": 18,     # NEW: Mode-specific
    "max_tokens": 8192,
    "streaming": True            # Existing
}
```

---

## Reference System Updates

### Dual-Source Reference System

**Implementation**: References now come from two sources:

1. **Database Sources** (Actual Documents)
   - Up to 10 sources
   - Similarity ≥ 0.7 required
   - Numbered [1] to [N]

2. **LLM Academic References** (Generated)
   - Mode-specific count (6, 10, 14, or 18)
   - APA 7th edition format
   - Numbered [N+1] onwards

**Files Modified**:
- `backend/pgvector_api.py`
  - `generate_llm_academic_references()` - Enhanced for mode-specific counts
  - Reference section assembly updated

---

### APA 7th Edition Formatting

**Implementation**: LLM academic references now use proper APA format.

**Formats**:
```
Journal Article:
Smith, J. D., & Jones, M. A. (2023). Title of article. <i>Journal Name</i>, 15(2), 45-67. https://doi.org/xx.xxx

Book:
Chen, W. (2024). <i>Book Title: Subtitle</i> (2nd ed.). Publisher.

Conference Paper:
Johnson, R. et al. (2022). Paper title. In <i>Conference Proceedings</i> (pp. 123-145). IEEE.
```

---

## Citation System Updates

### In-Text Citation Format

**Standard Format**:
```html
<span class="citation-ref">[N]</span>
```

### Citation Post-Processing

**New Function**: `post_process_citations()`

**Purpose**: Fix repeated citations by alternating between DB and academic sources.

**Example**:
```
Input:  "...[1]... [1]... [1]..."
Output: "...[1]... [N+1]... [2]..."
```

**Files Modified**:
- `backend/pgvector_api.py`

---

### Citation Requirements

**Executive Summary & Conclusion**:
- Minimum 8 different sources
- Must mix DB sources [1-N] and academic refs [N+1 onwards]
- No consecutive repeats

**Subsections**:
- 3-5 citations per subsection
- Varied sources

---

## Bug Fixes

### 1. Smart Search Source Relevance

**Issue**: Smart search returned too many low-relevance sources.

**Fix**: 
- Implemented strict filtering (similarity ≥ 0.7)
- Reduced entity chunk collection (12 → 5)

**Result**: Higher quality source selection.

---

### 2. Streaming for Quick/Balanced Modes

**Issue**: Quick and Balanced modes returned 400 error for streaming requests.

**Fix**: 
- Unified streaming handler for all modes
- All modes now use `chat_stream()` endpoint

**Result**: Consistent streaming across all query modes.

---

### 3. Citation Repetition

**Issue**: LLM would cite the same source repeatedly (e.g., [1], [1], [1]).

**Fix**:
- Added `post_process_citations()` function
- Automatic alternation between DB and academic sources

**Result**: Varied citations throughout content.

---

### 4. Missing Academic References

**Issue**: References section sometimes showed only database sources.

**Fix**:
- Enhanced reference generation pipeline
- Guaranteed academic reference inclusion
- Mode-specific counts implemented

**Result**: Complete references section with both source types.

---

### 5. Italic Rendering in References

**Issue**: APA italics not rendering correctly in display and print.

**Fix**:
- Frontend converts `<i>` to `*text*` for display
- Print converts `*text*` back to `<i>` for proper rendering
- Consistent markdown-based approach

**Result**: Proper italic rendering for journal names and titles.

---

## Configuration Changes

### Backend Configuration

**File**: `backend/pgvector_api.py`

**New/Updated Constants**:
```python
# Similarity thresholds
SIMILARITY_THRESHOLD_STRICT = 0.7       # NEW
SIMILARITY_THRESHOLD_ENTITY_CHUNK = 0.65 # NEW

# Source limits
MAX_DB_SOURCES = 10                     # UPDATED (was 5)
MAX_SOURCES_PROCESSING = 15

# Entity collection
CHUNKS_PER_ENTITY = 5                   # UPDATED (was 12)

# Mode-specific academic references
ACADEMIC_REFS_QUICK = 6                 # NEW
ACADEMIC_REFS_BALANCED = 10             # NEW
ACADEMIC_REFS_COMPREHENSIVE = 14        # NEW
ACADEMIC_REFS_ULTRA_DEEP = 18           # NEW
```

---

### Frontend Configuration

**File**: `frontend/src/components/tabs/QueryTab.ts`

**New Handling**:
```typescript
// Display: HTML to markdown
content.replace(/<i>([\s\S]*?)<\/i>/gi, '*$1*');

// Print: Markdown to HTML
processedText
  .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  .replace(/\*([^*]+)\*/g, '<i>$1</i>');
```

---

## Migration Guide

### From v1.x to v2.0-beta

**Breaking Changes**: None

**New Features**:
- Smart search mode (recommended default)
- Streaming for all query modes
- Mode-specific academic reference counts
- Strict similarity filtering (≥ 0.7)
- Dual-source reference system
- APA 7th edition formatting

**Recommended Updates**:

#### 1. Update API Calls (Optional)

**Old** (still works):
```json
{
  "query": "What is AI?",
  "mode": "semantic"
}
```

**New** (recommended):
```json
{
  "query": "What is AI?",
  "mode": "smart",
  "detail_level": "balanced",
  "similarity_threshold": 0.7,
  "use_llm_references": true
}
```

#### 2. Enable Streaming

All modes now support streaming:
```json
{
  "query": "What is AI?",
  "stream": true
}
```

#### 3. Select Appropriate Query Mode

| Use Case | Recommended Mode |
|----------|-----------------|
| Quick lookup | `quick` |
| Standard research | `balanced` (default) |
| Deep analysis | `comprehensive` |
| Academic paper | `ultra-deep` |

---

## Files Modified Summary

### Backend

| File | Changes |
|------|---------|
| `backend/pgvector_api.py` | Major refactoring for all features |

**Key Functions Added/Modified**:
- `search_smart()` - Added strict filtering
- `generate_ultra_response()` - Added `num_academic_refs` parameter
- `generate_ultra_response_streaming()` - Added `num_academic_refs` parameter
- `generate_llm_academic_references()` - Mode-specific counts
- `post_process_citations()` - Citation fixing
- `chat_stream()` - Unified streaming handler

### Frontend

| File | Changes |
|------|---------|
| `frontend/src/components/tabs/QueryTab.ts` | Citation rendering, streaming display, print formatting |

---

## Documentation

### New Documentation Files

| File | Description |
|------|-------------|
| `docs/V2_SEARCH_QUERY_MODES_REFERENCE.md` | Complete reference guide |
| `docs/QUICK_REFERENCE.md` | Quick reference card |
| `docs/CHANGELOG_v2.0.md` | This changelog |

### Updated Documentation Files

| File | Description |
|------|-------------|
| `docs/SEARCH_MODES_SUMMARY.md` | Updated with query modes and reference system |
| `docs/CONSOLIDATED_SEARCH_MODES.md` | Updated with latest changes |

---

## Testing Checklist

### Search Modes
- [ ] Smart mode returns 5-10 high-quality sources
- [ ] All modes apply similarity ≥ 0.7 filtering
- [ ] Entity chunk collection limited to 5 per entity
- [ ] Relationship enhancement works across all modes

### Query Modes
- [ ] Quick mode generates ~600-1200 words
- [ ] Balanced mode generates ~1500-2000 words
- [ ] Comprehensive mode generates ~1800-2500 words
- [ ] Ultra-Deep mode generates ~2500-3500 words
- [ ] All modes stream correctly

### Reference System
- [ ] Database sources limited to 10
- [ ] Academic references match mode-specific counts
- [ ] APA formatting correct (italics for journals/books)
- [ ] Numbering continues correctly [1-N] then [N+1 onwards]

### Citation System
- [ ] Citations use `<span class="citation-ref">[N]</span>` format
- [ ] No repeated consecutive citations
- [ ] Mix of DB and academic sources in content
- [ ] Citations match references section

---

## Future Roadmap

### Planned for v2.1
- [ ] Citation verification against actual source content
- [ ] User feedback loop for reference quality
- [ ] Custom citation styles (MLA, Chicago, etc.)
- [ ] Reference export (BibTeX, RIS)

### Planned for v2.2
- [ ] Multi-language reference support
- [ ] Automatic DOI resolution
- [ ] Citation impact metrics
- [ ] Reference similarity clustering

---

*End of Changelog*
