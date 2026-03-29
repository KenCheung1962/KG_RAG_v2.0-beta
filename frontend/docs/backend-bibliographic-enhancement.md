# Backend Enhancement: Bibliographic Metadata Extraction

## Overview
Enhance the LightRAG backend to extract and store bibliographic metadata from uploaded documents, enabling proper academic-style references in query responses.

## Current State
- API returns `sources` as a **number** (count of sources): `20`
- **BUG**: Should return array of source filenames: `["document.pdf", "article.txt"]`
- No structured bibliographic data available

## Target State
- API returns structured bibliographic metadata for each source
- Frontend can display full academic references

## Immediate Fix Required

### Fix: Return Source Filenames Instead of Count

**Problem**: The API currently returns:
```json
{
  "response": "...",
  "sources": 20  // Just a number!
}
```

**Should return**:
```json
{
  "response": "...",
  "sources": ["doc1.pdf", "doc2.txt", "article.md"]
}
```

**Backend Fix** (in query endpoint):

```python
# CURRENT (broken):
return {
    "response": answer,
    "sources": len(retrieved_chunks)  # Returns number only
}

# FIXED:
return {
    "response": answer,
    "sources": [chunk.doc_id or chunk.source_file for chunk in retrieved_chunks]
}
```

Or if using LightRAG's internal storage:

```python
# Get unique source documents from chunks
source_files = list(set([
    chunk.get("file_name") or chunk.get("doc_id", "unknown") 
    for chunk in retrieved_context
]))

return {
    "response": answer,
    "sources": source_files
}
```

## Required Changes

### 1. Database Schema Update

Add new table/collection for document metadata:

```sql
CREATE TABLE document_metadata (
    doc_id VARCHAR(255) PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    -- Bibliographic fields
    title VARCHAR(1000),
    authors JSON,  -- Array of {name: string, affiliation?: string}
    publication_year INTEGER,
    journal_or_publisher VARCHAR(500),
    volume VARCHAR(50),
    issue VARCHAR(50),
    pages VARCHAR(50),
    doi VARCHAR(255),
    url VARCHAR(1000),
    -- Extraction metadata
    extraction_method VARCHAR(50),  -- 'pdf_metadata', 'grobid', 'llm', 'manual'
    extraction_confidence FLOAT,
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 2. Metadata Extraction Pipeline

#### Option A: PDF Metadata Extraction (Basic)
```python
import pypdf
from dataclasses import dataclass

@dataclass
class BibliographicData:
    title: str | None
    authors: list[str]
    year: int | None
    publisher: str | None
    doi: str | None

def extract_pdf_metadata(file_path: str) -> BibliographicData:
    """Extract metadata from PDF file."""
    reader = pypdf.PdfReader(file_path)
    meta = reader.metadata
    
    return BibliographicData(
        title=meta.get('/Title'),
        authors=meta.get('/Author', '').split(', ') if meta.get('/Author') else [],
        year=parse_year(meta.get('/CreationDate')),
        publisher=meta.get('/Producer'),
        doi=None  # PDF metadata rarely includes DOI
    )
```

#### Option B: GROBID Integration (Recommended)
Use [GROBID](https://github.com/kermitt2/grobid) for academic document parsing:

```python
import requests
from xml.etree import ElementTree as ET

def extract_with_grobid(pdf_path: str, grobid_url: str = "http://localhost:8070") -> BibliographicData:
    """Extract metadata using GROBID service."""
    with open(pdf_path, 'rb') as f:
        response = requests.post(
            f"{grobid_url}/api/processHeaderDocument",
            files={'input': f},
            data={'consolidateHeader': '1'}
        )
    
    # Parse TEI XML response
    root = ET.fromstring(response.text)
    
    # Extract structured data
    title = root.find('.//{http://www.tei-c.org/ns/1.0}title')
    authors = root.findall('.//{http://www.tei-c.org/ns/1.0}author')
    
    return BibliographicData(
        title=title.text if title is not None else None,
        authors=[get_author_name(a) for a in authors],
        year=get_publication_year(root),
        publisher=get_publisher(root),
        doi=get_doi(root)
    )
```

#### Option C: LLM-Based Extraction (Fallback)
```python
async def extract_with_llm(text_sample: str, llm_client) -> BibliographicData:
    """Use LLM to extract bibliographic data from text."""
    prompt = """
    Extract bibliographic information from this document excerpt.
    Return JSON with fields: title, authors (array), year, journal_or_publisher, doi
    
    Document excerpt:
    {text}
    """
    
    response = await llm_client.complete(prompt.format(text=text_sample[:5000]))
    return parse_json_response(response)
```

### 3. API Response Update

Update `QueryResponse` to include structured source data:

```python
class SourceDocument(BaseModel):
    doc_id: str
    filename: str
    # Bibliographic data
    title: str | None
    authors: list[str]
    year: int | None
    journal_or_publisher: str | None
    volume: str | None
    issue: str | None
    pages: str | None
    doi: str | None
    url: str | None
    # Relevance info
    relevance_score: float | None
    chunks_used: int

class QueryResponse(BaseModel):
    response: str
    answer: str
    sources: list[SourceDocument]  # Updated from list[str]
    source_documents: list[SourceDocument]  # Alias for compatibility
```

### 4. Citation Integration in LLM Prompts

Modify system prompts to request inline citations:

```python
SYSTEM_PROMPT_COMPREHENSIVE = """
You are a knowledgeable research assistant. Provide a comprehensive answer 
based on the retrieved context.

CRITICAL: You MUST cite your sources using numbered references [1], [2], etc.
at the end of sentences or paragraphs where information is used.

At the end of your response, include a "References" section listing all 
cited sources with full bibliographic details.

Format references as:
[1] Author, A. B., & Author, C. D. (Year). Title. Journal/Publisher.

Use the provided document metadata to construct proper citations.
"""
```

### 5. Document Upload Enhancement

Update upload endpoint to trigger metadata extraction:

```python
@app.post("/documents/upload")
async def upload_document(file: UploadFile):
    # Save file
    doc_id = await save_file(file)
    
    # Extract metadata asynchronously
    metadata = await extract_metadata(file_path, file.content_type)
    
    # Store in database
    await store_document_metadata(doc_id, file.filename, metadata)
    
    # Continue with chunking/indexing
    await index_document(doc_id)
    
    return {"doc_id": doc_id, "status": "processing"}
```

## Implementation Priority

1. **Phase 1**: Basic PDF metadata extraction (title, author)
2. **Phase 2**: GROBID integration for academic papers
3. **Phase 3**: LLM fallback for unstructured documents
4. **Phase 4**: Citation integration in LLM responses

## Frontend Impact

The frontend types need updating:

```typescript
// src/api/types.ts
export interface SourceDocument {
  doc_id: string;
  filename: string;
  title?: string;
  authors: string[];
  year?: number;
  journal_or_publisher?: string;
  volume?: string;
  issue?: string;
  pages?: string;
  doi?: string;
  url?: string;
  relevance_score?: number;
  chunks_used: number;
}

export interface QueryResponse {
  response?: string;
  answer?: string;
  sources?: SourceDocument[] | number;
  source_documents?: SourceDocument[] | number;
  detail?: string;
}
```

## Example Output

### Current:
```json
{
  "response": "HBM packages use TSVs for vertical connectivity...",
  "sources": ["hbm_whitepaper.pdf", "tsv_research.pdf"]
}
```

### Enhanced:
```json
{
  "response": "HBM packages use Through-Silicon Vias (TSVs) for vertical connectivity between stacked dies [1][2].",
  "sources": [
    {
      "doc_id": "doc_001",
      "filename": "hbm_whitepaper.pdf",
      "title": "High Bandwidth Memory: Architecture and Applications",
      "authors": ["John Smith", "Jane Doe"],
      "year": 2023,
      "journal_or_publisher": "IEEE Transactions on Semiconductor Manufacturing",
      "volume": "36",
      "issue": "2",
      "pages": "145-158",
      "doi": "10.1109/TSM.2023.1234567",
      "chunks_used": 5
    },
    {
      "doc_id": "doc_002", 
      "filename": "tsv_research.pdf",
      "title": "Advanced TSV Technologies for 3D Integration",
      "authors": ["Robert Chen"],
      "year": 2022,
      "journal_or_publisher": "Journal of Microelectronic Engineering",
      "volume": "215",
      "pages": "112-125",
      "doi": null,
      "chunks_used": 3
    }
  ]
}
```

## Display Format

### In UI:
```
## References

[1] Smith, J., & Doe, J. (2023). High Bandwidth Memory: Architecture and 
    Applications. IEEE Transactions on Semiconductor Manufacturing, 36(2), 
    145-158. https://doi.org/10.1109/TSM.2023.1234567

[2] Chen, R. (2022). Advanced TSV Technologies for 3D Integration. 
    Journal of Microelectronic Engineering, 215, 112-125.
```

## Dependencies to Add

```txt
# For PDF metadata
pypdf>=4.0.0

# For GROBID integration (optional)
requests>=2.31.0

# For DOI resolution (optional)
crossref-commons>=0.0.7
```

## Testing

1. Upload various document types (PDF, DOCX, TXT)
2. Verify metadata extraction
3. Run queries and verify structured source responses
4. Check reference formatting in UI
5. Test edge cases (missing metadata, malformed PDFs)
