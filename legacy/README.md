# Legacy Scripts

This folder contains unused and legacy scripts that are no longer part of the core v2.0-beta application.

## Contents

### backend/
- **app.py** - Legacy Flask/FastAPI application (replaced by pgvector_api.py)
- **manage_embeddings.py** - Legacy embedding management with hardcoded absolute paths
- **migrations/** - One-time database migration scripts (already applied):
  - `add_relationship_embeddings.sql` - SQL to add embedding column
  - `apply_relationship_embeddings.py` - Applies SQL migration
  - `generate_relationship_embeddings.py` - Generates embeddings for existing relationships
- **tests/** - Legacy test scripts with external path references

### scripts/
- **embedding_watchdog.py** - Legacy cron-based embedding processor with hardcoded paths
- **manage_embeddings.py** - Legacy management script with hardcoded paths
- **auto_start_entity_backfill.py** - Legacy backfill script with hardcoded paths

## Status

These scripts are **NOT needed** for normal operations. They were used for:
1. Initial database setup and migrations (completed)
2. Embedding generation for existing data (completed)
3. Legacy API server (replaced)

The main application (`backend/pgvector_api.py`) is now fully self-contained and does not reference these files.
