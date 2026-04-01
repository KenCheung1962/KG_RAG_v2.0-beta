# KG RAG System v2.0-beta - Startup Guide

## Quick Start

To start the complete KG RAG system, simply run:

```bash
./start_kg_rag.sh
```

## What This Script Does

The `start_kg_rag.sh` script automates the initialization and startup of your KG RAG system with the following steps:

### 1. Ollama Availability Check
- Verifies Ollama is running at `http://localhost:11434`
- Lists available models
- Checks for required embedding model (`nomic-embed-text`)

### 2. Backend API Startup
- Starts the pgvector backend at `http://localhost:8002`
- Waits for successful startup with health check
- Logs output to `backend.log`

### 3. Database Health Check
- Verifies backend health endpoint
- Checks dataset sizes:
  - Minimum 1,000 entities
  - Minimum 1,000 relationships
  - Minimum 1,000 chunks
  - Minimum 10 documents
- Warns if datasets are below thresholds

### 4. Frontend WebUI Startup
- Starts the Vite dev server at `http://localhost:8081`
- Installs dependencies if `node_modules` is missing
- Logs output to `frontend.log`

## Prerequisites

Before running the script, ensure you have:

1. **Ollama installed and running**
   ```bash
   # Start Ollama server
   ollama serve
   
   # Or open the Ollama macOS app
   ```

2. **Required Ollama models**
   ```bash
   # Pull the embedding model
   ollama pull nomic-embed-text
   
   # Pull a chat model (e.g., llama3.2)
   ollama pull llama3.2
   ```

3. **Python dependencies installed** (for backend)
   ```bash
   cd backend
   pip install -r requirements.txt  # if exists
   # or ensure your venv has all required packages
   ```

4. **Node.js and npm installed** (for frontend)
   ```bash
   # Check versions
   node --version  # v18+ recommended
   npm --version
   ```

## Services Overview

| Service | URL | Description |
|---------|-----|-------------|
| Frontend WebUI | http://localhost:8081 | React/Vite web interface |
| Backend API | http://localhost:8002 | FastAPI/pgvector backend |
| Ollama | http://localhost:11434 | LLM/embedding service |
| Health Check | http://localhost:8002/health | Database statistics |

## Script Features

### Automatic Cleanup
- Press `Ctrl+C` to gracefully stop all services
- Kills backend and frontend processes
- Cleans up resources

### Port Conflict Detection
- Checks if ports 8002 and 8081 are available
- Shows what's using the port if conflict detected

### Health Monitoring
- Continuous health checks every 5 seconds
- Alerts if services stop unexpectedly

### Colored Output
- ✓ Green: Success
- ✗ Red: Errors
- ⚠ Yellow: Warnings
- ℹ Blue: Information

## Logs

Log files are created in the v2.0-beta directory:

- `backend.log` - Backend API output and errors
- `frontend.log` - Frontend build and runtime logs

To view logs in real-time:
```bash
# Terminal 1: View backend logs
tail -f backend.log

# Terminal 2: View frontend logs
tail -f frontend.log
```

## Troubleshooting

### "Ollama is not running"
```bash
# Start Ollama
ollama serve

# Or open from Applications folder on macOS
```

### "Port 8002 is already in use"
```bash
# Find and kill the process
lsof -Pi :8002
kill <PID>

# Or use the script which will show you the process
```

### "Backend failed to start"
```bash
# Check backend logs
cat backend.log

# Common issues:
# - Missing Python dependencies
# - Database connection issues
# - Port conflicts
```

### "Frontend failed to start"
```bash
# Check frontend logs
cat frontend.log

# Try manually installing dependencies
cd frontend
npm install
npm run dev
```

### Database shows low entity/document counts
The script warns if datasets are below thresholds but still starts. To ingest more data:
1. Open the WebUI at http://localhost:8081
2. Use the document upload feature
3. Or use the backend API directly

## Manual Startup (Alternative)

If you prefer to start services manually:

### 1. Start Ollama
```bash
ollama serve
```

### 2. Start Backend
```bash
cd backend
python pgvector_api.py
# Backend will be at http://localhost:8002
```

### 3. Start Frontend
```bash
cd frontend
npm run dev
# Frontend will be at http://localhost:8081
```

## Environment Variables

Optional environment variables (defined in backend/config.py):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_HOST` | http://127.0.0.1:11434 | Ollama server URL |
| `OLLAMA_EMBED_MODEL` | nomic-embed-text:latest | Embedding model |
| `USE_OLLAMA_DIRECT` | true | Use Ollama directly vs API |
| `API_BASE_URL` | http://127.0.0.1:8001 | Base API URL |

## Support

For issues or questions:
1. Check the logs (`backend.log`, `frontend.log`)
2. Verify all prerequisites are met
3. Check the main README.md in the project root
