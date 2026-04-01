# LLM Configuration for File Upload - Implementation Summary

## Overview
This implementation makes the **Entity Extraction during file upload** respect the **LLM Provider settings** from the Configuration Tab. Previously, entity extraction was hardcoded to use MiniMax API only.

## Changes Made

### 1. Backend Changes (`pgvector_api.py`)

#### Added Import at Top of File (Lines 41-49)
```python
# Import LLM provider functions for configurable entity extraction
try:
    from minimax_fixed import llm_complete_with_provider
except ImportError:
    async def llm_complete_with_provider(*args, **kwargs):
        raise Exception("LLM provider module not available")
```

#### Updated `extract_entities_and_relations()` Function (Line ~534)
**Before:**
- Hardcoded to use `call_minimax()` function
- No configuration options

**After:**
- Accepts `llm_config` parameter with `provider` and `fallback_provider`
- Uses `llm_complete_with_provider()` which supports DeepSeek and MiniMax
- Supports automatic fallback if primary provider fails

#### Updated `upload_document_json()` Endpoint (Line ~808)
**Changes:**
- Extracts `llm_config` from request body
- Logs which provider is being used
- Passes `llm_config` to `extract_entities_and_relations()`

#### Updated `upload_folder_json()` Endpoint (Line ~1274)
**Changes:**
- Extracts `llm_config` from request body
- Passes `llm_config` to `process_single_file()`

#### Updated `process_single_file()` Function (Line ~1110)
**Changes:**
- Accepts `llm_config` parameter
- Passes `llm_config` to `extract_entities_and_relations()`

### 2. Frontend Changes

#### Updated `frontend/src/api/client.ts`

##### Added Helper Function
```typescript
function getEntityExtractionConfig(): LLMProviderConfig {
  const config = getLLMConfig();
  return {
    provider: config.entityExtraction.primary,
    fallback_provider: config.entityExtraction.fallback
  };
}
```

##### Updated `uploadDocument()` Function
**Changes:**
- Gets LLM config from Config Tab via `getEntityExtractionConfig()`
- Includes `llm_config` in request body

##### Updated `uploadFolder()` Function
**Changes:**
- Gets LLM config from Config Tab
- Includes `llm_config` in request body

#### Updated `backend/js/api.js` (Legacy JS Frontend)

##### Added Helper Function
```javascript
function getLLMConfigFromStorage() {
    // Reads from localStorage 'kg_rag_llm_config' set by Config Tab
    return {
        provider: config.entityExtraction?.primary || 'deepseek',
        fallback_provider: config.entityExtraction?.fallback || null
    };
}
```

##### Updated `uploadDocument()` Function
**Changes:**
- Gets LLM config from localStorage
- Includes `llm_config` in request body

## How It Works

### Configuration Flow
```
┌─────────────────────────────────────────────────────────────────┐
│  User sets LLM Provider in Config Tab                            │
│  (e.g., Entity Extraction: Primary=DeepSeek, Fallback=MiniMax)  │
└──────────────┬──────────────────────────────────────────────────┘
               │ Saves to localStorage: 'kg_rag_llm_config'
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  User uploads file(s)                                           │
└──────────────┬──────────────────────────────────────────────────┘
               │ Frontend reads config from localStorage
               │ Adds llm_config to upload request body
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Backend receives upload request with llm_config                │
└──────────────┬──────────────────────────────────────────────────┘
               │ Passes llm_config to extract_entities_and_relations()
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  Entity extraction uses configured LLM provider                 │
│  (DeepSeek or MiniMax based on user preference)                 │
└─────────────────────────────────────────────────────────────────┘
```

### API Request/Response Examples

#### Single File Upload
```json
// Request to POST /api/v1/documents/upload/json
{
  "content": "base64encodedcontent...",
  "id": "document.pdf",
  "content_type": "application/pdf",
  "llm_config": {
    "provider": "deepseek",
    "fallback_provider": "minimax"
  }
}
```

#### Folder Upload
```json
// Request to POST /api/v1/documents/upload/folder/json
{
  "folder_path": "/path/to/folder",
  "recursive": true,
  "skip_existing": true,
  "llm_config": {
    "provider": "deepseek",
    "fallback_provider": null
  }
}
```

## Testing

### Test Case 1: Upload with DeepSeek
1. Open Configuration Tab
2. Set "Entity Extraction" Primary to "DeepSeek"
3. Save configuration
4. Upload a file
5. Check backend logs - should show: `[Upload] Using LLM provider: deepseek`

### Test Case 2: Upload with MiniMax
1. Open Configuration Tab
2. Set "Entity Extraction" Primary to "MiniMax"
3. Save configuration
4. Upload a file
5. Check backend logs - should show: `[Upload] Using LLM provider: minimax`

### Test Case 3: Fallback
1. Set Primary to a provider that's not available
2. Set Fallback to the working provider
3. Upload should automatically use fallback

## Logging

The backend now logs which LLM provider is being used:
```
[Upload] Using LLM provider: deepseek (fallback: minimax)
[Upload] Extracted 12 entities, 8 relationships
[Folder Upload] Using LLM provider: deepseek
```

## Backward Compatibility

- If no `llm_config` is provided in request, defaults to `deepseek` (same as query endpoints)
- If `minimax_fixed` module fails to import, logs a warning and entity extraction will fail gracefully
- Legacy uploads without `llm_config` will use default configuration

## Files Modified

| File | Changes |
|------|---------|
| `backend/pgvector_api.py` | Added import, updated 4 functions |
| `frontend/src/api/client.ts` | Added helper, updated 2 functions |
| `backend/js/api.js` | Added helper, updated 1 function |

## Default Configuration

If no configuration is set in the Config Tab:
- **Primary Provider:** `deepseek`
- **Fallback Provider:** `null` (no fallback)

This matches the default configuration in the Config Tab:
```typescript
const DEFAULT_LLM_CONFIG = {
  entityExtraction: { primary: 'deepseek', fallback: 'minimax' },
  // ...
};
```
