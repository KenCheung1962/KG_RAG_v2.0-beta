# Task T058: RAG Web UI Development

**Task ID:** T058  
**Task Name:** RAG Web User Interface  
**Assignee:** Kenny  
**Requester:** Boss  
**Priority:** High  
**Created:** 2026-02-17  
**Status:** Draft - Pending Approval

---

## 1. Overview

### 1.1 Purpose
Develop a web-based user interface for the Knowledge Graph RAG system, enabling users to interact with the RAG system through a modern, intuitive chat interface with document upload capabilities.

### 1.2 Scope
- **Frontend:** Streamlit-based web application
- **Backend:** Reuse existing T036 FastAPI endpoints
- **Core Features:**
  - RAG query interface (mainly)
  - Admin panel (small window)
  - Chat interface for queries
  - Document upload (PDF, DOCX)
  - Search mode selection (Local/Global/Hybrid)
- **Target Users:** Internal team/users
- **Design Reference:** LightRAG Web UI (don't copy)
- **LLM Provider:** Kimi AI API
- **Excluded:** Knowledge graph visualization (Phase 2)

---

## 2. Technology Stack

### 2.1 Frontend
- **Framework:** Streamlit (Python-based, rapid development)
- **Reasoning:** Best fit for RAG/ML applications, easy integration with T036 FastAPI

### 2.2 Backend Integration
- **API:** T036 FastAPI (existing)
- **Endpoints:** Reuse existing `/api/v1/...` endpoints

### 2.3 Dependencies
```
streamlit
requests
python-multipart (for file upload)
pandas (for data display)
```

---

## 3. Functional Requirements

### 3.1 Chat Interface (FR-CHAT)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-CHAT-01 | Chat message history display | High |
| FR-CHAT-02 | Text input for queries | High |
| FR-CHAT-03 | Streaming response display | High |
| FR-CHAT-04 | Markdown support in responses | Medium |
| FR-CHAT-05 | Clear chat history button | Medium |

### 3.2 Document Upload (FR-UPLOAD)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-UPLOAD-01 | PDF file upload | High |
| FR-UPLOAD-02 | DOCX file upload | High |
| FR-UPLOAD-03 | Drag-and-drop support | Medium |
| FR-UPLOAD-04 | Upload progress indicator | Medium |
| FR-UPLOAD-05 | File validation (type, size) | High |

### 3.3 Search Mode Selection (FR-SEARCH)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-SEARCH-01 | Local search mode | High |
| FR-SEARCH-02 | Global search mode | High |
| FR-SEARCH-03 | Hybrid search mode | High |
| FR-SEARCH-04 | Mode indicator in UI | Medium |

### 3.4 Response Display (FR-RESP)
| ID | Requirement | Priority |
|----|-------------|----------|
| FR-RESP-01 | Response source attribution | High |
| FR-RESP-02 | Confidence scores | Medium |
| FR-RESP-03 | Response streaming | High |
| FR-RESP-04 | Error messages | High |

---

## 4. Non-Functional Requirements

### 4.1 Performance
| ID | Requirement | Target |
|----|-------------|--------|
| NFR-PERF-01 | Response time | < 5 seconds |
| NFR-PERF-02 | UI load time | < 3 seconds |
| NFR-PERF-03 | Concurrent users | 1-5 users |

### 4.2 Usability
| ID | Requirement |
|----|-------------|
| NFR-USR-01 | Intuitive navigation |
| NFR-USR-02 | Responsive design |
| NFR-USR-03 | Clear error messages |

### 4.3 Reliability
| ID | Requirement |
|----|-------------|
| NFR-REL-01 | API error handling |
| NFR-REL-02 | Connection timeout handling |
| NFR-REL-03 | Graceful degradation |

---

## 5. User Interface Design

### 5.1 Layout Structure
```
┌─────────────────────────────────────────────────────┐
│ Header                                              │
│ - Title: RAG Assistant                             │
│ - Mode Selector: [Local] [Global] [Hybrid]          │
├─────────────────────────────────────────────────────┤
│ Chat History                                        │
│ - User message (right aligned)                      │
│ - Assistant response (left aligned)                 │
├─────────────────────────────────────────────────────┤
│ Document Upload Section                             │
│ - [Upload PDF/DOCX]                                │
│ - Uploaded files list                              │
├─────────────────────────────────────────────────────┤
│ Input Area                                         │
│ - [Query input box.............................]  │
│ - [Send] [Clear Chat]                             │
└─────────────────────────────────────────────────────┘
```

### 5.2 Color Scheme
- Primary: Professional blue/gray
- Accent: Green for success, Red for errors
- Background: Clean, readable

---

## 6. API Integration

### 6.1 Endpoints to Reuse
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/query` | POST | Submit queries |
| `/api/v1/entities` | GET | Retrieve entities |
| `/api/v1/relations` | GET | Retrieve relations |
| `/api/v1/index` | POST | Index documents |

### 6.2 Request/Response Format
```python
# Query Request
{
    "query": "string",
    "mode": "local|global|hybrid",
    "top_k": 10
}

# Query Response
{
    "response": "string",
    "sources": [{"id": "string", "content": "string"}],
    "confidence": float
}
```

---

## 7. Deliverables

| Deliverable | Description | Format |
|-------------|-------------|--------|
| Source Code | Streamlit web application | `/source/app.py` |
| Requirements | This document | `/docs/REQUIREMENTS.md` |
| User Manual | Operating instructions | `/docs/USER_MANUAL.md` |
| Test Records | Unit/integration tests | `/tests/` |

---

## 8. Acceptance Criteria

- [ ] Chat interface displays and functions correctly
- [ ] PDF and DOCX upload works
- [ ] Search mode selection functions
- [ ] API integration with T036 endpoints successful
- [ ] Error handling implemented
- [ ] Documentation complete
- [ ] Tests passing (>= 80%)

---

## 9. Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1: Core UI | 2 days | Chat + Upload |
| Phase 2: Integration | 2 days | API connection |
| Phase 3: Testing | 1 day | Tests + Fixes |

**Total Estimated Time:** 5 days

---

## 10. Dependencies

- T036 FastAPI endpoints (existing)
- Document processing libraries (PyPDF2, python-docx)
- Streamlit framework

---

## 11. Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| API changes | High | Version control |
| Large file uploads | Medium | Size limits |
| Slow responses | Medium | Streaming UI |

---

## 12. Approval

| Role | Name | Status | Date |
|------|------|--------|------|
| Owner | Kenny | ⏳ Pending | - |
| Reviewer | Jenny | ⏳ Pending | - |
| Approver | Boss | ⏳ Pending | - |

---

*Document Version: 1.0*  
*Created: 2026-02-17 22:55 GMT+8*
