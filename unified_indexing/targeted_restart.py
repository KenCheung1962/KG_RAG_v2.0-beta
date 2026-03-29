#!/usr/bin/env python3
#!/usr/bin/env python3
"""
LightRAG Targeted Restart Script
Fixes embedding issues and resumes processing from checkpoint.
"""
import sys
import os
import json
import asyncio
import hashlib
import time
from datetime import datetime

# Add paths
sys.path.insert(0, '/Users/ken/clawd/lightrag_local')
os.environ['PYTHONPATH'] = '/usr/local/lib/python3.13/site-packages:' + os.environ.get('PYTHONPATH', '')

# Apply patches
import ultra_early_patch

import numpy as np
import httpx
from collections import OrderedDict

# Configuration
STORAGE_DIR = "/Users/ken/clawd/lightrag_storage_deepseek_new"
# Ollama for embeddings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
EMBEDDING_URL = f"{OLLAMA_HOST}/api/embeddings"
CONCURRENCY = 5  # Reduced from 10
TIMEOUT = 120  # seconds
BATCH_SIZE = 10

print("=" * 70)
print("LightRAG Targeted Restart Script")
print("=" * 70)

# Step 1: Load current state
print("\n📊 Step 1: Loading current state...")

with open(f'{STORAGE_DIR}/kv_store_full_entities.json', 'r') as f:
    entities_kv = json.load(f)

with open(f'{STORAGE_DIR}/kv_store_full_relations.json', 'r') as f:
    relations_kv = json.load(f)

with open(f'{STORAGE_DIR}/vdb_entities.json', 'r') as f:
    vdb_entities = json.load(f)

with open(f'{STORAGE_DIR}/vdb_relationships.json', 'r') as f:
    vdb_relations = json.load(f)

with open(f'{STORAGE_DIR}/kv_store_doc_status.json', 'r') as f:
    doc_status = json.load(f)

# Count current state
processed_docs = sum(1 for d in doc_status.values() if d.get('status') == 'processed')
total_docs = len(doc_status)
print(f"   Processed docs: {processed_docs}/{total_docs}")

# Extract entity names from KV store
entity_names = set()
for doc_data in entities_kv.values():
    if isinstance(doc_data, dict) and 'entity_names' in doc_data:
        entity_names.update(doc_data['entity_names'])

# Extract relation info from KV store  
relation_triples = []
for doc_data in relations_kv.values():
    if isinstance(doc_data, dict) and 'relation_triples' in doc_data:
        for triple in doc_data['relation_triples']:
            if len(triple) >= 3:
                relation_triples.append({
                    'src': triple[0],
                    'dst': triple[2],
                    'rel': triple[1]
                })

# Get existing embedded entities
existing_entities = set()
if isinstance(vdb_entities.get('data'), list):
    for item in vdb_entities['data']:
        if isinstance(item, dict) and 'entity_name' in item:
            existing_entities.add(item['entity_name'])

# Get existing embedded relations
existing_relations = set()
if isinstance(vdb_relations.get('data'), list):
    for item in vdb_relations['data']:
        if isinstance(item, dict):
            # Create a signature for the relation (handle None values)
            src = item.get('src') or ''
            dst = item.get('dst') or ''
            sig = tuple(sorted([src, dst]))
            existing_relations.add(sig)

missing_entities = entity_names - existing_entities
missing_relations = []
for triple in relation_triples:
    sig = tuple(sorted([triple['src'], triple['dst']]))
    if sig not in existing_relations:
        missing_relations.append(triple)

print(f"   Total entities extracted: {len(entity_names)}")
print(f"   Entities already embedded: {len(existing_entities)}")
print(f"   Entities missing: {len(missing_entities)}")
print(f"   Total relations extracted: {len(relation_triples)}")
print(f"   Relations already embedded: {len(existing_relations)}")
print(f"   Relations missing: {len(missing_relations)}")

# Step 2: Generate embeddings for missing entities
print("\n🔧 Step 2: Generating embeddings for missing entities...")

async def embed_texts(texts: list) -> np.ndarray:
    """Generate embeddings using Docker BGE-M3."""
    valid_texts = [text for text in texts if text and str(text).strip()]
    if not valid_texts:
        return np.array([], dtype=np.float32).reshape(0, 1024)
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            EMBEDDING_URL,
            json={"texts": valid_texts, "normalize": True},
            timeout=TIMEOUT
        )
        if response.status_code == 200:
            result = response.json()
            return np.array(result["embeddings"], dtype=np.float32)
        else:
            raise Exception(f"Embedding failed: {response.status_code}")

def generate_entity_content(entity_name: str) -> str:
    """Generate content for entity embedding."""
    return f"Entity: {entity_name}\nType: concept\nDescription: {entity_name} is a named entity extracted from the knowledge base."

def generate_relation_content(src: str, rel: str, dst: str) -> str:
    """Generate content for relation embedding."""
    return f"Source: {src}\nRelation: {rel}\nTarget: {dst}\nType: relationship"

async def embed_entities_batch(entities: list, batch_size: int = BATCH_SIZE) -> dict:
    """Embed a batch of entities with concurrency control."""
    results = {}
    
    for i in range(0, len(entities), batch_size):
        batch = list(entities)[i:i + batch_size]
        texts = [generate_entity_content(e) for e in batch]
        
        try:
            embeddings = await embed_texts(texts)
            for j, entity in enumerate(batch):
                results[entity] = {
                    "__id__": hashlib.md5(entity.encode()).hexdigest(),
                    "__created_at__": int(time.time()),
                    "entity_name": entity,
                    "content": texts[j],
                    "vector": embeddings[j].tolist() if j < len(embeddings) else None
                }
            print(f"   ✓ Embedded {i + len(batch)}/{len(entities)} entities")
        except Exception as e:
            print(f"   ✗ Failed to embed batch starting at {i}: {e}")
            # Retry with smaller batch
            for entity in batch:
                try:
                    text = generate_entity_content(entity)
                    embedding = await embed_texts([text])
                    results[entity] = {
                        "__id__": hashlib.md5(entity.encode()).hexdigest(),
                        "__created_at__": int(time.time()),
                        "entity_name": entity,
                        "content": text,
                        "vector": embedding[0].tolist()
                    }
                    print(f"   ✓ Embedded entity: {entity}")
                except Exception as e2:
                    print(f"   ✗ Failed to embed entity {entity}: {e2}")
    
    return results

async def embed_relations_batch(relations: list, batch_size: int = BATCH_SIZE) -> list:
    """Embed a batch of relations with concurrency control."""
    results = []
    
    for i in range(0, len(relations), batch_size):
        batch = relations[i:i + batch_size]
        texts = [generate_relation_content(r['src'], r['rel'], r['dst']) for r in batch]
        
        try:
            embeddings = await embed_texts(texts)
            for j, rel in enumerate(batch):
                results.append({
                    "__id__": hashlib.md5(f"{rel['src']}{rel['rel']}{rel['dst']}".encode()).hexdigest(),
                    "__created_at__": int(time.time()),
                    "src": rel['src'],
                    "dst": rel['dst'],
                    "rel": rel['rel'],
                    "content": texts[j],
                    "vector": embeddings[j].tolist() if j < len(embeddings) else None
                })
            print(f"   ✓ Embedded {i + len(batch)}/{len(relations)} relations")
        except Exception as e:
            print(f"   ✗ Failed to embed batch starting at {i}: {e}")
    
    return results

# Embed missing entities
if missing_entities:
    print(f"   Processing {len(missing_entities)} missing entities...")
    embedded_entities = asyncio.run(embed_entities_batch(list(missing_entities)))
    print(f"   Successfully embedded {len(embedded_entities)} entities")
else:
    print("   ✓ No missing entities")
    embedded_entities = {}

# Embed missing relations
if missing_relations:
    print(f"   Processing {len(missing_relations)} missing relations...")
    embedded_relations = asyncio.run(embed_relations_batch(missing_relations))
    print(f"   Successfully embedded {len(embedded_relations)} relations")
else:
    print("   ✓ No missing relations")
    embedded_relations = []

# Step 3: Update VDB files
print("\n💾 Step 3: Updating VDB files...")

# Update entity VDB
if embedded_entities:
    if 'data' not in vdb_entities or not isinstance(vdb_entities['data'], list):
        vdb_entities['data'] = []
    
    # Add new entities
    for entity in embedded_entities.values():
        if entity.get('vector') is not None:
            vdb_entities['data'].append(entity)
    
    with open(f'{STORAGE_DIR}/vdb_entities.json', 'w') as f:
        json.dump(vdb_entities, f, indent=2)
    print(f"   ✓ Updated vdb_entities.json ({len(vdb_entities['data'])} total entities)")

# Update relation VDB
if embedded_relations:
    if 'data' not in vdb_relations or not isinstance(vdb_relations['data'], list):
        vdb_relations['data'] = []
    
    # Add new relations
    for rel in embedded_relations:
        if rel.get('vector') is not None:
            vdb_relations['data'].append(rel)
    
    with open(f'{STORAGE_DIR}/vdb_relationships.json', 'w') as f:
        json.dump(vdb_relations, f, indent=2)
    print(f"   ✓ Updated vdb_relationships.json ({len(vdb_relations['data'])} total relations)")

# Step 4: Fix checkpoint
print("\n📍 Step 4: Fixing checkpoint...")

pending_docs = [doc_id for doc_id, data in doc_status.items() if data.get('status') != 'processed']
print(f"   Pending documents: {len(pending_docs)}")

# Update checkpoint
checkpoint = {
    "timestamp": datetime.utcnow().isoformat(),
    "indexed": processed_docs,
    "pending": len(pending_docs),
    "last_updated": datetime.utcnow().isoformat()
}

with open(f'{STORAGE_DIR}/.index_checkpoint.json', 'w') as f:
    json.dump(checkpoint, f, indent=2)

print(f"   ✓ Updated checkpoint: {processed_docs}/{total_docs} processed")

# Step 5: Summary
print("\n" + "=" * 70)
print("📊 SUMMARY")
print("=" * 70)
print(f"   Entities embedded: {len(embedded_entities)}")
print(f"   Relations embedded: {len(embedded_relations)}")
print(f"   Processed docs: {processed_docs}/{total_docs}")
print(f"   Pending docs: {len(pending_docs)}")

if pending_docs:
    print(f"\n⚠️  {len(pending_docs)} documents still need processing")
    print("   Run resume script to continue...")

print("\n✅ Targeted restart complete!")
