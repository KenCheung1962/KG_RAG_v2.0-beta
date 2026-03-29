#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "========================================="
echo "  Starting KG RAG System v1.3-beta"
echo "========================================="

# Start Backend
echo "Starting Backend on port 8002..."
cd "$BACKEND_DIR"
python3 pgvector_api.py &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

sleep 5

# Start Frontend
echo "Starting Frontend on port 8081..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "========================================="
echo "  KG RAG System Started!"
echo "========================================="
echo "Backend:   http://localhost:8002"
echo "Frontend:  http://localhost:8081"
echo "To stop: ./stop_kg_rag.sh"
echo ""
