# RAG Web UI - User Manual

**Task ID:** T058  
**Version:** 1.0  
**Last Updated:** 2026-02-18

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Using the Chat Interface](#using-the-chat-interface)
4. [Uploading Documents](#uploading-documents)
5. [Search Modes](#search-modes)
6. [Troubleshooting](#troubleshooting)

---

## Introduction

The RAG Web UI is a Streamlit-based web application that provides an intuitive interface for the Knowledge Graph RAG system. This user manual guides you through all features and functionality.

### Features

- 💬 **Chat Interface** - Query the RAG system with natural language
- 📁 **Document Upload** - Upload PDF/DOCX files for indexing
- 🔍 **Search Modes** - Choose between Local, Global, or Hybrid search
- 📊 **Response Details** - View sources and confidence scores

---

## Getting Started

### Installation

```bash
cd /Users/ken/clawd/RG_RAG/KG_RAG_Tasks/t058_web_ui
pip install -r requirements.txt
```

### Running the Application

```bash
cd source
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

### System Requirements

- Python 3.10+
- T036 FastAPI running at `http://localhost:8000`
- Modern web browser (Chrome, Firefox, Edge, Safari)

---

## Using the Chat Interface

### Sending a Query

1. Type your question in the chat input box at the bottom
2. Press Enter or click Send
3. Wait for the response (typically 3-5 seconds)

### Example Queries

```
"What is machine learning?"
"Explain the concept of neural networks"
"How does RAG work?"
"What are the applications of AI in healthcare?"
```

### Viewing Response Details

Each response shows:
- **Answer** - The generated response
- **Sources** - Click to expand and see source documents
- **Confidence Score** - Indicates reliability (0.0 - 1.0)

### Chat History

- Previous messages are displayed in the chat history
- History persists during your session
- Use "Clear Chat" in sidebar to start fresh

---

## Uploading Documents

### Supported File Types

| Format | Extensions | Max Size |
|--------|-----------|----------|
| PDF | .pdf | 50 MB |
| Word | .docx | 50 MB |

### Upload Steps

1. Click "Choose Files" or drag & drop files
2. Select one or more files (PDF or DOCX)
3. Click "Upload & Index"
4. Watch the progress bar
5. Receive confirmation when complete

### Upload Best Practices

- ✅ Use clear, descriptive filenames
- ✅ Ensure files are readable (not scanned images)
- ✅ Keep files under 50 MB
- ✅ Upload relevant documents for your queries

### Troubleshooting Uploads

| Issue | Solution |
|-------|----------|
| "Invalid file type" | Ensure PDF or DOCX format |
| "File too large" | Split into smaller files (<50MB) |
| "Upload timeout" | Check network connection, try again |
| "Indexing failed" | Verify T036 backend is running |

---

## Search Modes

### Local Search

- Searches only in uploaded documents
- Best for: Specific document Q&A
- Faster response time

### Global Search

- Searches the entire knowledge base
- Best: General questions, broad topics
- Slower but comprehensive

### Hybrid Search (Default)

- Combines local + global search
- Best for: Most queries
- Balanced speed and coverage

### Mode Selector

Use the sidebar dropdown to switch modes at any time.

---

## Troubleshooting

### Connection Issues

**Problem:** "Cannot connect to API"

**Solutions:**
1. Verify T036 is running: `curl http://localhost:8000/docs`
2. Check API_BASE_URL environment variable
3. Restart both T036 and RAG Web UI

### Slow Responses

**Problem:** Queries take too long

**Solutions:**
1. Try Local mode (faster)
2. Reduce top_k value in settings
3. Check system resources

### Empty Responses

**Problem:** No results returned

**Solutions:**
1. Try rephrasing the query
2. Upload relevant documents
3. Check if documents were indexed successfully

### Error Messages

| Error | Meaning | Action |
|-------|---------|--------|
| "API Error 500" | Server error | Wait, then retry |
| "Timeout" | Request too long | Try simpler query |
| "Connection refused" | API not running | Start T036 backend |

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Enter | Send message |
| Ctrl+Enter | New line in input |
| Esc | Clear input |

---

## Support

For issues or questions:

1. Check this manual
2. Review implementation plan: `docs/IMPLEMENTATION_PLAN.md`
3. Check test results: `tests/test_modules.py`
4. Contact the development team

---

*Document Version: 1.0*  
*Created: 2026-02-18*
