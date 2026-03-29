# Search Mode Configuration

Updated search mode settings for Query and Query+File tabs.

## Mode Settings

### Quick Mode
- **Chunks**: 10
- **Answer Type**: standard
- **Estimated Time**: 30-60 sec
- **Timeout**: 2 minutes (120 seconds)

### Balanced Mode
- **Chunks**: 20
- **Answer Type**: standard
- **Estimated Time**: 30-60 sec
- **Timeout**: 2 minutes (120 seconds)

### Comprehensive Mode
- **Chunks**: 30
- **Answer Type**: comprehensive (2000+ words)
- **Estimated Time**: 2-4 min
- **Timeout**: 4 minutes (240 seconds)

### Ultra Deep Mode
- **Chunks**: 40
- **Answer Type**: ultra-extensive (3000+ words)
- **Estimated Time**: 3-5 min
- **Timeout**: 5 minutes (300 seconds)

## Display Message Format

```
<strong>{Mode} Mode</strong><br>
Retrieving {chunks} chunks + Generating {answer_type} answer...<br>
Estimated time: {estimated_time}<br>
<small>Please wait, do not close or refresh the page</small>
```

### Examples

**Quick Mode:**
```
Quick Mode
Retrieving 10 chunks + Generating standard answer...
Estimated time: 30-60 sec
Please wait, do not close or refresh the page
```

**Comprehensive Mode:**
```
Comprehensive Mode
Retrieving 30 chunks + Generating comprehensive (2000+ words) answer...
Estimated time: 2-4 min
Please wait, do not close or refresh the page
```

## Files Modified
- `QueryTab.ts` - Updated display message and timeout settings
- `QueryFileTab.ts` - Updated display message and timeout settings (3 locations)

## Build Status
✅ Frontend builds successfully
