# Entity Embedding Implementation

## Overview
This implementation adds **embedding generation for entities** during the file upload process. Previously, only text chunks and relationships had embeddings; entities were stored with `embedding=NULL`.

## What Gets Embedded Now

### 1. Document Entities
| Attribute | Value |
|-----------|-------|
| **What** | The uploaded file itself |
| **Entity Type** | `document` |
| **Embedding Text** | `{filename} (document) - Uploaded document` |
| **Example** | `"report.pdf (document) - Uploaded document"` |

### 2. Extracted Entities (from LLM)
| Attribute | Value |
|-----------|-------|
| **What** | Entities extracted by LLM during upload |
| **Entity Types** | company, person, product, technology, tool, location, organization, concept, project, task, note, stock, money, percentage, number, date, article, patent, book, journal |
| **Embedding Text** | `{name} ({type}) - {description}` |
| **Example** | `"Apple Inc. (company) - Technology company founded in 1976"` |

## Entity Extraction Schema (JSON from LLM)

```json
{
  "entities": [
    {
      "name": "Entity Name",
      "type": "entity_type",
      "description": "brief description"
    }
  ],
  "relationships": [
    {
      "from": "Entity1",
      "to": "Entity2",
      "type": "relationship_type"
    }
  ]
}
```

### Allowed Entity Types
- **Organizations:** company, organization
- **People:** person
- **Products/Tech:** product, technology, tool
- **Location:** location
- **Concepts:** concept, project, task, note
- **Financial:** stock, money, percentage, number
- **Temporal:** date
- **Documents:** article, patent, book, journal

### Allowed Relationship Types
`cites`, `authored_by`, `related_to`, `based_on`, `created_by`, `contains`, `extends`, `depends_on`, `implemented_in`, `part_of`, `uses`, `implements`, `works_at`, `extracted_from`, `trades_at`, `has_price`, `has_change`, `has_volume`, `has_market_cap`, `granted_to`, `owned_by`, `contribute_to`, `mentions`

## Code Changes

### Files Modified

#### 1. `backend/pgvector_api.py`

**Updated Functions:**
- `upload_document_json()` - Single file upload
- `process_single_file()` - Folder upload processing

**Changes in Each Location:**

```python
# BEFORE: Document entity without embedding
entity = Entity(
    entity_id=doc_id,
    entity_type="document",
    name=filename,
    description=f"Document: {filename}",
    properties={"filename": filename, "type": "uploaded"}
)

# AFTER: Document entity WITH embedding
doc_embedding_text = f"{filename} (document) - Uploaded document"
try:
    doc_embedding = get_ollama_embedding(doc_embedding_text)
except Exception as e:
    print(f"[Upload] Document embedding failed for {filename}: {e}")
    doc_embedding = None

entity = Entity(
    entity_id=doc_id,
    entity_type="document",
    name=filename,
    description=f"Document: {filename}",
    properties={"filename": filename, "type": "uploaded"},
    embedding=doc_embedding  # ← NEW
)
```

```python
# BEFORE: Extracted entity without embedding
ent_entity = Entity(
    entity_id=ent_id,
    entity_type=ent_type,
    name=ent_name,
    description=f"Extracted from {filename}",
    properties={"source": filename, "extracted": True}
)

# AFTER: Extracted entity WITH embedding
embedding_text = f"{ent_name} ({ent_type})"
if ent_description:
    embedding_text += f" - {ent_description}"

try:
    ent_embedding = get_ollama_embedding(embedding_text)
except Exception as e:
    print(f"[Upload] Entity embedding failed for {ent_name}: {e}")
    ent_embedding = None

ent_entity = Entity(
    entity_id=ent_id,
    entity_type=ent_type,
    name=ent_name,
    description=ent_description or f"Extracted from {filename}",
    properties={"source": filename, "extracted": True},
    embedding=ent_embedding  # ← NEW
)
```

## Embedding Generation Flow

```
File Upload
    ↓
Extract Text from Document
    ↓
┌─────────────────────────┐
│ Create Document Entity  │
│ - Generate embedding:   │
│   "filename (document)" │
└──────────┬──────────────┘
           ↓
Split into Chunks
    ↓
Generate Chunk Embeddings
    ↓
LLM Entity Extraction
    ↓
┌─────────────────────────┐
│ Create Extracted        │
│ Entities (with          │
│ embeddings):            │
│ "Name (type) - desc"    │
└──────────┬──────────────┘
           ↓
Create Relationships
    ↓
Done
```

## Complete List of Embedded Quantities

| Quantity | With Embeddings | Embedding Text Format | Status |
|----------|-----------------|----------------------|--------|
| **Text Chunks** | 100% | Raw chunk content | ✅ Implemented |
| **Relationships** | ~52% | `source type target` | ✅ Implemented |
| **Document Entities** | 100% (new) | `filename (document)` | ✅ NEW |
| **Extracted Entities** | 100% (new) | `name (type) - description` | ✅ NEW |

## Database Schema

### Entities Table
```sql
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    entity_id VARCHAR(255) UNIQUE,
    entity_type VARCHAR(100),
    name TEXT,
    description TEXT,
    properties JSONB,
    embedding VECTOR(768),  -- ← Stores entity embedding
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Testing

### Verify Entity Embeddings
```bash
# Check entity embedding count
cd /Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta
python3 -c "
import asyncpg
import asyncio

async def check():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/kg_rag')
    result = await conn.fetchrow('SELECT COUNT(*) as total, COUNT(embedding) as with_emb FROM entities')
    print(f'Entities: {result[\"total\"]} total, {result[\"with_emb\"]} with embeddings ({result[\"with_emb\"]/result[\"total\"]*100:.1f}%)')
    await conn.close()

asyncio.run(check())
"
```

### Expected Output After Upload
```
[Upload] Using LLM provider: deepseek (fallback: minimax)
[Upload] Document embedding generated for report.pdf
[Upload] Extracted 12 entities, 8 relationships
[Upload] Entity embeddings generated: 12
[Upload] Successfully uploaded report.pdf
```

## Search Impact

The `search_entities()` function in `storage.py` now works properly:

```python
async def search_entities(self, query_vector: List[float], ...):
    query = """
    SELECT *, (1 - (embedding <=> $1::vector)) as similarity
    FROM entities
    WHERE embedding IS NOT NULL  -- Now returns results!
    ORDER BY embedding <=> $1::vector
    LIMIT $2
    """
```

**Before:** All entities had `embedding=NULL`, so entity vector search returned nothing.

**After:** Entities have embeddings, enabling semantic search over entities.

## Performance Impact

| Metric | Impact |
|--------|--------|
| **Upload Time** | +0.1-0.3s per entity (embedding generation) |
| **Memory** | No significant change |
| **Database Size** | +3KB per entity (768-dim vector) |

For a document with 10 extracted entities:
- Additional upload time: ~1-2 seconds
- Additional storage: ~30KB

## Backward Compatibility

- ✅ Existing entities without embeddings remain functional
- ✅ Entity search gracefully handles NULL embeddings
- ✅ No breaking changes to API
- ✅ Embeddings generated only for new uploads

## Migration for Existing Entities

To generate embeddings for existing entities (optional):

```python
# Run in Python shell
import asyncio
from pgvector_api import get_ollama_embedding

async def backfill_entity_embeddings():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/kg_rag')
    
    # Get entities without embeddings
    rows = await conn.fetch('SELECT entity_id, name, entity_type, description FROM entities WHERE embedding IS NULL')
    
    for row in rows:
        text = f"{row['name']} ({row['entity_type']})"
        if row['description']:
            text += f" - {row['description']}"
        
        try:
            embedding = get_ollama_embedding(text)
            await conn.execute(
                'UPDATE entities SET embedding = $1::vector WHERE entity_id = $2',
                '[' + ','.join(str(v) for v in embedding) + ']',
                row['entity_id']
            )
            print(f"✅ {row['name']}")
        except Exception as e:
            print(f"❌ {row['name']}: {e}")
    
    await conn.close()

asyncio.run(backfill_entity_embeddings())
```
