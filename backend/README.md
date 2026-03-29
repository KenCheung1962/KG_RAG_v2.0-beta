# KG RAG Backend API

FastAPI backend for KG RAG System with PostgreSQL + pgvector.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python pgvector_api.py

# Server will be available at http://localhost:8002
```

## API Endpoints

### Main Query
```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "What are fabrication processes for HBM?",
  "mode": "hybrid",
  "top_k": 20,
  "detailed": false,
  "ultra_comprehensive": false
}
```

### Response
```json
{
  "response": "Detailed answer...",
  "answer": "Detailed answer...",
  "sources": ["doc1.pdf", "doc2.txt"],
  "confidence": 0.85
}
```

### Document Upload
```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

file: <binary>
```

### Query with Files
```http
POST /api/v1/chat/with-doc
Content-Type: application/json

{
  "message": "Explain this document",
  "filenames": ["uploaded.pdf"]
}
```

## Files

| File | Description |
|------|-------------|
| `pgvector_api.py` | Main FastAPI application with RAG endpoints |
| `metadata_extractor.py` | APA 7th edition bibliographic metadata extraction |
| `test_metadata_extractor.py` | Test suite for metadata extractor |

## Metadata Extractor Module

The `metadata_extractor.py` module extracts bibliographic information from documents in APA 7th edition format.

### Usage

```python
from metadata_extractor import MetadataExtractor, format_apa_reference

# Extract metadata from a file
extractor = MetadataExtractor()
data = extractor.extract("/path/to/document.pdf")

# Format as APA reference
apa_reference = format_apa_reference(data)
print(apa_reference)
# Output: Smith, J. D., & Jones, M. A. (2023). Title of article. *Journal Name*, 15(2), 45-67.
```

### Supported Formats

- **PDF** (.pdf) - Uses PyPDF2 for metadata and text extraction
- **HTML** (.html, .htm) - Extracts meta tags and citation metadata
- **Text** (.txt, .md) - Pattern matching for bibliographic info

### Extracted Fields

- `authors` - List of authors in APA format (e.g., ["Smith, J. D.", "Jones, M. A."])
- `year` - Publication year
- `title` - Document title
- `source_type` - journal, book, webpage, report, unknown
- `journal` - Journal name (for articles)
- `volume`, `issue`, `pages` - Citation details
- `doi` - DOI if available
- `filename` - Original filename (fallback)

### Test the Extractor

```bash
# Run the test suite
python test_metadata_extractor.py

# Test with specific files
python metadata_extractor.py document.pdf article.html notes.txt
```

### Integration with API

The metadata extractor is integrated into the document upload and query endpoints:

1. When a document is uploaded, metadata is extracted automatically
2. Query responses include formatted APA references
3. Low-confidence extractions fall back to filenames

### APA 7th Edition Format Examples

```
Journal Article:
  Smith, J. D., & Jones, M. A. (2023). Title of article. *Journal Name*, 15(2), 45-67.

Book:
  Smith, J. D. (2023). *Title of book* (2nd ed.). Publisher Name.

Webpage:
  Smith, J. D. (2023). Title of page. Website Name. https://example.com

Unknown (fallback):
  document_filename.txt
```

## Environment Variables

```bash
# Required
DEEPSEEK_API_KEY=your_deepseek_key
MINIMAX_API_KEY=your_minimax_key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/kg_rag

# Optional
LOG_LEVEL=INFO
```

## Query Modes

| Mode | top_k | Tokens | Timeout | Description |
|------|-------|--------|---------|-------------|
| Quick | 10 | 4,096 | 3 min | Fast answers |
| Balanced | 20 | 4,096 | 4 min | Standard queries |
| Comprehensive | 30 | 8,192 | 5 min | Detailed analysis |
| Ultra Deep | 40 | 8,192 | 15 min | Extensive research |

## Troubleshooting

### Backend won't start
- Check PostgreSQL is running: `pg_isready`
- Verify port 8002 is free: `lsof -i :8002`
- Check API keys are set

### Metadata extraction not working
- Install optional dependencies: `pip install pypdf beautifulsoup4`
- Check file permissions
- View extraction confidence in output

### No sources in response
- Restart backend after code changes
- Check documents are indexed in database
- Verify source extraction in logs
