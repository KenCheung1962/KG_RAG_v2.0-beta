#!/bin/bash
# Check if backend is running and return source format

echo "Checking backend on port 8002..."

# Check if port 8002 is in use
if lsof -i :8002 > /dev/null 2>&1; then
    echo "✅ Backend is running on port 8002"
    echo ""
    echo "Testing query endpoint..."
    
    # Test query to check response format
    response=$(curl -s -X POST http://localhost:8002/api/v1/chat \
        -H "Content-Type: application/json" \
        -d '{"message": "test", "top_k": 5}' 2>/dev/null)
    
    if [ -n "$response" ]; then
        echo "Response received"
        echo ""
        echo "Checking 'sources' field in response:"
        
        # Extract sources field
        if echo "$response" | grep -q '"sources": \['; then
            echo "✅ Backend is returning ARRAY (filenames) - GOOD!"
            echo "Sources: $(echo "$response" | grep -o '"sources": \[[^]]*\]')"
        elif echo "$response" | grep -q '"sources": [0-9]'; then
            echo "❌ Backend is returning NUMBER (count only) - NEEDS RESTART!"
            echo "Sources: $(echo "$response" | grep -o '"sources": [0-9]*')"
        else
            echo "⚠️  Could not determine sources format"
            echo "Raw response: $response"
        fi
    else
        echo "❌ No response from backend"
    fi
else
    echo "❌ Backend is NOT running on port 8002"
    echo ""
    echo "Start it with:"
    echo "  cd /Users/ken/clawd_workspace/projects/KG_RAG/v1.2-beta/backend"
    echo "  python pgvector_api.py"
fi
