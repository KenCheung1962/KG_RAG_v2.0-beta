# No Truncation Configuration

## Requirement
**NO ANSWER TRUNCATION** is a mandatory requirement for all search modes in both Query and Query+File tabs.

## Issue Fixed
Previously, answers were being truncated (e.g., "明確彰顯了王權的" - incomplete sentence).

## Root Cause
Multiple locations in the backend had low `max_tokens` settings:
- Main query handler: 3,200-8,000 tokens
- Section-by-section generation: 1,200 tokens per section
- Conclusion generation: 800 tokens
- Outline generation: 2,000 tokens
- Various defaults: 4,096 tokens

## Token Limits by Mode (FIXED)

| Mode | Token Limit | Word Target |
|------|-------------|-------------|
| **Quick** | 6,000 tokens | 600-1200 words |
| **Balanced** | 8,000 tokens | 1200-1800 words |
| **Comprehensive** | 12,000 tokens | 1800-2500 words |
| **Ultra Deep** | 16,000 tokens | 2500-3500 words |

## Files Modified

### Backend API (`backend/pgvector_api.py`)

| Line | Location | Old Value | New Value |
|------|----------|-----------|-----------|
| 1427 | Outline generation | 2,000 | 8,000 |
| 1439 | Fallback generation | 4,000 | 16,000 |
| 1498 | Section generation | 1,200 | 8,000 |
| 1537 | Conclusion generation | 800 | 4,000 |
| 2015 | Ultra Deep mode | 8,000 | 16,000 |
| 2020 | Comprehensive mode | 6,400 | 12,000 |
| 2025 | Balanced mode | 4,800 | 8,000 |
| 2030 | Quick mode | 3,200 | 6,000 |
| 2572 | LLM Knowledge Fallback | 4,096 | 16,000 |
| 2605 | Query+File Ultra Deep | 8,000 | 16,000 |
| 2607 | Query+File Comprehensive | 6,400 | 12,000 |
| 2609 | Query+File Balanced | 4,800 | 8,000 |
| 2611 | Query+File Quick | 3,200 | 6,000 |

### API Client (`backend/api_client.py`)

| Line | Function | Old Default | New Default |
|------|----------|-------------|-------------|
| 75 | `call_minimax()` | 1,024 | 16,000 |
| 281 | Synchronous wrapper | 1,024 | 16,000 |

### Unified Indexing (`unified_indexing/service.py`)

| Line | Location | Old Value | New Value |
|------|----------|-----------|-----------|
| 145 | DeepSeek API call | 2,000 | 16,000 |

### Unified Indexing (`unified_indexing/minimax_fixed.py`)

| Line | Function | Old Default | New Default |
|------|----------|-------------|-------------|
| 84 | `minimax_complete()` | 4,096 | 16,000 |
| 156 | `deepseek_complete()` | 4,096 | 16,000 |
| 541 | `llm_complete_with_provider()` | 4,096 | 16,000 |

## Technical Details

### Why These Limits?
- **Chinese characters**: ~1.5-2 tokens per character
- **English words**: ~1.3-1.5 tokens per word
- **Safety margin**: 2-3x the target word count to ensure NO truncation

### Example Calculation
For Ultra Deep mode (2500-3500 words):
- Conservative estimate: 3,500 words × 2 tokens/word = 7,000 tokens
- Safety margin: 7,000 × 2.3 = ~16,000 tokens
- Result: **16,000 tokens** ensures NO truncation even for maximum output

## Verification

To verify no truncation is occurring:
1. Run a query in any mode
2. Check that the response ends with complete sentences
3. Verify the Conclusion section is fully generated
4. Check the References section is complete
5. Ensure no sentence cuts off mid-word (e.g., "明確彰顯了王權的" should be "明確彰顯了王權的正當性" or complete sentence)

## API Timeout Considerations

Higher token limits may require longer timeouts:
- Quick/Balanced: 2 minutes
- Comprehensive: 4 minutes
- Ultra Deep: 5 minutes

These timeouts have been updated in the frontend to match the no-truncation requirements.
