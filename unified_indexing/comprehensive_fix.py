#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Comprehensive fix for LightRAG query issues:
1. Clear ALL documents and start fresh
2. Index cybersecurity content properly
3. Ensure proper file paths for references
"""
import sys
sys.path.insert(0, '/Users/ken/clawd/lightrag_local')

import json
import asyncio
import shutil
from pathlib import Path
import re
from bs4 import BeautifulSoup

# Apply ultra-early patch first
import ultra_early_patch

from config import WORKING_DIR, EMBEDDING_DIM
from minimax import deepseek_complete, minimax_embed
from lightrag.utils import EmbeddingFunc

try:
    from lightrag_hku import LightRAG, QueryParam
except ImportError:
    from lightrag import LightRAG, QueryParam

def extract_cybersecurity_content():
    """Extract cybersecurity content from HTML files."""
    cybersecurity_folder = Path.home() / "Desktop/Manus AI Task Example/Training on Cybersecurity/cybersecurity_training/presentations"
    
    documents = []
    for html_file in cybersecurity_folder.glob("*.html"):
        if html_file.name in ['index.html', 'template.html', 'script.js', 'styles.css']:
            continue
        
        # Extract text
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        soup = BeautifulSoup(content, 'html.parser')
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        text = soup.get_text(separator=' ')
        text = re.sub(r'\s+', ' ', text).strip()
        
        if text and len(text) > 100:
            documents.append({
                "content": text,
                "name": html_file.name,
                "path": str(html_file)
            })
            print(f"📄 {html_file.name}: {len(text):,} chars")
    
    return documents

def backup_storage():
    """Backup current storage."""
    storage_dir = Path(WORKING_DIR)
    backup_dir = storage_dir.parent / f"{storage_dir.name}_backup"
    
    if storage_dir.exists():
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(storage_dir, backup_dir)
        print(f"✅ Backed up storage to: {backup_dir}")
    else:
        print("⚠️ No storage directory to backup")

def create_fresh_storage():
    """Create fresh storage directory."""
    storage_dir = Path(WORKING_DIR)
    
    if storage_dir.exists():
        shutil.rmtree(storage_dir)
        print(f"🗑️ Removed old storage: {storage_dir}")
    
    storage_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ Created fresh storage: {storage_dir}")

async def main():
    print("=" * 60)
    print("COMPREHENSIVE FIX FOR LIGHTRAG QUERY ISSUES")
    print("=" * 60)
    
    # Step 1: Backup and create fresh storage
    print("\n1️⃣ Creating fresh storage...")
    backup_storage()
    create_fresh_storage()
    
    # Step 2: Extract cybersecurity content
    print("\n2️⃣ Extracting cybersecurity content...")
    documents = extract_cybersecurity_content()
    if not documents:
        print("❌ No cybersecurity content found!")
        return
    
    print(f"📊 Total: {len(documents)} documents, {sum(len(d['content']) for d in documents):,} chars")
    
    # Step 3: Initialize LightRAG with fresh storage
    print("\n3️⃣ Initializing LightRAG with fresh storage...")
    
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
    print("✅ LightRAG initialized with fresh storage")
    
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
    
    # Analyze results
    print("\n6️⃣ Analyzing results...")
    
    # Check for cybersecurity content
    if "cybersecurity" in result.lower():
        print("✅ Query returned cybersecurity-related content!")
    else:
        print("❌ Query did not return cybersecurity content")
    
    # Check for references
    import re
    ref_patterns = re.findall(r'\[\d+\]', result)
    if ref_patterns:
        print(f"✅ Found references: {ref_patterns[:5]}")
        # Check if they start from [1]
        if ref_patterns and ref_patterns[0] == '[1]':
            print("✅ References start from [1]!")
        else:
            print(f"⚠️ References don't start from [1]: {ref_patterns[0] if ref_patterns else 'No refs'}")
    else:
        print("⚠️ No reference patterns found")
    
    await rag.finalize_storages()
    print("\n✅ Comprehensive fix completed!")

if __name__ == "__main__":
    asyncio.run(main())
