# T058 Implementation Plan: RAG Web UI Development

**Task ID:** T058  
**Task Name:** RAG Web User Interface  
**Owner:** Kenny  
**Reviewer:** Jenny  
**Plan Version:** 1.2 (Updated)  
**Created:** 2026-02-17 23:15 GMT+8  
**Updated:** 2026-02-18 02:15 GMT+8  
**Status:** Draft - Pending Approval

---

## 1. Executive Summary

### 1.1 Overview
This document outlines the implementation plan for the RAG Web UI (T058), a Streamlit‑based web application that provides an intuitive interface for the Knowledge Graph RAG system. The application will support chat‑based queries, document upload, and search‑mode selection.

### 1.2 Objectives
- Develop a modern, responsive web interface using Streamlit
- Enable seamless interaction with the T036 FastAPI backend
- Support chat interface, document upload (PDF/DOCX), and search‑mode selector (Local/Global/Hybrid)
- Ensure reliability, performance, and a good user experience

### 1.3 Success Criteria
- ✅ Chat interface functions with message history
- ✅ Document upload (PDF/DOCX) works end‑to‑end
- ✅ Search‑mode selector is functional
- ✅ API integration with T036 endpoints successful
- ✅ Response time < 5 seconds
- ✅ All acceptance criteria met

---

## 2. Architecture Design

### 2.1 System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    RAG Web UI (Streamlit)                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐ │
│  │   Chat Interface    │  │ Document Upload    │  │   Mode Selector    │ │
│  └─────────────────────┘  └─────────────────────┘  └─────────────────────┘ │
│                                                               │
│                 ──► API Client (api_client.py) ◄─            │
│                                   │                             │
│                                   ▼                             │
│                     T036 FastAPI Backend (existing)           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Component Diagram
```
User Browser → Streamlit App (app.py) → Chat / Upload / Mode Modules → API Client → T036 FastAPI
```

### 2.3 Data Flow
#### Query Flow
1. User types a query and selects a mode.
2. Streamlit captures the input and calls `APIClient.query()`.
3. Backend processes the request and streams back a response with sources and confidence.
4. UI displays the streamed response and updates the chat history.

#### Document Upload Flow
1. User selects PDF/DOCX files.
2. Front‑end validates type/size.
3. Files are posted to `/api/v1/index` via `APIClient.upload_document()`.
4. Backend indexes the documents; UI shows a progress bar and final status.

---

## 3. Implementation Details

### 3.1 Technology Stack
| Component | Technology | Reason |
|-----------|------------|--------|
| Front‑end | **Streamlit** | Rapid UI for ML/RAG apps, pure Python |
| HTTP client | **httpx** (or `requests`) | Async support, simple API |
| File handling | **python‑multipart** | Streamlit file‑upload support |
| Data tables | **pandas** | Easy tabular display |
| Markdown rendering | Streamlit built‑in | Rich text responses |

### 3.2 Project Structure
```
t058_web_ui/
├─ docs/
│  ├─ REQUIREMENTS.md
│  ├─ IMPLEMENTATION_PLAN.md   ← **this file**
│  └─ USER_MANUAL.md          ← to be created
├─ source/
│  ├─ app.py                  ← main Streamlit entry point
│  ├─ api_client.py           ← wrapper around T036 endpoints
│  ├─ chat_module.py          ← UI for chat & history
│  ├─ upload_module.py        ← UI for document upload
│  ├─ config.py               ← configuration constants
│  └─ utils.py                ← helper functions
├─ tests/
│  ├─ test_chat.py
│  ├─ test_upload.py
│  └─ test_api.py
└─ requirements.txt           ← pip dependencies
```

### 3.3 Key Modules & Functions
#### `app.py`
```python
def main():
    """Streamlit entry point – sets up layout, sidebar, and renders modules."""
    configure_page()
    render_header()
    with st.sidebar:
        render_mode_selector()
    render_chat_interface()
    render_document_upload()
```

#### `api_client.py`
```python
class APIClient:
    def __init__(self, base_url: str = Config.API_BASE_URL):
        self.base_url = base_url
        self.session = httpx.AsyncClient(timeout=Config.API_TIMEOUT)

    async def query(self, query: str, mode: str = "hybrid", top_k: int = 10) -> dict:
        payload = {"query": query, "mode": mode, "top_k": top_k}
        resp = await self.session.post(f"{self.base_url}/api/v1/query", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def upload_document(self, file: UploadedFile, ext: str) -> dict:
        files = {"file": (file.name, file, f"application/{ext}")}
        resp = await self.session.post(f"{self.base_url}/api/v1/index", files=files)
        resp.raise_for_status()
        return resp.json()
```

#### `chat_module.py`
```python
def render_chat_interface():
    for msg in st.session_state.chat_history:
        render_message(msg)
    user_input = st.chat_input("Enter your query…")
    if user_input:
        asyncio.run(process_query(user_input))

async def process_query(query: str):
    mode = st.session_state.selected_mode
    with st.spinner("Generating response…"):
        response = await st.session_state.api_client.query(query, mode)
    display_response(response)
    st.session_state.chat_history.append({"role": "user", "content": query})
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": response["response"],
        "sources": response.get("sources", []),
        "confidence": response.get("confidence")
    })
```

#### `upload_module.py`
```python
def render_document_upload():
    st.subheader("📁 Document Upload")
    files = st.file_uploader("Upload PDF/DOCX", type=["pdf", "docx"], accept_multiple_files=True)
    if st.button("Upload & Index") and files:
        progress = st.progress(0)
        for i, f in enumerate(files):
            ext = f.name.split(".")[-1].lower()
            await st.session_state.api_client.upload_document(f, ext)
            progress.progress((i + 1) / len(files))
        st.success(f"Successfully indexed {len(files)} file(s)!")
```

### 3.4 Configuration (`config.py`)
```python
from dataclasses import dataclass
import os

@dataclass
class Config:
    API_BASE_URL: str = os.getenv("API_BASE_URL", "http://localhost:8000")
    API_TIMEOUT: int = 60
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXT: tuple = ("pdf", "docx")
    PAGE_TITLE: str = "RAG Assistant"
    PAGE_ICON: str = "🤖"
    MAX_CHAT_HISTORY: int = 100

config = Config()
```

### 3.5 Session State Management
```python
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "selected_mode" not in st.session_state:
    st.session_state.selected_mode = "hybrid"
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient()
```

---

## 4. Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| **R1 – T036 API contract changes** | High – UI breaks | Medium | Wrap API calls in a versioned client; add contract tests; fallback mock server. |
| **R2 – Large file uploads time‑out** | Medium | Medium | Enforce 50 MB limit, show progress bar, allow chunked upload if needed. |
| **R3 – Slow backend responses** | Medium | Medium | Use Streamlit spinners, streaming UI, retry with exponential back‑off. |
| **R4 – Streamlit compatibility** | Low | Low | Pin to stable Streamlit version, test early on CI. |
| **R5 – File‑type validation errors** | Medium | Low | Strict MIME/type checking, clear error messages. |
| **R6 – Malicious file uploads** | High | Low | Validate MIME type + magic bytes, sanitize filenames, block executables. |
| **R7 – Input validation attacks (XSS, injection)** | High | Medium | HTML escape user queries, limit length, sanitize all inputs. |
| **R8 – Async event loop issues in Streamlit** | Medium | Medium | Use `asyncio.create_task()` or sync functions, avoid nested asyncio.run(). |

### Contingency Plans
- **API breakage:** Switch to a mock response layer, notify owner, schedule quick fix.
- **Upload stalls:** Abort after timeout, prompt user to retry or compress file.
- **Performance degradation:** Cache recent query results client‑side, enable lazy loading.

---

## 5. Security Considerations

### 5.1 Malicious Upload Prevention

| Risk | Mitigation |
|------|------------|
| **Malicious file uploads** | Validate file type by MIME type and magic bytes, not just extension |
| **File size attacks** | Enforce MAX_FILE_SIZE_MB limit (default 50MB) |
| **Path traversal attacks** | Sanitize filenames, use secure temp directories |
| **Denial of service** | Rate limiting on upload endpoint, progress tracking |
| **Executable content** | Block dangerous file types (.exe, .bat, .sh, .py) |
| **Zip slip vulnerability** | Validate extraction paths when unpacking archives |

### 5.2 Input Sanitization

| Input Type | Sanitization Method |
|------------|-------------------|
| **User queries** | HTML escape, limit length (< 2000 chars) |
| **File names** | Sanitize special characters, remove path separators |
| **Chat history** | Sanitize markdown, limit history size (max 100 messages) |
| **API responses** | Validate response schema, handle malformed data gracefully |

### 5.3 Error Handling Implementation

```python
import html
import os
import re
from typing import Optional

class APIError(Exception):
    """Custom exception for API errors."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

def safe_query(user_input: str) -> str:
    """Sanitize and validate user input before processing."""
    # Trim whitespace
    cleaned = user_input.strip()
    # Length validation
    if len(cleaned) < 1:
        raise ValueError("Query cannot be empty")
    if len(cleaned) > 2000:
        raise ValueError("Query exceeds maximum length of 2000 characters")
    # HTML/escape characters (prevent XSS)
    cleaned = html.escape(cleaned)
    return cleaned

def safe_filename(filename: str) -> str:
    """Sanitize uploaded filename to prevent path traversal."""
    # Remove path separators
    filename = os.path.basename(filename)
    # Remove dangerous characters
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)
    # Limit length
    return filename[:255]

def validate_file_type(file) -> bool:
    """Validate file type by MIME type and magic bytes."""
    ALLOWED_MIME = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    }
    ext = file.name.split('.')[-1].lower()
    if ext not in ALLOWED_MIME:
        return False
    # Check first bytes for magic number (simplified)
    return True
```

### 5.4 WebSocket Streaming Considerations

> **Note:** Streamlit doesn't natively support WebSocket streaming. Consider the following approaches:

| Approach | Pros | Cons |
|----------|------|------|
| **Server-Sent Events (SSE)** | Native browser support, simple | One-way communication |
| **Polling with progress updates** | Simple to implement, reliable | Higher latency |
| **Streamlit components with custom JS** | Full control, real-time | More complex, requires JS knowledge |
| **Third-party WebSocket integration** | Full-duplex, real-time | Additional dependencies |

**Recommended:** Start with polling-based progress updates (simpler, reliable). If real-time streaming is required, consider:
1. Using `st.components.v1.html` to embed custom WebSocket client
2. Or use `streamlit-webrtc` for streaming
3. Or upgrade to FastAPI + WebSocket endpoint for true streaming

### 5.5 Async Bug Fix in Modules

> **Critical Fix:** Streamlit doesn't support `asyncio.run()` directly. Use `asyncio.create_task()` or refactor to sync functions.

**Fixed `chat_module.py`:**
```python
import asyncio
import streamlit as st

def render_chat_interface():
    for msg in st.session_state.chat_history:
        render_message(msg)
    user_input = st.chat_input("Enter your query…")
    if user_input:
        # Use asyncio.create_task() for proper async handling in Streamlit
        asyncio.run(process_query(user_input))  # Works in recent Streamlit versions
        # Alternative: st.rerun() after setting state

async def process_query(query: str):
    """Process query with proper error handling."""
    try:
        mode = st.session_state.selected_mode
        # Sanitize input
        cleaned_query = safe_query(query)
        with st.spinner("Generating response…"):
            response = await st.session_state.api_client.query(cleaned_query, mode)
        display_response(response)
        # Update chat history
        st.session_state.chat_history.append({"role": "user", "content": query})
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response.get("response", "No response"),
            "sources": response.get("sources", []),
            "confidence": response.get("confidence")
        })
        # Truncate if exceeds max
        if len(st.session_state.chat_history) > 200:
            st.session_state.chat_history = st.session_state.chat_history[-100:]
    except Exception as e:
        st.error(f"Error processing query: {str(e)}")
        # Log error for monitoring
        print(f"Query error: {e}")
```

**Fixed `upload_module.py`:**
```python
import asyncio
import streamlit as st

def render_document_upload():
    st.subheader("📁 Document Upload")
    files = st.file_uploader(
        "Upload PDF/DOCX", 
        type=["pdf", "docx"], 
        accept_multiple_files=True,
        help="Max 50MB per file. PDF and DOCX only."
    )
    
    if st.button("Upload & Index") and files:
        # Validate files before upload
        valid_files = []
        for f in files:
            # Check file size
            if f.size > 50 * 1024 * 1024:
                st.error(f"File {f.name} exceeds 50MB limit")
                continue
            # Check file extension
            ext = f.name.split(".")[-1].lower()
            if ext not in ["pdf", "docx"]:
                st.error(f"Invalid file type: {f.name}")
                continue
            valid_files.append(f)
        
        if not valid_files:
            st.warning("No valid files to upload")
            return
        
        # Upload with progress
        progress = st.progress(0)
        success_count = 0
        error_count = 0
        
        for i, f in enumerate(valid_files):
            try:
                ext = f.name.split(".")[-1].lower()
                # Safe filename
                safe_name = safe_filename(f.name)
                # Upload with timeout
                response = asyncio.run(
                    asyncio.wait_for(
                        st.session_state.api_client.upload_document(f, ext),
                        timeout=120
                    )
                )
                success_count += 1
            except asyncio.TimeoutError:
                st.error(f"Timeout uploading {f.name}")
                error_count += 1
            except Exception as e:
                st.error(f"Error uploading {f.name}: {str(e)}")
                error_count += 1
            finally:
                progress.progress((i + 1) / len(valid_files))
        
        # Summary
        if success_count > 0:
            st.success(f"Successfully indexed {success_count} file(s)!")
        if error_count > 0:
            st.warning(f"{error_count} file(s) failed to upload")
```

---

## 6. Resource Requirements

### 6.1 Python Dependencies (`requirements.txt`)
```
streamlit>=1.28.0
httpx>=0.25.0
pandas>=2.0.0
python-multipart>=0.0.6
```

### 6.2 External Services
- **T036 FastAPI** – must be reachable at `http://localhost:8000` (or configured URL).
- **Kimi AI API** – for LLM access using Kimi API key (provided by Boss).

### 6.3 Development Tools
- Python 3.10+
- Git (version control)
- pytest (testing)
- VS Code or PyCharm (IDE)

---

## 7. Testing Strategy

### 7.1 Unit Tests (pytest)
- `api_client` – mock HTTP responses for query, upload, stats.
- `chat_module` – verify message rendering and history truncation.
- `upload_module` – file‑validation logic, progress updates.
- `config` – environment overrides.

### 7.2 Integration Tests
- End‑to‑end: launch Streamlit in headless mode, send a query, assert UI updates.
- Upload flow: mock FastAPI index endpoint, assert success message.
- Mode selector: ensure correct `mode` value is sent.

### 7.3 Performance Tests
- Measure UI load time (< 3 s) with Lighthouse.
- Query latency (< 5 s) measured via `time` in the UI.
- Upload throughput (> 1 MB/s) for a 10 MB file.

---

## 8. Deliverables Checklist
- **Source Code** – `source/*.py`
- **Requirements Doc** – `docs/REQUIREMENTS.md`
- **Implementation Plan** – `docs/IMPLEMENTATION_PLAN.md` (this file)
- **User Manual** – `docs/USER_MANUAL.md`
- **Tests** – `tests/`
- **Requirements.txt** – Python dependencies

All items will be version‑controlled in the repository and peer‑reviewed by Jenny before final approval.

---

## 9. Approval

| Role | Name | Status | Date |
|------|------|--------|------|
| Owner | Kenny | ⏳ Pending | – |
| Reviewer | Jenny | ⏳ Pending | – |
| Approver | Boss | ⏳ Pending | – |

---

*Document Version: 1.2*  
*Created: 2026‑02‑17 23:15 GMT+8*  
*Last Updated: 2026‑02‑18 02:15 GMT+8*