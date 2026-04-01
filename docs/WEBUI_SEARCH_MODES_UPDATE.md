# WebUI Search Modes Update

## Summary

Updated the KG RAG WebUI to have 4 search mode buttons with the following layout:

```
┌─────────────────────────────────────────────────────────────┐
│  Query Mode                                                 │
│  ○ Smart (default)  ○ Semantic  ○ Entity-lookup  ○ Graph   │
└─────────────────────────────────────────────────────────────┘
```

## Button Mapping

| WebUI Button | Backend Mode | Description |
|--------------|--------------|-------------|
| **Smart** ⭐ | `smart` | Unified search combining all strategies (NEW) |
| **Semantic** | `semantic-hybrid` | Vector + keyword + relationship enhancement |
| **Entity-lookup** | `entity-lookup` | Entity-centric with relationship expansion |
| **Graph-traversal** | `graph-traversal` | Graph traversal with embedding enhancement |

## Changes Made

### 1. config.ts
```typescript
// Added 'smart' to QueryMode type
export type QueryMode = 'smart' | 'semantic' | 'entity-lookup' | 'graph-traversal';
export const QUERY_MODES: QueryMode[] = ['smart', 'semantic', 'entity-lookup', 'graph-traversal'];
```

### 2. api/client.ts
```typescript
function mapQueryMode(mode?: string): string {
  const modeMap: Record<string, string> = {
    'smart': 'smart',                           // Smart → smart (unified)
    'semantic': 'semantic-hybrid',              // Semantic → semantic-hybrid
    'entity-lookup': 'entity-lookup',           // Entity-lookup → entity-lookup
    'graph-traversal': 'graph-traversal'        // Graph-traversal → graph-traversal
  };
  return modeMap[mode || ''] || 'smart';        // Default: smart
}
```

### 3. components/tabs/QueryTab.ts
```html
<!-- New Smart button as default (checked) -->
<label title="Smart unified search: combines semantic, keyword, entity, and relationship embeddings">
  <input type="radio" name="queryMode" value="smart" checked> Smart
</label>

<!-- Semantic button (now maps to semantic-hybrid backend) -->
<label title="Semantic hybrid search: vector similarity + keyword matching + relationship enhancement">
  <input type="radio" name="queryMode" value="semantic"> Semantic
</label>
```

## Key Design Decisions

1. **Smart as Default**: New users get the best experience automatically
2. **Semantic → Semantic-Hybrid**: The "Semantic" button now provides enhanced search (vector + keyword + relationship)
3. **Backward Compatible**: Existing code using mode names continues to work
4. **Clear Tooltips**: Each button has descriptive tooltip explaining its function

## Migration for Users

| Old Behavior | New Behavior |
|--------------|--------------|
| Click "Semantic" → pure vector search | Click "Semantic" → hybrid (vector + keyword + relationship) |
| No "Smart" option | "Smart" available as default (recommended) |
| "Entity-lookup" → basic entity search | "Entity-lookup" → enhanced with relationship expansion |

## Testing

After frontend rebuild, verify:
1. ✅ "Smart" button appears first and is selected by default
2. ✅ All 4 buttons are visible
3. ✅ Clicking "Semantic" sends `mode: 'semantic-hybrid'` to backend
4. ✅ Clicking "Smart" sends `mode: 'smart'` to backend

## Rebuild Frontend

```bash
cd /Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta/frontend
npm run build
# or for development:
npm run dev
```
