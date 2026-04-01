# Restart Backend to Apply Fixes

## Problem
The backend is still running the old code that returns source count instead of filenames.

## Solution: Restart the Backend

### Step 1: Stop Current Backend
```bash
# Find the backend process
lsof -i :8002

# Or use this command to find Python processes
ps aux | grep pgvector_api

# Kill the process (replace <PID> with the actual number)
kill <PID>

# Or force kill if needed
kill -9 <PID>
```

### Step 2: Start New Backend
```bash
cd /Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta/backend
python pgvector_api.py
```

You should see output like:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8002 (Press CTRL+C to quit)
```

### Step 3: Test Query
Run a query in the frontend and check if References now shows filenames like:
```
## References

1. document1.pdf
2. article2.txt
```

## Check Console Logs

Open browser console (F12) and look for:
```
[Query] Raw sources: ["file1.pdf", "file2.pdf"]
[Query] sources type: object
[Query] sources isArray: true
```

If you see `sources type: number`, the backend hasn't been restarted yet.

## Alternative: Use start.sh Script

The start.sh script will automatically start the new backend:

```bash
cd /Users/ken/clawd_workspace/projects/KG_RAG/v2.0-beta
./start.sh
```

Select option 1 for pgvector_api backend.
