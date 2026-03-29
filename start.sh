#!/bin/bash
# KG RAG System v1.2-beta Startup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================="
echo "  KG RAG System v1.2-beta"
echo "========================================="
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM

# Check which backend to use
echo "Select backend:"
echo "1) pgvector_api (Port 8002) - Recommended"
echo "2) unified_indexing (Port 8001)"
read -p "Enter choice [1-2]: " choice

if [ "$choice" = "2" ]; then
    BACKEND_DIR="$SCRIPT_DIR/unified_indexing"
    BACKEND_PORT=8001
    BACKEND_CMD="python -m main"
else
    BACKEND_DIR="$SCRIPT_DIR/backend"
    BACKEND_PORT=8002
    BACKEND_CMD="python pgvector_api.py"
fi

FRONTEND_DIR="$SCRIPT_DIR/frontend"
FRONTEND_PORT=8081

# Start Backend
echo ""
echo "Starting Backend on port $BACKEND_PORT..."
cd "$BACKEND_DIR"
$BACKEND_CMD &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to be ready
echo "Waiting for backend to start..."
sleep 5

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "ERROR: Backend failed to start!"
    exit 1
fi

# Start Frontend
echo ""
echo "Starting Frontend on port $FRONTEND_PORT..."
cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Wait for frontend
echo "Waiting for frontend to start..."
sleep 3

echo ""
echo "========================================="
echo "  Services Started!"
echo "========================================="
echo ""
echo "Backend:   http://localhost:$BACKEND_PORT"
echo "Frontend:  http://localhost:$FRONTEND_PORT"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID
