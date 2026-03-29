#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Fix LightRAG query issues:
1. Clear stuck processing documents
2. Index cybersecurity content with proper file paths
3. Test query
"""
import sys
sys.path.insert(0, '/Users/ken/clawd/lightrag_local')

import json
import asyncio
from pathlib import Path

# Apply ultra-early patch first
import ultra_early_patch

from config import WORKING_DIR, EMBEDDING_DIM
from minimax import deepseek_complete, minimax_embed
from lightrag.utils import EmbeddingFunc

try:
    from lightrag_hku import LightRAG, QueryParam
except ImportError:
    from lightrag import LightRAG, QueryParam

def clear_stuck_documents():
    """Clear stuck processing documents from doc_status."""
    doc_status_path = Path(WORKING_DIR) / "kv_store_doc_status.json"
    
    if not doc_status_path.exists():
        print("❌ No doc_status file found")
        return
    
    with open(doc_status_path, 'r') as f:
        doc_status = json.load(f)
    
    # Keep only processed documents
    clean_status = {}
    for doc_id, status in doc_status.items():
        if status.get('status') == 'processed':
            clean_status[doc_id] = status
        else:
            print(f"⚠️ Removing stuck document: {doc_id}")
    
    # Save clean status
    with open(doc_status_path, 'w') as f:
        json.dump(clean_status, f, indent=2)
    
    print(f"✅ Cleaned doc_status: {len(clean_status)} processed documents kept")
    return len(doc_status) - len(clean_status)

def read_cybersecurity_content():
    """Read cybersecurity text files."""
    content_folder = Path.home() / "Desktop/cybersecurity_content"
    documents = []
    
    for txt_file in content_folder.glob("*.txt"):
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        documents.append({
            "content": content,
            "name": txt_file.name,
            "path": str(txt_file)
        })
        print(f"📄 {txt_file.name}: {len(content):,} chars")
    
    return documents

async def main():
    print("=" * 60)
    print("Fixing LightRAG Query Issues")
    print("=" * 60)
    
    # Step 1: Clear stuck documents
    print("\n1️⃣ Clearing stuck processing documents...")
    cleared = clear_stuck_documents()
    if cleared > 0:
        print(f"✅ Cleared {cleared} stuck documents")
    
    # Step 2: Read cybersecurity content
    print("\n2️⃣ Loading cybersecurity content...")
    documents = read_cybersecurity_content()
    if not documents:
        print("❌ No cybersecurity content found!")
        return
    
    print(f"📊 Total: {len(documents)} documents, {sum(len(d['content']) for d in documents):,} chars")
    
    # Step 3: Initialize LightRAG
    print("\n3️⃣ Initializing LightRAG...")
    
    embedding_function = EmbeddingFunc(
        embedding_dim=EMBEDDING_DIM,
        max_token_size=8192,
        func=minimax_embed
    )
    
    rag = LightRAG(
        working_dir=str(WORKING_DIR),
        embedding_func=embedding_function,
        llm_model_func=deepseek_complete,
        chunk_token_size=1200,
        chunk_overlap_token_size=100,
        addon_params={"language": "English", "entity_types": ["person", "organization", "location", "event", "concept", "technology", "product", "document", "framework", "regulation", "metric", "tool"]},
        enable_llm_cache=True
    )
    
    await rag.initialize_storages()
    print("✅ LightRAG initialized")
    
    # Step 4: Index cybersecurity content
    print("\n4️⃣ Indexing cybersecurity content...")
    contents = [doc["content"] for doc in documents]
    await rag.ainsert(contents)
    print(f"✅ Indexed {len(documents)} cybersecurity documents")
    
    # Step 5: Test query
    print("\n5️⃣ Testing query: 'what is cybersecurity?'")
    print("=" * 60)
    
    result = await rag.aquery(
        "what is cybersecurity?",
        param=QueryParam(
            mode="hybrid",
            response_type="Multiple Paragraphs",
            top_k=60,
            chunk_top_k=20
        )
    )
    
    print(result)
    print("=" * 60)
    
    # Check if response contains cybersecurity content
    if "cybersecurity" in result.lower() or "security" in result.lower():
        print("✅ Query returned cybersecurity-related content!")
    else:
        print("⚠️ Query may not have returned cybersecurity content")
    
    await rag.finalize_storages()
    print("\n✅ Fixes applied successfully!")

if __name__ == "__main__":
    asyncio.run(main())
