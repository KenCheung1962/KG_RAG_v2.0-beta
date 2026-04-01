# Database Setup Guide for KG RAG v2.0-beta

This guide explains how to set up the PostgreSQL database for KG RAG v2.0-beta. The setup is **self-contained** within the v2.0-beta directory.

## Quick Start

### Option 1: Using Docker (Recommended)

```bash
# 1. Start PostgreSQL with Docker Compose
cd /Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta
docker-compose up -d

# 2. Wait for PostgreSQL to be ready (about 10 seconds)
sleep 10

# 3. Initialize the database schema
cd backend
python3 init_database.py

# 4. Verify setup
python3 init_database.py --verify
```

### Option 2: Using Existing PostgreSQL

If you already have PostgreSQL installed:

```bash
# 1. Create database manually (or use init_database.py)
createdb -U postgres kg_rag

# 2. Enable pgvector extension (must be installed)
psql -U postgres -d kg_rag -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 3. Initialize schema
cd backend
python3 init_database.py
```

## File Structure

```
v2.0-beta/
├── docker-compose.yml          # Docker setup (self-contained)
├── backend/
│   ├── schema.sql              # Database schema (copied here)
│   ├── init_database.py        # Initialization script
│   └── migrations/             # Schema migrations
│       ├── add_relationship_embeddings.sql
│       └── ...
└── DATABASE_SETUP.md           # This file
```

## Database Schema

The schema is defined in `backend/schema.sql` and includes:

### Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| **entities** | Knowledge graph nodes | entity_id, name, type, embedding (768d) |
| **relationships** | Knowledge graph edges | relationship_id, source_id, target_id, type, embedding (768d) |
| **chunks** | Text chunks for RAG | chunk_id, content, embedding (768d), entity_id |

### Indexes

| Index | Type | Purpose |
|-------|------|---------|
| idx_entities_embedding | HNSW (vector) | Fast entity similarity search |
| idx_relationships_embedding | HNSW (vector) | Fast relationship similarity search |
| idx_chunks_embedding | HNSW (vector) | Fast chunk similarity search |
| idx_entities_type | B-tree | Filter by entity type |
| idx_relationships_source/target | B-tree | Graph traversal |

### Extensions

- **pgvector**: Vector similarity search (768 dimensions)
- **Full-text search**: GIN indexes on entity names and chunk content

## Management Commands

### Start/Stop PostgreSQL

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Stop and remove data (DANGER)
docker-compose down -v
```

### Initialize/Reset Database

```bash
cd backend

# Initialize everything (create DB, schema, migrations)
python3 init_database.py

# Check status
python3 init_database.py --status

# Verify setup
python3 init_database.py --verify

# Apply migrations only
python3 init_database.py --migrate

# Reset database (DANGER: deletes all data)
python3 init_database.py --reset

# Force re-initialize
python3 init_database.py --force
```

### Connection Information

| Parameter | Value |
|-----------|-------|
| Host | `localhost` |
| Port | `5432` (PostgreSQL), `6432` (PgBouncer) |
| Database | `kg_rag` |
| User | `postgres` |
| Password | `postgres` |

Connection string:
```
postgresql://postgres:postgres@localhost:5432/kg_rag
```

## Migrations

### What Are Migrations?

Migrations are incremental schema changes applied after the initial setup:

1. **Schema migrations** (`.sql` files): Add columns, indexes, tables
2. **Data migrations** (`.py` files): Transform existing data

### Existing Migrations

| Migration | Purpose |
|-----------|---------|
| `add_relationship_embeddings.sql` | Add embedding column to relationships table |

### Apply Migrations

```bash
# Automatically applied during init
python3 init_database.py

# Apply migrations only
python3 init_database.py --migrate
```

### Create New Migration

1. **Create SQL file** (`backend/migrations/add_feature.sql`):
```sql
-- Add new column
ALTER TABLE entities 
ADD COLUMN IF NOT EXISTS new_field VARCHAR(255);

-- Create index
CREATE INDEX IF NOT EXISTS idx_entities_new_field 
ON entities(new_field);
```

2. **Apply migration**:
```bash
python3 init_database.py --migrate
```

## Troubleshooting

### PostgreSQL won't start

```bash
# Check logs
docker-compose logs postgres

# Check if port 5432 is in use
lsof -i :5432

# Use different port
docker-compose down
# Edit docker-compose.yml, change "5432:5432" to "5433:5432"
docker-compose up -d
```

### Schema not initialized

```bash
# Check if schema file exists
ls -la backend/schema.sql

# Force re-initialize
python3 init_database.py --force
```

### PgBouncer connection issues

```bash
# Connect directly to PostgreSQL (skip PgBouncer)
psql postgresql://postgres:postgres@localhost:5432/kg_rag

# Or disable PgBouncer in docker-compose.yml
# Comment out the pgbouncer service
```

### Vector extension not available

```bash
# Check if pgvector is installed in container
docker-compose exec postgres psql -U postgres -d kg_rag -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# If missing, the Docker image may be wrong
# Make sure you're using 'ankane/pgvector:latest'
```

## Advanced Configuration

### Custom PostgreSQL Configuration

Create `backend/postgresql.conf` and mount it:

```yaml
# docker-compose.yml
services:
  postgres:
    volumes:
      - ./backend/postgresql.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

### Environment Variables

```bash
# Use different credentials
export PGHOST=localhost
export PGPORT=5432
export PGDATABASE=kg_rag
export PGUSER=postgres
export PGPASSWORD=postgres

# Then run
python3 init_database.py
```

## Data Persistence

Data is stored in a Docker volume named `kg_rag_postgres_data`.

### Backup Data

```bash
# Backup
docker-compose exec postgres pg_dump -U postgres kg_rag > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres kg_rag < backup.sql
```

### Reset Everything

```bash
# Stop and remove all data
docker-compose down -v

# Start fresh
docker-compose up -d
python3 backend/init_database.py
```

## Verification Checklist

After setup, verify:

- [ ] PostgreSQL container is running: `docker-compose ps`
- [ ] Database exists: `python3 init_database.py --verify`
- [ ] Tables created: `python3 init_database.py --status`
- [ ] pgvector extension enabled
- [ ] Can connect from application

## Migration from proj_ph2

If you were using the schema from `proj_ph2/source/postgres/init.sql`:

1. The schema has been copied to `v2.0-beta/backend/schema.sql`
2. Use `init_database.py` instead of direct SQL execution
3. All migrations are now in `v2.0-beta/backend/migrations/`

The v2.0-beta is now **fully self-contained**!
