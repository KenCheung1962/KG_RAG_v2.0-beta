#!/bin/bash
echo "========================================="
echo "  Stopping KG RAG System"
echo "========================================="
pkill -f "pgvector_api.py" 2>/dev/null && echo "Backend stopped" || echo "Backend not running"
pkill -f "vite" 2>/dev/null && echo "Frontend stopped" || echo "Frontend not running"
echo "========================================="
echo "  KG RAG System Stopped!"
echo "========================================="
