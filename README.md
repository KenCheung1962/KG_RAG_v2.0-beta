# KG RAG System v2.0-beta

Unified Knowledge Graph RAG System with PostgreSQL + pgvector backend and Vite + TypeScript frontend.

## 📖 Documentation

**[📘 Complete User Manual](KG_RAG_USER_MANUAL.md)** - Comprehensive guide covering:
- System startup process
- WebUI tabs and functionality
- File ingestion and indexing
- Query search modes and workflows
- Configuration and LLM setup
- Troubleshooting

## 🚀 Quick Start

### Prerequisites

1. **PostgreSQL with pgvector** - Database for storing knowledge graph
2. **Ollama** - Local embeddings server (`nomic-embed-text` model required)
3. **Node.js 18+** - Frontend build environment
4. **Python 3.9+** - Backend runtime

### Start the System

```bash
# Using the startup script (recommended)
python3 start_kg_rag.py

# Or with fresh dependencies
python3 start_kg_rag.py --fresh

# Access the WebUI
open http://localhost:8081
```

### Stop the System

```bash
./stop_kg_rag.sh
```

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        KG RAG v2.0-beta                         │
├─────────────────────────────────────────────────────────────────┤
│  WebUI (Vite)        │  Backend API (FastAPI)     │  Database   │
│  Port: 8081          │  Port: 8002                │  PostgreSQL │
│                      │                            │  + pgvector │
├──────────────────────┼────────────────────────────┼─────────────┤
│  • Query Tab         │  • Chat Endpoint           │  • Entities │
│  • Query+File Tab    │  • Upload Endpoint         │  • Relations│
│  • Ingest Tab        │  • Search Endpoints        │  • Chunks   │
│  • Config Tab        │  • Health Check            │  • Documents│
└──────────────────────┴────────────────────────────┴─────────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   Ollama (Local)      │
        │   Port: 11434         │
        │   Model: nomic-embed  │
        └───────────────────────┘
```

### Service Ports

| Service | Port | Purpose |
|---------|------|---------|
| Frontend WebUI | 8081 | User interface |
| Backend API | 8002 | FastAPI backend |
| DB Management API | 8013 | Database operations |
| Ollama | 11434 | Local embeddings |

## 📁 Folder Structure

```
v2.0-beta/
├── backend/                   # FastAPI Backend Server
│   ├── pgvector_api.py        # Main API with RAG chat endpoints
│   ├── api_client.py          # LLM provider clients (DeepSeek, MiniMax)
│   ├── metadata_extractor.py  # Bibliographic metadata extraction
│   └── ...
├── frontend/                  # Vite + TypeScript Frontend
│   ├── src/
│   │   ├── components/tabs/   # Query, QueryFile, Ingest, Config tabs
│   │   ├── api/               # API client modules
│   │   └── config.ts          # Frontend configuration
│   └── scripts/               # DB management scripts
├── unified_indexing/          # Alternative backend (not active)
├── KG_RAG_USER_MANUAL.md      # 📘 Complete user manual
├── kgrag_config.yaml          # System configuration
├── start_kg_rag.py            # Startup script
└── stop_kg_rag.sh             # Stop script
```

## ⚙️ Configuration

### Main Config File

Edit `kgrag_config.yaml` to customize:

```yaml
services:
  backend:
    port: 8002
  frontend:
    port: 8081
  db_management_api:
    port: 8013

ollama:
  required_models:
    - "nomic-embed-text"
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `KGRAG_BACKEND_PORT` | Backend API port |
| `KGRAG_FRONTEND_PORT` | WebUI port |
| `KGRAG_LOG_LEVEL` | Logging level (DEBUG, INFO, WARN, ERROR) |
| `MINIMAX_API_KEY` | MiniMax API key |

### LLM Providers

| Provider | Type | Status |
|----------|------|--------|
| DeepSeek | Primary | ✅ Required |
| MiniMax | Fallback | ⚠️ Recommended |
| Ollama | Embeddings | ✅ Required (local) |

## ✨ Features

### Query Modes (4 Modes)

| Mode | Description | Best For |
|------|-------------|----------|
| **Smart** ⭐ (default) | Multi-layer unified search using ALL embeddings | All queries (recommended) |
| **Semantic** | Vector similarity on chunks | Simple semantic queries |
| **Entity-lookup** | Entity-centric with keyword boost | Entity-focused questions |
| **Graph-traversal** | Graph BFS with path finding | Relationship questions |

**Smart Mode** automatically combines:
- Chunk embeddings (semantic foundation)
- Entity embeddings (entity discovery)
- Relationship embeddings (relationship enhancement)
- Keyword extraction (precision boosting)

### Detail Levels

| Level | Words | Description |
|-------|-------|-------------|
| ⚡ Quick | ~300 | Brief summary |
| 📊 Balanced | ~800 | Moderate detail |
| 📚 Comprehensive | ~1500 | In-depth analysis |
| 🎓 Ultra Deep | ~3000+ | Academic level with full citations |

### Document Support

- **PDF** - Full text extraction with metadata
- **DOCX** - Microsoft Word documents
- **TXT/MD** - Plain text and Markdown
- **HTML** - Web pages

## 🔧 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Ollama model not found | `ollama pull nomic-embed-text` |
| Port already in use | `lsof -Pi :8002` then `kill <PID>` |
| DB API not running | Restart with `python3 start_kg_rag.py` |
| Frontend module error | `rm -rf node_modules && npm install` |

### Logs

| Log File | Purpose |
|----------|---------|
| `backend.log` | Backend API logs |
| `frontend.log` | Frontend dev server logs |
| `db-api.log` | Database API logs |

### Health Checks

```bash
# Backend
curl http://localhost:8002/health

# Ollama
curl http://localhost:11434/api/tags

# DB API
curl http://localhost:8013/health
```

## 📚 Additional Documentation

| Document | Description |
|----------|-------------|
| [KG_RAG_USER_MANUAL.md](KG_RAG_USER_MANUAL.md) | Complete user guide |
| [CONFIGURATION_GUIDE.md](CONFIGURATION_GUIDE.md) | Configuration reference |
| [STARTUP_GUIDE.md](STARTUP_GUIDE.md) | Startup process details |
| [SEARCH_MODES_IMPLEMENTATION.md](SEARCH_MODES_IMPLEMENTATION.md) | Search modes implementation details |
| [docs/SEARCH_MODES_SUMMARY.md](docs/SEARCH_MODES_SUMMARY.md) | Search modes user guide |
| [CHANGELOG.md](CHANGELOG.md) | All system changes |
| `backend/docs/` | Backend technical docs |
| `frontend/README.md` | Frontend documentation |

## 📝 Version History

- **v2.0-beta**: Enhanced startup script, DB Management API auto-restart, font size improvements
- **v2.0-beta**: Combined v1.0 backend + v1.1 frontend
- **v1.1-beta**: Vite + TypeScript frontend
- **v1.0-beta**: Original pgvector backend

## 🔗 Access URLs

| Service | URL |
|---------|-----|
| WebUI | http://localhost:8081 |
| Backend API | http://localhost:8002 |
| Backend Docs | http://localhost:8002/docs |
| DB API | http://localhost:8013 |

---

For detailed information, see **[KG_RAG_USER_MANUAL.md](KG_RAG_USER_MANUAL.md)**.
