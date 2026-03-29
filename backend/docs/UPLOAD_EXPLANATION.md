# 📤 Upload & Index Button - Explanation

## What It Does

The **"📤 Upload & Index"** button allows users to upload PDF or DOCX documents to the RAG system for indexing.

---

## How It Works

```
┌─────────────────────────────────────────────────────────┐
│  User selects PDF/DOCX files                           │
│           ↓                                            │
│  System validates file type and size                   │
│           ↓                                            │
│  Files sent to T036 backend for indexing              │
│           ↓                                            │
│  Documents processed and added to knowledge base      │
│           ↓                                            │
│  ✅ Success message shown                              │
└─────────────────────────────────────────────────────────┘
```

---

## What Gets Indexed

| File Type | Purpose |
|-----------|---------|
| **PDF** | Academic papers, reports, books |
| **DOCX** | Word documents, notes |

---

## What "Index" Means

**Index** = Convert document into searchable format

- Extracts text from files
- Breaks into chunks
- Creates embeddings (vector representation)
- Stores in knowledge graph
- Enables semantic search

---

## Usage Steps

1. **Click "📁 Upload"** tab
2. **Select files** (PDF or DOCX, max 50MB each)
3. **Click "📤 Upload & Index"**
4. **Wait** for processing (progress bar shown)
5. **See confirmation** when complete

---

## What Happens After Upload

- Document becomes searchable
- Can be queried via chat interface
- Sources will reference the uploaded document
- Available for future queries

---

## Current Status

| Mode | Upload Works? |
|------|---------------|
| **Demo Mode** | ✅ Yes (mocked) |
| **Real Mode** | ✅ Yes (real indexing) |

---

## Tips for Users

| ✅ Do | ❌ Don't |
|-------|---------|
| Use clear filenames | Upload executable files |
| Keep under 50MB | Upload password-protected files |
| Use readable PDFs | Upload corrupt files |

---

## Example Use Case

```
User: "I want to ask questions about my research paper"

Steps:
1. Upload PDF of research paper
2. Wait for indexing confirmation
3. Ask: "What is the main conclusion?"
4. System references your uploaded paper
```
