# v2.0-beta Self-Contained Setup Summary

## Overview
KG RAG v2.0-beta is now **fully self-contained**. All database schema files and initialization scripts are within the v2.0-beta directory.

## Changes Made

### 1. Schema File Copied
**Source:** `proj_ph2/source/postgres/init.sql`  
**Destination:** `v2.0-beta/backend/schema.sql`

The complete database schema is now local to v2.0-beta.

### 2. New Initialization Script
**File:** `v2.0-beta/backend/init_database.py`

Features:
- ✅ Creates database if it doesn't exist
- ✅ Initializes schema from local `schema.sql`
- ✅ Applies migrations from `migrations/` directory
- ✅ Tracks applied migrations (no re-applying)
- ✅ Verify setup command
- ✅ Reset database command
- ✅ Self-contained (no external dependencies)

### 3. Docker Compose File
**File:** `v2.0-beta/docker-compose.yml`

Features:
- ✅ PostgreSQL with pgvector pre-installed
- ✅ Automatic schema initialization on first run
- ✅ Persistent data volume
- ✅ Optional PgBouncer for connection pooling
- ✅ Health checks

### 4. Documentation
**File:** `v2.0-beta/DATABASE_SETUP.md`

Complete setup guide with:
- Quick start instructions
- Management commands
- Troubleshooting
- Migration guide from proj_ph2

## Quick Start

```bash
# 1. Navigate to v2.0-beta
cd /Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta

# 2. Start PostgreSQL
docker-compose up -d

# 3. Wait for PostgreSQL to be ready
sleep 10

# 4. Initialize database
cd backend
python3 init_database.py

# 5. Verify
python3 init_database.py --verify
```

## File Structure (Self-Contained)

```
v2.0-beta/
├── docker-compose.yml          # Docker setup
├── DATABASE_SETUP.md           # Setup guide
├── SELF_CONTAINED_SETUP.md     # This file
└── backend/
    ├── schema.sql              # Database schema (local copy)
    ├── init_database.py        # Initialization script
    └── migrations/             # Schema migrations
        ├── add_relationship_embeddings.sql
        ├── apply_relationship_embeddings.py
        └── generate_relationship_embeddings.py
```

## No External Dependencies

Before (depended on proj_ph2):
```python
# Old way - depended on external file
sys.path.insert(0, '/Users/ken/clawd_workspace/projects/KG_RAG/proj_ph2/source/postgres')
from client import init_postgres_client
```

After (self-contained):
```python
# New way - everything is local
sys.path.insert(0, str(Path(__file__).parent))
from client import init_postgres_client  # Uses local client.py
```

## Migration Tracking

The initialization script tracks applied migrations:

```sql
-- Migration tracking table (auto-created)
CREATE TABLE _schema_migrations (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

This prevents re-applying the same migration twice.

## Commands Reference

```bash
# Initialize everything
python3 init_database.py

# Check status
python3 init_database.py --status

# Verify setup
python3 init_database.py --verify

# Apply migrations only
python3 init_database.py --migrate

# Reset database (DANGER)
python3 init_database.py --reset

# Force re-initialize
python3 init_database.py --force

# Custom connection
python3 init_database.py --host myhost --port 5433 --password mypass
```

## Docker Management

```bash
# Start PostgreSQL
docker-compose up -d

# View logs
docker-compose logs -f postgres

# Stop
docker-compose down

# Stop and remove data (DANGER)
docker-compose down -v

# Restart
docker-compose restart
```

## Verification

After setup, you should see:

```
✅ Database initialization complete!

📊 Database Status
==================================================

📋 Tables (4):
   • _schema_migrations: 2 rows
   • chunks: 0 rows
   • entities: 0 rows
   • relationships: 0 rows

📂 Applied Migrations (1):
   • add_relationship_embeddings.sql (2026-04-01 10:30)

🔌 Extensions: vector
```

## Benefits

1. **Self-Contained**: No dependencies on proj_ph2 or other external files
2. **Version Control**: Schema is versioned with v2.0-beta code
3. **Reproducible**: Same setup every time with Docker
4. **Trackable**: Migrations are tracked and won't be re-applied
5. **Easy Setup**: One command to initialize everything
