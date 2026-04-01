# KG RAG System v2.0-beta - User Manual

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Startup Process](#2-startup-process)
3. [WebUI Tabs and Functionality](#3-webui-tabs-and-functionality)
4. [File Ingestion and Database Indexing](#4-file-ingestion-and-database-indexing)
5. [Query Search Modes and Workflow](#5-query-search-modes-and-workflow)
6. [Configuration and LLM Setup](#6-configuration-and-llm-setup)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. System Overview

The KG RAG (Knowledge Graph Retrieval-Augmented Generation) System v2.0-beta is an advanced document intelligence platform that combines:

- **Knowledge Graph Construction**: Automatic extraction of entities and relationships
- **Vector Search**: Semantic document retrieval using pgvector
- **LLM Integration**: Multi-provider support (DeepSeek primary, MiniMax fallback)
- **Document Management**: Upload, index, and query documents

### System Architecture

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
        │   (Embeddings)        │
        └───────────────────────┘
```

### Service Ports

| Service | Port | Purpose | Status Check |
|---------|------|---------|--------------|
| Frontend WebUI | 8081 | User interface | `http://localhost:8081` |
| Backend API | 8002 | FastAPI backend | `http://localhost:8002/health` |
| DB Management API | 8013 | Database operations | `http://localhost:8013/health` |
| Ollama | 11434 | Local embeddings | `http://localhost:11434/api/tags` |

### Required Models

| Model | Source | Purpose | Required |
|-------|--------|---------|----------|
| `nomic-embed-text` | Ollama | Document/query embeddings | ✅ Yes |
| `deepseek-chat` | DeepSeek API | LLM responses | ✅ Yes (API key) |
| `minimax-m2.7` | MiniMax API | Fallback LLM | ⚠️ Recommended |

---

## 2. Startup Process

### 2.1 Using the Startup Script

The system is started using the Python startup script `start_kg_rag.py`:

```bash
cd /v2.0-beta
python3 start_kg_rag.py
```

### 2.2 Startup Sequence

The startup script performs the following checks and initialization steps:

#### Step 1: Ollama Verification
```
[INFO] Checking Ollama availability...
[✓] Ollama is running at http://localhost:11434
[✓] Required models available: nomic-embed-text
```
- Verifies Ollama server is running
- Checks if `nomic-embed-text` model is available
- Prompts to run `ollama pull nomic-embed-text` if missing

#### Step 2: Backend Startup (Port 8002)
```
[INFO] Starting backend on port 8002...
[INFO] Backend PID: <pid>
[✓] Backend is running at http://localhost:8002
```
- Starts FastAPI backend (`pgvector_api.py`)
- Performs health check verification
- Waits up to 30 seconds for startup

#### Step 3: Database Health Check
```
[INFO] Checking database health...
Database Statistics:
  Entities:      45,887
  Relationships: 116,305
  Chunks:        368,536
  Documents:     1,982
[✓] Database has sizable datasets and is ready
```
- Connects to PostgreSQL with pgvector extension
- Validates entity/relationship/chunk counts
- Reports database health status

#### Step 4: DB Management API Startup (Port 8013)
```
[INFO] Starting DB Management API on port 8013...
[INFO] DB API PID: <pid>
[✓] DB Management API is running at http://localhost:8013
```
- Starts Node.js database management service
- Provides database statistics and backup/restore functions
- Auto-restarts if it fails during operation

#### Step 5: Frontend Startup (Port 8081)
```
[INFO] Starting frontend on port 8081...
[INFO] Frontend PID: <pid>
[✓] Frontend is running at http://localhost:8081
```
- Starts Vite development server
- Validates `node_modules` (reinstalls if corrupted)
- Serves WebUI at `http://localhost:8081`

### 2.3 Startup Script Options

```bash
# Basic usage
python3 start_kg_rag.py

# Skip Ollama check (if not using local embeddings)
python3 start_kg_rag.py --skip-ollama

# Start only backend
python3 start_kg_rag.py --backend-only

# Start only frontend
python3 start_kg_rag.py --frontend-only

# Fresh install (clean npm dependencies)
python3 start_kg_rag.py --fresh

# Use custom config
python3 start_kg_rag.py --config /path/to/config.yaml
```

### 2.4 Stopping the System

There are several ways to stop the KG RAG system properly:

#### Method 1: Using the Stop Script (Recommended)

The `stop_kg_rag.sh` script safely terminates all running services:

```bash
cd /v2.0-beta
./stop_kg_rag.sh
```

**What it does:**
- Finds and stops the Backend API (Python process on port 8002)
- Stops the Frontend dev server (Node/npm process on port 8081)
- Stops the DB Management API (Node process on port 8013)
- Kills any remaining processes on the configured ports

**Expected output:**
```
=========================================
  Stopping KG RAG System
=========================================
Backend stopped
Frontend stopped
=========================================
  KG RAG System Stopped!
=========================================
```

#### Method 2: Ctrl+C in Terminal

If you started the system with `start_kg_rag.py` in the foreground:

1. Press `Ctrl+C` in the terminal
2. The script will catch the signal and gracefully shutdown all services
3. You'll see: `[INFO] Received signal 2, shutting down...`

#### Method 3: Stopping Individual Services

If you need to stop/restart a specific service:

**Stop Backend only:**
```bash
# Find PID
lsof -Pi :8002 -sTCP:LISTEN
# Kill process
kill <PID>
```

**Stop Frontend only:**
```bash
# Find PID
lsof -Pi :8081 -sTCP:LISTEN
# Kill process
kill <PID>
```

**Stop DB Management API only:**
```bash
# Find PID
lsof -Pi :8013 -sTCP:LISTEN
# Kill process
kill <PID>
```

#### Method 4: Force Stop (If Services Hang)

If normal stopping doesn't work:

```bash
# Kill all KG RAG related processes
pkill -f "pgvector_api.py"
pkill -f "npm run dev"
pkill -f "db-management-api"

# Or force kill specific ports
kill -9 $(lsof -Pi :8002 -sTCP:LISTEN -t) 2>/dev/null
kill -9 $(lsof -Pi :8081 -sTCP:LISTEN -t) 2>/dev/null
kill -9 $(lsof -Pi :8013 -sTCP:LISTEN -t) 2>/dev/null
```

#### Verifying Services Are Stopped

Check that all ports are free:

```bash
# Check all KG RAG ports
for port in 8002 8081 8013; do
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Port $port: STILL IN USE"
    lsof -Pi :$port -sTCP:LISTEN
  else
    echo "Port $port: FREE"
  fi
done
```

**Expected output when fully stopped:**
```
Port 8002: FREE
Port 8081: FREE
Port 8013: FREE
```

#### Post-Shutdown Cleanup (Optional)

After stopping, you may want to clean up log files:

```bash
# Remove log files (optional)
rm -f backend.log frontend.log db-api.log

# Or archive them
tar -czf logs-$(date +%Y%m%d-%H%M%S).tar.gz *.log
rm -f *.log
```

#### Restarting After Stop

To restart the system after stopping:

```bash
# Standard restart
python3 start_kg_rag.py

# Restart with fresh npm install (if frontend issues)
python3 start_kg_rag.py --fresh

# Skip Ollama check (if already verified)
python3 start_kg_rag.py --skip-ollama
```

---

## 3. WebUI Tabs and Functionality

The WebUI is accessible at `http://localhost:8081` and provides four main tabs:

### 3.1 Query Tab

**Purpose**: Search the knowledge graph using natural language queries.

#### Interface Elements:

| Element | Description |
|---------|-------------|
| Query Input | Large text area (20px font) for entering questions |
| Query Mode | Select search strategy: Semantic, Entity-lookup, or Graph-traversal |
| Detail Level | Select response depth: Quick, Balanced, Comprehensive, Ultra Deep |
| Submit Button | Send query to backend |
| Response Area | Display formatted answer with citations |

#### Query Modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Semantic** (default) | Vector similarity + keyword fallback | General queries |
| **Entity-lookup** | Entity-focused search | Specific entity questions |
| **Graph-traversal** | Relationship graph search | Connection analysis |

#### Detail Levels:

| Level | Target Words | Description |
|-------|--------------|-------------|
| **Quick** | ~300 | Brief summary with key points |
| **Balanced** (default) | ~800 | Moderate detail with structure |
| **Comprehensive** | ~1500 | In-depth analysis with sections |
| **Ultra Deep** | ~3000+ | Academic/research level with full citations |

### 3.2 Query + File Tab

**Purpose**: Query specific documents alongside the knowledge graph.

#### Additional Features:

| Feature | Description |
|---------|-------------|
| File Upload | Select specific documents to query |
| Document Context | Combines uploaded file content with KG search |
| Same Query Options | All modes and detail levels available |

### 3.3 Ingest Tab

**Purpose**: Upload and index documents into the knowledge graph.

#### Upload Methods:

| Method | Description |
|--------|-------------|
| **Files** | Select multiple individual files |
| **Folder** | Upload entire directory structure |

#### Supported File Types:

- `.txt` - Plain text files
- `.md` - Markdown files
- `.pdf` - PDF documents
- `.doc`, `.docx` - Microsoft Word documents
- `.html` - HTML files
- `.csv` - CSV data files

#### Ingestion Features:

| Feature | Description |
|---------|-------------|
| Auto-Backup | Create database backup every N files |
| Resume Upload | Continue interrupted uploads |
| Progress Tracking | Real-time upload progress |
| Database Stats | View current database statistics |
| Backup/Restore | Manual database backup and restore |

#### Database Management Panel:

| Function | Description |
|----------|-------------|
| Create Backup | Save current database state |
| Restore Backup | Restore from previous backup |
| View Stats | Database entity/relationship counts |
| Clear Database | Remove all data (with confirmation) |

### 3.4 Config Tab

**Purpose**: Configure LLM providers and system settings.

#### LLM Provider Configuration:

| Provider | Setting | Description |
|----------|---------|-------------|
| **DeepSeek** | API Key | Primary LLM provider |
| **DeepSeek** | Model | Model selection (default: deepseek-chat) |
| **MiniMax** | API Key | Fallback LLM provider |
| **MiniMax** | Model | Model selection (default: minimax-m2.7) |

#### Configuration Options:

| Option | Description |
|--------|-------------|
| Primary Provider | Select main LLM (DeepSeek or MiniMax) |
| Enable Fallback | Automatically use fallback on failure |
| Embedding Model | Configure Ollama embedding model |

---

## 4. File Ingestion and Database Indexing

### 4.1 Ingestion Workflow

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│ File Upload │ -> │ Text Extract │ -> │  Chunking   │ -> │  Embedding  │
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
                                                                  │
┌─────────────┐    ┌──────────────┐    ┌─────────────┐           │
│ Knowledge   │ <- │ Relationship │ <- │   Entity    │ <-  Embedding  │
│   Graph     │    │ Extraction   │    │ Extraction  │
└─────────────┘    └──────────────┘    └─────────────┘
```

### 4.2 Indexing Process

#### Step 1: Document Upload
- File is uploaded to backend via `/api/v1/documents/upload`
- File size limit: 200MB per file
- Supported formats extracted to plain text

#### Step 2: Text Extraction
| Format | Extraction Method |
|--------|-------------------|
| PDF | PDF text extraction |
| DOCX | Word document parser |
| TXT/MD | Direct text reading |
| HTML | HTML-to-text conversion |

#### Step 3: Text Chunking
- Document split into chunks (default: 1200 tokens)
- Overlap between chunks (default: 100 tokens)
- Preserves context across chunk boundaries

#### Step 4: Embedding Generation
```python
# Using Ollama nomic-embed-text
embeddings = get_ollama_embedding(text_chunk)
# Output: 768-dimensional vector
```

#### Step 5: Entity Extraction
- LLM extracts named entities from text
- Entities stored in PostgreSQL with metadata
- Relationships between entities identified

#### Step 6: Knowledge Graph Construction
- Entity nodes created with properties
- Relationship edges connected
- Graph stored in PostgreSQL with pgvector

### 4.3 Incremental Indexing

The system supports incremental updates:

| Feature | Description |
|---------|-------------|
| Duplicate Detection | Checks for existing documents |
| Resume Capability | Continue interrupted uploads |
| Session Tracking | Maintains upload state |
| Auto-Backup | Backup every N files (configurable) |

### 4.4 Database Schema

| Table | Purpose |
|-------|---------|
| `entities` | Named entities (people, organizations, concepts) |
| `relationships` | Connections between entities |
| `chunks` | Text chunks with vector embeddings |
| `documents` | Document metadata and status |
| `upload_failures` | Failed upload tracking |

---

## 5. Query Search Modes and Workflow

### 5.1 Query Processing Workflow

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ User Query   │ -> │ Embedding    │ -> │ Vector Search│ -> │  Reranking   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                      │
┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│   Response   │ <- │  LLM Generate│ <- │ Context Build│ <------------┘
│  (Answer)    │    │              │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

### 5.2 Search Modes Detail

> **Naming Note:** The search modes have been renamed to better reflect their functionality:
> - `Hybrid` → `Semantic` (semantic similarity search)
> - `Local` → `Entity-lookup` (entity-focused search)
> - `Global` → `Graph-traversal` (relationship graph search)

#### Semantic Mode (Default)

Semantic mode (previously called "Hybrid") combines vector similarity search with keyword fallback and reranking for optimal semantic matching.

**Workflow Diagram:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SEMANTIC SEARCH MODE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: Query Embedding                                                │
│  ┌─────────────────┐                                                    │
│  │  User Query     │ ──> nomic-embed-text ──> 768-dim vector           │
│  │  "What is HBM?" │                                                    │
│  └─────────────────┘                                                    │
│                          │                                              │
│                          ▼                                              │
│  STEP 2: Vector Similarity Search (Initial Retrieval)                   │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  SELECT content, source, 1 - (embedding <=> query_vec)      │       │
│  │    AS similarity                                           │       │
│  │  FROM chunks                                               │       │
│  │  WHERE 1 - (embedding <=> query_vec) > 0.2                 │       │
│  │  ORDER BY similarity DESC                                  │       │
│  │  LIMIT 40 (initial_top_k)                                  │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                          │                                              │
│                          ▼                                              │
│  STEP 3: Results Found?                                                 │
│              ┌───────────┴───────────┐                                 │
│              ▼                       ▼                                 │
│         [Yes - >0]              [No - 0 results]                       │
│              │                       │                                 │
│              ▼                       ▼                                 │
│  STEP 4a: Reranking      STEP 4b: Keyword Fallback                    │
│  ┌──────────────────┐    ┌──────────────────────────────────┐        │
│  │ Semantic Reranker  │    │ Extract keywords from query      │        │
│  │                  │    │ Remove stop words                │        │
│  │ Score = α·vector │    │ Search: content ILIKE '%word%'   │        │
│  │        + β·BM25  │    │ LIMIT 10 per keyword             │        │
│  │                  │    │ Combine results                  │        │
│  │ α=0.7, β=0.3     │    └──────────────────────────────────┘        │
│  └──────────────────┘                                                   │
│                          │                                              │
│                          ▼                                              │
│  STEP 5: Final Selection                                                │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  Sort by rerank_score DESC                                  │       │
│  │  Deduplicate by content                                     │       │
│  │  Return top_k (default: 15)                                 │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                          │                                              │
│                          ▼                                              │
│  STEP 6: Context Building                                               │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  Combine top chunks with format:                            │       │
│  │  [1] Source: filename                                       │       │
│  │  Content: chunk text                                        │       │
│  │  ---                                                        │       │
│  │  [2] Source: filename                                       │       │
│  │  Content: chunk text                                        │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Technical Details:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| `initial_top_k` | 40 | Chunks retrieved for reranking |
| `final_top_k` | 15 | Chunks after reranking |
| `match_threshold` | 0.2 | Minimum cosine similarity |
| `vector_weight` | 0.7 | Weight for vector similarity |
| `keyword_weight` | 0.3 | Weight for BM25 keyword score |
| `distance_metric` | Cosine | pgvector distance calculation |

**When to Use:**
- General knowledge questions
- When you're unsure if query matches exactly
- Best overall accuracy

---

#### Entity-lookup Mode

Entity-lookup mode (previously called "Local") performs entity-focused search, looking for specific mentions of entities within their context windows.

**Workflow Diagram:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                          ENTITY-LOOKUP SEARCH MODE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: Entity Extraction from Query                                   │
│  ┌─────────────────┐                                                    │
│  │  User Query     │ ──> LLM/NER extraction                            │
│  │  "What did John│    Entities: ["John Smith", "Apple Inc"]           │
│  │   Smith say     │                                                    │
│  │   about Apple?" │                                                    │
│  └─────────────────┘                                                    │
│                          │                                              │
│                          ▼                                              │
│  STEP 2: Entity Lookup in Database                                      │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  SELECT entity_name, entity_type, chunk_ids                │       │
│  │  FROM entities                                              │       │
│  │  WHERE entity_name ILIKE '%john smith%'                     │       │
│  │     OR entity_name ILIKE '%apple inc%'                      │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                          │                                              │
│                          ▼                                              │
│  STEP 3: Retrieve Entity Context Chunks                                 │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  FOR EACH matched entity:                                   │       │
│  │                                                             │       │
│  │  Get chunks where entity appears:                           │       │
│  │    SELECT c.*, e.entity_name                                │       │
│  │    FROM chunks c                                            │       │
│  │    JOIN entity_mentions em ON c.id = em.chunk_id           │       │
│  │    WHERE em.entity_id = <entity_id>                         │       │
│  │    ORDER BY c.document_order                                │       │
│  │                                                             │       │
│  │  Get context window (±2 chunks around entity):              │       │
│  │    - Include chunks before and after                        │       │
│  │    - Maintain document flow                                 │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                          │                                              │
│                          ▼                                              │
│  STEP 4: Vector Refinement (Optional)                                   │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  If many chunks found, apply vector similarity:             │       │
│  │                                                             │       │
│  │  query_embedding <=> chunk_embedding                        │       │
│  │  ORDER BY similarity DESC                                   │       │
│  │  LIMIT 20                                                   │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                          │                                              │
│                          ▼                                              │
│  STEP 5: Score and Rank by Entity Relevance                             │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  For each chunk:                                            │       │
│  │                                                             │       │
│  │  score = entity_mention_count × 0.4                         │       │
│  │        + context_relevance × 0.3                            │       │
│  │        + vector_similarity × 0.3                            │       │
│  │                                                             │       │
│  │  (Prioritizes chunks with more entity mentions)             │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                          │                                              │
│                          ▼                                              │
│  STEP 6: Build Entity-Focused Context                                   │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  Format with entity highlighting:                           │       │
│  │                                                             │       │
│  │  Related to: John Smith, Apple Inc                          │       │
│  │  ──────────────────────────────────────                     │       │
│  │  [1] From: annual_report_2024.pdf                           │       │
│  │      Context: "John Smith stated that Apple Inc..."         │       │
│  │                                                             │       │
│  │  [2] From: meeting_notes.pdf                                │       │
│  │      Context: "According to John Smith..."                  │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Technical Details:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| `context_window` | ±2 chunks | Chunks around entity mention |
| `max_entity_chunks` | 20 | Maximum chunks per entity |
| `entity_weight` | 0.4 | Weight for mention frequency |
| `context_weight` | 0.3 | Weight for context relevance |
| `vector_weight` | 0.3 | Weight for semantic similarity |
| `min_mentions` | 1 | Minimum entity mentions required |

**Database Queries:**

```sql
-- Find entities matching query
SELECT id, name, description 
FROM entities 
WHERE name ILIKE '%query_term%';

-- Get chunks containing entity
SELECT c.*, em.mention_count
FROM chunks c
JOIN entity_mentions em ON c.id = em.chunk_id
WHERE em.entity_id = :entity_id
ORDER BY em.mention_count DESC;
```

**When to Use:**
- Questions about specific people, organizations, or concepts
- "What did [Person] say about [Topic]?"
- "What is [Entity]'s position on [Subject]?"
- Finding all mentions of a specific entity

---

#### Graph-traversal Mode

Graph-traversal mode (previously called "Global") performs relationship-focused search, traversing the knowledge graph to find connections between entities.

**Workflow Diagram:**
```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GRAPH-TRAVERSAL SEARCH MODE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  STEP 1: Relationship Pattern Extraction                                │
│  ┌─────────────────┐                                                    │
│  │  User Query     │ ──> Parse for relationship patterns               │
│  │  "How is TSMC   │                                                    │
│  │   connected to  │    Pattern: CONNECTION(EntityA, EntityB)          │
│  │   NVIDIA?"      │    Entities: ["TSMC", "NVIDIA"]                    │
│  └─────────────────┘                                                    │
│                          │                                              │
│                          ▼                                              │
│  STEP 2: Graph Traversal - Find Paths                                   │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  Find direct relationships:                                 │       │
│  │                                                             │       │
│  │  SELECT r.*, e1.name as source, e2.name as target          │       │
│  │  FROM relationships r                                       │       │
│  │  JOIN entities e1 ON r.source_id = e1.id                   │       │
│  │  JOIN entities e2 ON r.target_id = e2.id                   │       │
│  │  WHERE (e1.name ILIKE '%tsmc%' AND e2.name ILIKE '%nvidia%')│       │
│  │     OR (e1.name ILIKE '%nvidia%' AND e2.name ILIKE '%tsmc%')│       │
│  └─────────────────────────────────────────────────────────────┘       │
│                          │                                              │
│                          ▼                                              │
│  STEP 3: Multi-Hop Path Discovery (if no direct link)                   │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  Find 2-hop paths:                                          │       │
│  │                                                             │       │
│  │  TSMC --[supplies]--> EntityX --[partners_with]--> NVIDIA   │       │
│  │                                                             │       │
│  │  Query:                                                     │       │
│  │  WITH RECURSIVE paths AS (                                  │       │
│  │    SELECT source_id, target_id, 1 as hops,                  │       │
│  │           ARRAY[source_id] as path                          │       │
│  │    FROM relationships                                       │       │
│  │    WHERE source_id = (SELECT id FROM entities               │       │
│  │                        WHERE name ILIKE '%tsmc%')          │       │
│  │    UNION ALL                                                │       │
│  │    SELECT r.source_id, r.target_id, p.hops + 1,             │       │
│  │           p.path || r.source_id                             │       │
│  │    FROM relationships r                                     │       │
│  │    JOIN paths p ON r.source_id = p.target_id               │       │
│  │    WHERE p.hops < 3 AND NOT r.target_id = ANY(p.path)      │       │
│  │  )                                                          │       │
│  │  SELECT * FROM paths                                        │       │
│  │  WHERE target_id = (SELECT id FROM entities                │       │
│  │                      WHERE name ILIKE '%nvidia%')          │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                          │                                              │
│                          ▼                                              │
│  STEP 4: Retrieve Relationship Context                                  │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  For each relationship found:                               │       │
│  │                                                             │       │
│  │  Get supporting chunks:                                     │       │
│  │    SELECT c.*, r.relationship_type                         │       │
│  │    FROM chunks c                                            │       │
│  │    JOIN relationship_evidence re ON c.id = re.chunk_id     │       │
│  │    WHERE re.relationship_id = :rel_id                       │       │
│  │                                                             │       │
│  │  Evidence types:                                            │       │
│  │    - Direct statement                                       │       │
│  │    - Implicit connection                                    │       │
│  │    - Temporal relationship                                  │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                          │                                              │
│                          ▼                                              │
│  STEP 5: Relationship Graph Scoring                                     │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  Score paths by:                                            │       │
│  │                                                             │       │
│  │  path_score = Σ(edge_strength) / hops                       │       │
│  │                                                             │       │
│  │  Where edge_strength factors:                               │       │
│  │    - relationship_confidence (0-1)                        │       │
│  │    - evidence_count (number of supporting chunks)         │       │
│  │    - recency (if temporal data available)                 │       │
│  │                                                             │       │
│  │  Prefer: fewer hops, higher confidence, more evidence     │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                          │                                              │
│                          ▼                                              │
│  STEP 6: Build Relationship Context                                     │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  Format with relationship paths:                            │       │
│  │                                                             │       │
│  │  Connection: TSMC → NVIDIA                                  │       │
│  │  ═══════════════════════════════════════                    │       │
│  │                                                             │       │
│  │  Path 1 (Direct):                                           │       │
│  │  TSMC --[supplier_of]--> NVIDIA                             │       │
│  │    Evidence: "TSMC manufactures chips for NVIDIA..."        │       │
│  │                                                             │       │
│  │  Path 2 (2-hop):                                            │       │
│  │  TSMC --[competitor_of]--> Samsung                          │       │
│  │          --[partner_with]--> NVIDIA                         │       │
│  │    Evidence: "Samsung and NVIDIA announced partnership..."  │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Technical Details:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| `max_hops` | 3 | Maximum relationship chain length |
| `min_confidence` | 0.5 | Minimum relationship confidence |
| `max_paths` | 5 | Maximum alternative paths to return |
| `path_scoring` | weighted | Based on confidence and evidence |
| `edge_weight` | 0.6 | Weight for direct relationships |
| `multi_hop_penalty` | 0.3 | Reduction per additional hop |

**Relationship Types Tracked:**

| Type | Example | Strength |
|------|---------|----------|
| `supplier_of` | TSMC → NVIDIA | 0.9 |
| `partner_with` | CompanyA → CompanyB | 0.8 |
| `competitor_of` | AMD → Intel | 0.7 |
| `owns` | Parent → Subsidiary | 0.9 |
| `founded_by` | Company → Person | 0.8 |
| `collaborates_with` | OrgA → OrgB | 0.7 |

**Database Queries:**

```sql
-- Direct relationship lookup
SELECT r.*, e1.name as source_name, e2.name as target_name
FROM relationships r
JOIN entities e1 ON r.source_id = e1.id
JOIN entities e2 ON r.target_id = e2.id
WHERE (e1.name ILIKE '%entity_a%' AND e2.name ILIKE '%entity_b%')
   OR (e1.name ILIKE '%entity_b%' AND e2.name ILIKE '%entity_a%');

-- Multi-hop path finding with CTE
WITH RECURSIVE paths AS (
  SELECT source_id, target_id, 1 as hops,
         ARRAY[source_id] as path,
         relationship_type
  FROM relationships
  WHERE source_id = :start_entity_id
  UNION ALL
  SELECT r.source_id, r.target_id, p.hops + 1,
         p.path || r.source_id,
         p.relationship_type || ' -> ' || r.relationship_type
  FROM relationships r
  JOIN paths p ON r.source_id = p.target_id
  WHERE p.hops < 3 
    AND NOT r.target_id = ANY(p.path)
)
SELECT * FROM paths WHERE target_id = :end_entity_id;
```

**When to Use:**
- Questions about connections between entities
- "How is [Entity A] related to [Entity B]?"
- "What is the relationship between X and Y?"
- Finding indirect connections in the knowledge graph
- Understanding organizational structures
- Supply chain or partnership analysis

---

#### Mode Comparison Summary

| Aspect | Hybrid | Local | Global |
|--------|--------|-------|--------|
| **Primary Focus** | Semantic similarity | Entity mentions | Relationship paths |
| **Search Strategy** | Vector + Keyword fallback | Entity lookup + context | Graph traversal |
| **Best For** | General questions | Specific entity info | Connection discovery |
| **Context Source** | Top-k similar chunks | Entity context windows | Relationship paths |
| **Ranking Method** | Hybrid score (vector+BM25) | Mention frequency | Path strength |
| **Query Example** | "What is HBM?" | "What did John say?" | "How is A connected to B?" |
| **Response Type** | Comprehensive answer | Entity-focused | Relationship map |

### 5.3 Response Detail Levels

#### Quick (~300 words)
```
• Brief answer
• Key points only
• Fast response time
```

#### Balanced (~800 words)
```
Executive Summary
• Overview paragraph

Key Points
• Bullet point 1
• Bullet point 2

Conclusion
• Summary

References
[1] Source 1
[2] Source 2
```

#### Comprehensive (~1500 words)
```
Title

Executive Summary
• Multi-paragraph overview

Section 1: Topic A
• Detailed analysis
• Supporting evidence

Section 2: Topic B
• Detailed analysis
• Supporting evidence

Conclusion
• Summary findings

References
[1-10] Full citations
```

#### Ultra Deep (~3000+ words)
```
Title

Executive Summary (250 words)
• Comprehensive overview

1. Introduction
   1.1 Background
   1.2 Scope

2. Main Analysis
   2.1 Subsection A (150 words)
   2.2 Subsection B (150 words)
   ...

3. Detailed Findings
   (Multiple subsections)

4. Implications

5. Conclusion (300 words)

References
• Complete bibliography
• All sources cited

Sources for Verification
• Chunk references
• Confidence scores
```

### 5.4 Two-Pass Generation (Ultra Deep)

For Ultra Deep responses that exceed token limits:

1. **First Pass**: Generate content with max tokens (8192)
2. **Truncation Detection**: Check if conclusion/references are complete
3. **Second Pass**: Continue from truncated point with context
4. **Reference Auto-Generation**: Programmatically generate complete references

---

## 6. Configuration and LLM Setup

### 6.1 Configuration Files

| File | Purpose |
|------|---------|
| `kgrag_config.yaml` | Main system configuration |
| `backend/.env` | API keys and secrets |
| `frontend/src/config.ts` | Frontend settings |

### 6.2 LLM Provider Setup

#### DeepSeek (Primary)

```yaml
# In kgrag_config.yaml or via Config Tab
llm:
  primary_provider: "deepseek"
  deepseek:
    api_key: "your-deepseek-api-key"
    model: "deepseek-chat"
    base_url: "https://api.deepseek.com/v1"
```

#### MiniMax (Fallback)

```yaml
# In kgrag_config.yaml or via Config Tab
llm:
  fallback_provider: "minimax"
  minimax:
    api_key: "your-minimax-api-key"
    model: "minimax-m2.7"
    base_url: "https://api.minimax.chat/v1"
```

### 6.3 Ollama Configuration

Required for embeddings:

```bash
# Install Ollama (if not installed)
# macOS: https://ollama.com/download

# Start Ollama
ollama serve

# Pull required model
ollama pull nomic-embed-text
```

Configuration in `kgrag_config.yaml`:
```yaml
ollama:
  enabled: true
  host: "http://localhost"
  port: 11434
  required_models:
    - "nomic-embed-text"
  check_on_startup: true
```

### 6.4 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `KGRAG_BACKEND_PORT` | Backend API port | `8002` |
| `KGRAG_FRONTEND_PORT` | WebUI port | `8081` |
| `KGRAG_OLLAMA_HOST` | Ollama server URL | `http://localhost` |
| `KGRAG_LOG_LEVEL` | Logging level | `INFO` |
| `MINIMAX_API_KEY` | MiniMax API key | `sk-...` |

### 6.5 PostgreSQL Connection

The backend connects to PostgreSQL with pgvector:

```python
# Default connection (from backend/pgvector_api.py)
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5433"))
POSTGRES_DB = os.environ.get("POSTGRES_DB", "lightrag")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "password")
```

Set via environment:
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5433
export POSTGRES_DB=lightrag
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password
```

---

## 7. Troubleshooting

### 7.1 Common Issues

#### Issue: "Required Ollama models not found"
```
[✗] Required Ollama models not found: nomic-embed-text
```

**Solution:**
```bash
ollama pull nomic-embed-text
```

#### Issue: "Port already in use"
```
[✗] Port 8002 is already in use!
```

**Solution:**
```bash
# Find and kill the process
lsof -Pi :8002
kill <PID>

# Or change ports in kgrag_config.yaml
```

#### Issue: "DB Management API Not Running"
```
⚠️ Database Management API Not Running
```

**Solution:**
```bash
# Start manually
cd frontend
node scripts/db-management-api.cjs

# Or restart the system
./stop_kg_rag.sh
python3 start_kg_rag.py
```

#### Issue: Frontend node_modules corrupted
```
ERR_MODULE_NOT_FOUND
```

**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### 7.2 Log Files

| Log File | Purpose |
|----------|---------|
| `backend.log` | Backend API logs |
| `frontend.log` | Vite dev server logs |
| `db-api.log` | DB Management API logs |
| `pgvector_api.log` | pgvector-specific logs |

### 7.3 Health Check Commands

```bash
# Backend health
curl http://localhost:8002/health

# Ollama status
curl http://localhost:11434/api/tags

# Database API
curl http://localhost:8013/health
```

### 7.4 Support

For additional help:
1. Check log files for error details
2. Verify all services are running with `lsof -Pi :<port>`
3. Ensure PostgreSQL with pgvector is accessible
4. Confirm Ollama has the required model pulled

---

## Appendix A: Quick Reference

### Startup Commands
```bash
# Start all services
python3 start_kg_rag.py

# Start with fresh dependencies
python3 start_kg_rag.py --fresh

# Skip Ollama check
python3 start_kg_rag.py --skip-ollama
```

### Stop Commands
```bash
# Stop all services (recommended)
./stop_kg_rag.sh

# Or press Ctrl+C in the terminal running start_kg_rag.py

# Force stop if hanging
pkill -f "pgvector_api.py"
pkill -f "npm run dev"

# Verify all stopped
for port in 8002 8081 8013; do
  lsof -Pi :$port -sTCP:LISTEN
done
```

### Access URLs
| Service | URL |
|---------|-----|
| WebUI | http://localhost:8081 |
| Backend API | http://localhost:8002 |
| Backend Docs | http://localhost:8002/docs |
| DB API | http://localhost:8013 |

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/chat` | POST | Main chat/query endpoint |
| `/api/v1/documents/upload` | POST | Upload documents |
| `/api/v1/entities` | GET | List entities |
| `/api/v1/relations` | GET | List relationships |
| `/health` | GET | System health check |

---

*Document Version: v2.0-beta*  
*Last Updated: March 29, 2026*
