#!/usr/bin/env python3
#!/usr/bin/env python3
"""
Quick verification script to check if JsonKVStorage fix is properly applied.
"""
import os
import sys

def check_file(filepath):
    """Check if a file has ultra_early_patch import or its own patch."""
    try:
        with open(filepath, 'r') as f:
            content = f.read(2000)  # Read first 2000 chars
            # Check for ultra_early_patch import
            if 'import ultra_early_patch' in content:
                return True, "ultra_early_patch"
            # Check for own patch implementation
            if '_safe_serializer' in content or '_original_json_dumps' in content:
                return True, "own_patch"
            return False, "none"
    except:
        return False, "error"

print("=" * 70)
print("JsonKVStorage Fix Verification")
print("=" * 70)

# Critical files to check
critical_files = [
    'service.py',
    'ingest.py',
    'index_cybersecurity.py',
    'ingest_fixed.py',
    'ingest_deepseek.py',
    'index_knowledge_graph.py',
    'langchain_chunker.py',
    'ingest_recommended_articles.py',
    'retry_with_fix.py',
    'retry_failed_docs.py',
    'comprehensive_fix.py',
    'fix_lightrag_issues.py',
    'pipeline_complete.py',
    'test_single_file.py',
    'webui.py',
    'webui_simple.py',
    'webui_v2.py',
    'webui_fixed.py',
    'webui_ultra.py',
    'vector_rag.py',
    'rag_api.py',
]

base_path = '/Users/ken/clawd/lightrag_local'
all_ok = True

print("\nChecking critical files:")
print("-" * 70)

for filename in critical_files:
    filepath = os.path.join(base_path, filename)
    if os.path.exists(filepath):
        has_patch, patch_type = check_file(filepath)
        if has_patch:
            print(f"✓ {filename} ({patch_type})")
        else:
            print(f"✗ {filename} - MISSING patch!")
            all_ok = False
    else:
        print(f"? {filename} - Not found")

print("-" * 70)

# Test the actual fix
print("\nTesting the serialization fix:")
print("-" * 70)

try:
    sys.path.insert(0, base_path)
    import ultra_early_patch
    print("✓ ultra_early_patch imported successfully")
    
    # Test serialization
    import json
    from ultra_early_patch import _safe_serializer
    
    class MockKVStorage:
        def __init__(self):
            self.namespace = "test"
            self._data = {"key": "value", "number": 42}
    
    storage = MockKVStorage()
    result = _safe_serializer(storage)
    print(f"✓ JsonKVStorage serialization: {type(result).__name__}")
    
    # Test json.dumps
    test_obj = {"storage": storage, "list": [1, 2, storage]}
    json_result = json.dumps(test_obj)
    print("✓ json.dumps works correctly")
    
except Exception as e:
    print(f"✗ Error: {e}")
    all_ok = False

print("-" * 70)
print("\n" + "=" * 70)
if all_ok:
    print("✅ ALL CHECKS PASSED - JsonKVStorage fix is properly applied!")
else:
    print("❌ SOME CHECKS FAILED - Review the output above")
print("=" * 70)
