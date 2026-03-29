# KG RAG Configuration Guide

## Overview

The KG RAG system now uses a centralized YAML configuration file (`kgrag_config.yaml`) to control all aspects of initialization and startup. This makes it easy to customize ports, timeouts, health check thresholds, and feature flags without modifying the startup scripts.

## Files Overview

| File | Purpose |
|------|---------|
| `kgrag_config.yaml` | Main configuration file (YAML format) |
| `start_kg_rag.sh` | Bash startup script (reads from config) |
| `start_kg_rag.py` | Python startup script (reads from config) |
| `config_loader.py` | Python module for loading config |

## Quick Start

### Using the Configuration

Simply edit `kgrag_config.yaml` to customize settings, then run:

```bash
# Using bash script
./start_kg_rag.sh

# Or using Python script (recommended)
./start_kg_rag.py

# Or with custom config path
./start_kg_rag.py --config /path/to/custom_config.yaml
```

## Configuration Sections

### 1. Services Configuration

Control which services start and on which ports:

```yaml
services:
  backend:
    enabled: true
    port: 8002              # Change if port 8002 is taken
    host: "127.0.0.1"
    script: "pgvector_api.py"
    directory: "backend"
    log_file: "backend.log"
    startup_timeout: 30     # Seconds to wait for startup
    
  frontend:
    enabled: true
    port: 8081              # Change if port 8081 is taken
    host: true              # true = listen on all interfaces
    directory: "frontend"
    log_file: "frontend.log"
    startup_timeout: 15
    auto_install_deps: true # Auto-run npm install if needed
    
  db_management_api:
    enabled: true
    port: 8013
    script: "scripts/db-management-api.cjs"
    directory: "frontend"
    startup_timeout: 10
```

### 2. Ollama Configuration

```yaml
ollama:
  enabled: true
  host: "http://localhost"
  port: 11434             # Default Ollama port
  required_models:
    - "nomic-embed-text"  # Required for embeddings
  check_on_startup: true  # Verify Ollama is running
  auto_pull_models: false # Set true to auto-download models
```

### 3. Database Health Thresholds

Define what constitutes a "healthy" database:

```yaml
database_health:
  # Minimum counts for "healthy" status
  min_entities: 1000
  min_relationships: 1000
  min_chunks: 1000
  min_documents: 10
  
  # Warning thresholds
  warn_entities: 500
  warn_relationships: 500
  warn_chunks: 500
  warn_documents: 5
```

### 4. Proxy Configuration

Vite dev server proxy settings:

```yaml
proxy:
  api:
    path: "/api"
    target_port: 8002
    change_origin: true
    
  health:
    path: "/health"
    target_port: 8002
    
  pgvector:
    path: "/pgvector-api"
    target_port: 8002
    rewrite: true
    
  db_api:
    path: "/db-api"
    target_port: 8013
    rewrite: true
```

### 5. Feature Flags

Enable/disable features:

```yaml
features:
  webui: true
  chat_interface: true
  document_upload: true
  knowledge_graph_view: true
  database_management: true
  backup_restore: true
  upload_failure_tracking: true
  
  # Development features
  hot_reload: true
  debug_mode: false
  verbose_logging: false
```

### 6. Logging Configuration

```yaml
logging:
  level: "INFO"           # DEBUG, INFO, WARN, ERROR
  backend:
    enabled: true
    file: "backend.log"
    max_size: "10MB"
    max_backups: 3
```

### 7. Security Settings

```yaml
security:
  api_key: "static-internal-key"
  cors:
    enabled: true
    origins:
      - "http://localhost:8081"
      
  upload:
    max_file_size_mb: 200
    allowed_extensions: ["pdf", "docx", "txt", "html", "md"]
    blocked_extensions: [".exe", ".bat", ".sh", ".py", ".js"]
```

## Environment Variable Overrides

You can override any configuration value using environment variables:

| Environment Variable | Overrides |
|---------------------|-----------|
| `KGRAG_BACKEND_PORT` | services.backend.port |
| `KGRAG_FRONTEND_PORT` | services.frontend.port |
| `KGRAG_DB_API_PORT` | services.db_management_api.port |
| `KGRAG_OLLAMA_HOST` | ollama.host |
| `KGRAG_OLLAMA_PORT` | ollama.port |
| `KGRAG_LOG_LEVEL` | logging.level |
| `KGRAG_DEBUG_MODE` | features.debug_mode |

### Example: Change Ports via Environment

```bash
# Use different ports
export KGRAG_BACKEND_PORT=9000
export KGRAG_FRONTEND_PORT=9001
./start_kg_rag.sh
```

## Common Customizations

### Change Default Ports

Edit `kgrag_config.yaml`:

```yaml
services:
  backend:
    port: 9000          # Changed from 8002
  frontend:
    port: 9001          # Changed from 8081
  db_management_api:
    port: 9002          # Changed from 8013
```

### Disable Database Management API

```yaml
services:
  db_management_api:
    enabled: false
```

### Lower Health Check Thresholds (for testing)

```yaml
database_health:
  min_entities: 100      # Lower from 1000
  min_relationships: 100
  min_chunks: 100
  min_documents: 1
```

### Enable Debug Logging

```yaml
logging:
  level: "DEBUG"
  
features:
  debug_mode: true
  verbose_logging: true
```

## Using the Python Startup Script

The Python script provides additional features:

```bash
# Basic usage
./start_kg_rag.py

# Use custom config file
./start_kg_rag.py --config /path/to/config.yaml

# Skip Ollama check
./start_kg_rag.py --skip-ollama

# Start only backend
./start_kg_rag.py --backend-only

# Start only frontend
./start_kg_rag.py --frontend-only

# Show help
./start_kg_rag.py --help
```

## Configuration Validation

To validate your configuration:

```python
from config_loader import get_config

config = get_config()
config.print_summary()

# Access specific values
print(f"Backend port: {config.backend_port}")
print(f"Frontend port: {config.frontend_port}")
print(f"Ollama URL: {config.ollama_url}")
```

## Troubleshooting

### Port Already in Use

If you see "Port X is already in use":

1. Find the process: `lsof -Pi :8002`
2. Kill it: `kill <PID>`
3. Or change the port in `kgrag_config.yaml`

### Config Not Loading

If the config file isn't being read:

1. Check file exists: `ls -la kgrag_config.yaml`
2. Validate YAML syntax: `python3 -c "import yaml; yaml.safe_load(open('kgrag_config.yaml'))"`
3. Check file permissions: `chmod 644 kgrag_config.yaml`

### Environment Variables Not Working

Make sure to export variables before running the script:

```bash
# ✓ Correct
export KGRAG_BACKEND_PORT=9000
./start_kg_rag.sh

# ✗ Incorrect (variable not exported to subprocess)
KGRAG_BACKEND_PORT=9000 ./start_kg_rag.sh
```

## Complete Configuration Reference

See the full `kgrag_config.yaml` file for all available options with inline comments explaining each setting.

## Migration from Old Startup

If you were using the old `start.sh`:

1. Copy your custom settings to `kgrag_config.yaml`
2. Update port variables in the config file
3. Use `./start_kg_rag.sh` or `./start_kg_rag.py` instead
4. The old `start.sh` is preserved for reference

## Best Practices

1. **Keep config in version control** - Track changes to `kgrag_config.yaml`
2. **Use environment variables for secrets** - Don't commit API keys
3. **Document custom ports** - If you change ports, document for your team
4. **Test config changes** - Validate YAML before running
5. **Use Python script for debugging** - Better error messages than bash
