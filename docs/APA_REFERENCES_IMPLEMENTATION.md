# APA 7th Edition References Implementation

## Goal
Extract bibliographic information from source documents and format references in APA 7th edition (author-date) style.

## Current State
- Backend returns: `["cybersecurity_threats.txt", "HBM_Summary.html"]`
- Display shows: `1. cybersecurity_threats.txt`

## Target State
- Display shows: `1. Smith, J. D., & Jones, M. A. (2023). Cybersecurity threats in modern systems. *Journal of Cybersecurity*, 15(2), 45-67.`
- Or if no metadata: `1. cybersecurity_threats.txt`

## APA 7th Edition Format Examples

### Journal Article
```
Author, A. A., & Author, B. B. (Year). Title of article. *Title of Periodical*, volume(issue), pages. https://doi.org/xx.xxx/yyyy
```

### Book
```
Author, A. A. (Year). *Title of work: Capital letter also for subtitle* (Edition). Publisher.
```

### Webpage/HTML
```
Author, A. A., & Author, B. B. (Date). Title of page. Site Name. URL
```

### Technical Report
```
Author, A. A. (Year). *Title of report* (Report No. xxx). Publisher. URL
```

## Implementation Plan

### Phase 1: Backend Metadata Extraction

#### 1.1 Document Metadata Extraction Pipeline

```python
# backend/metadata_extractor.py

import re
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
import pypdf
from bs4 import BeautifulSoup

@dataclass
class BibliographicData:
    """APA 7th edition bibliographic data"""
    authors: List[str]  # ["Smith, J. D.", "Jones, M. A."]
    year: Optional[int]
    title: str
    source_type: str  # "journal", "book", "webpage", "report", "unknown"
    
    # For journal articles
    journal: Optional[str]
    volume: Optional[str]
    issue: Optional[str]
    pages: Optional[str]
    doi: Optional[str]
    
    # For books/reports
    publisher: Optional[str]
    edition: Optional[str]
    
    # For webpages
    website_name: Optional[str]
    url: Optional[str]
    access_date: Optional[str]
    
    # Fallback
    filename: str
    extraction_confidence: float  # 0.0 to 1.0


class MetadataExtractor:
    """Extract bibliographic metadata from various document formats"""
    
    def extract_from_pdf(self, file_path: str) -> BibliographicData:
        """Extract metadata from PDF using PyPDF2 and pdfplumber"""
        import pypdf
        
        reader = pypdf.PdfReader(file_path)
        meta = reader.metadata
        
        # Try to get info from PDF metadata
        title = meta.get('/Title', '') if meta else ''
        author = meta.get('/Author', '') if meta else ''
        creation_date = meta.get('/CreationDate', '') if meta else ''
        
        # Parse year from creation date (D:YYYYMMDDHHMMSS format)
        year = self._parse_pdf_date(creation_date)
        
        # If no metadata, try to extract from first page text
        if not title or not author:
            first_page_text = reader.pages[0].extract_text() if reader.pages else ''
            extracted = self._extract_from_text(first_page_text)
            if not title:
                title = extracted.get('title', '')
            if not author:
                author = extracted.get('author', '')
        
        return BibliographicData(
            authors=self._parse_authors(author),
            year=year,
            title=title or self._get_filename_without_ext(file_path),
            source_type="unknown",
            journal=None,
            volume=None,
            issue=None,
            pages=None,
            doi=None,
            publisher=None,
            edition=None,
            website_name=None,
            url=None,
            access_date=None,
            filename=self._get_filename(file_path),
            extraction_confidence=0.5 if (title and author) else 0.2
        )
    
    def extract_from_txt(self, file_path: str) -> BibliographicData:
        """Extract metadata from text files"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(5000)  # First 5000 chars
        
        extracted = self._extract_from_text(content)
        
        return BibliographicData(
            authors=extracted.get('authors', []),
            year=extracted.get('year'),
            title=extracted.get('title', self._get_filename_without_ext(file_path)),
            source_type=extracted.get('source_type', 'unknown'),
            journal=extracted.get('journal'),
            volume=extracted.get('volume'),
            issue=extracted.get('issue'),
            pages=extracted.get('pages'),
            doi=extracted.get('doi'),
            publisher=extracted.get('publisher'),
            edition=extracted.get('edition'),
            website_name=None,
            url=None,
            access_date=datetime.now().strftime('%Y-%m-%d'),
            filename=self._get_filename(file_path),
            extraction_confidence=extracted.get('confidence', 0.3)
        )
    
    def extract_from_html(self, file_path: str) -> BibliographicData:
        """Extract metadata from HTML files"""
        from bs4 import BeautifulSoup
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        # Try to get meta tags
        title_tag = soup.find('title')
        title = title_tag.text if title_tag else ''
        
        # Look for meta author
        author_meta = soup.find('meta', attrs={'name': 'author'})
        author = author_meta.get('content', '') if author_meta else ''
        
        # Look for citation metadata (DC, citation_*, etc.)
        citation_title = soup.find('meta', attrs={'name': 'citation_title'})
        if citation_title:
            title = citation_title.get('content', title)
        
        citation_authors = soup.find_all('meta', attrs={'name': 'citation_author'})
        if citation_authors:
            author = '; '.join([a.get('content', '') for a in citation_authors])
        
        citation_year = soup.find('meta', attrs={'name': 'citation_date'})
        year = None
        if citation_year:
            year_str = citation_year.get('content', '')
            year_match = re.search(r'\d{4}', year_str)
            if year_match:
                year = int(year_match.group())
        
        return BibliographicData(
            authors=self._parse_authors(author),
            year=year,
            title=title or self._get_filename_without_ext(file_path),
            source_type="webpage",
            journal=None,
            volume=None,
            issue=None,
            pages=None,
            doi=None,
            publisher=None,
            edition=None,
            website_name=soup.find('meta', attrs={'property': 'og:site_name'}).get('content', '') if soup.find('meta', attrs={'property': 'og:site_name'}) else None,
            url=None,
            access_date=datetime.now().strftime('%Y-%m-%d'),
            filename=self._get_filename(file_path),
            extraction_confidence=0.6 if title else 0.3
        )
    
    def _extract_from_text(self, text: str) -> dict:
        """Extract bibliographic info from raw text using patterns"""
        result = {
            'authors': [],
            'year': None,
            'title': '',
            'source_type': 'unknown',
            'journal': None,
            'volume': None,
            'issue': None,
            'pages': None,
            'doi': None,
            'publisher': None,
            'confidence': 0.0
        }
        
        # Look for DOI
        doi_match = re.search(r'10\.\d{4,}/[^\s]+', text)
        if doi_match:
            result['doi'] = doi_match.group()
            result['confidence'] += 0.2
        
        # Look for year (19xx or 20xx)
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', text[:2000])
        if year_match:
            result['year'] = int(year_match.group())
            result['confidence'] += 0.1
        
        # Look for "Author et al." or "Author, A. B." patterns
        author_patterns = [
            r'([A-Z][a-z]+(?:,\s*[A-Z]\.?(?:\s*[A-Z]\.)?)*)',
            r'([A-Z][a-z]+\s+et\s+al\.?)',
        ]
        
        # Look for title (often first line or sentence)
        lines = text.split('\n')
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:
                result['title'] = line
                result['confidence'] += 0.1
                break
        
        # Look for journal name patterns
        journal_patterns = [
            r'Journal\s+of\s+[^,.]+',
            r'Proceedings\s+of\s+[^,.]+',
            r'IEEE\s+[^,.]+',
            r'ACM\s+[^,.]+',
        ]
        for pattern in journal_patterns:
            match = re.search(pattern, text[:3000], re.IGNORECASE)
            if match:
                result['journal'] = match.group()
                result['source_type'] = 'journal'
                result['confidence'] += 0.2
                break
        
        return result
    
    def _parse_authors(self, author_string: str) -> List[str]:
        """Parse author string into list of APA formatted authors"""
        if not author_string:
            return []
        
        # Split by common separators
        authors = re.split(r',|;|&|\band\b', author_string)
        parsed = []
        
        for author in authors:
            author = author.strip()
            if not author:
                continue
            
            # Try to parse "First Last" or "Last, First" format
            if ',' in author:
                # Already in "Last, First" format
                parsed.append(author)
            else:
                parts = author.split()
                if len(parts) >= 2:
                    # Convert "John Smith" to "Smith, J."
                    last = parts[-1]
                    initials = ''.join([p[0].upper() + '.' for p in parts[:-1] if p])
                    parsed.append(f"{last}, {initials}")
                else:
                    parsed.append(author)
        
        return parsed
    
    def _parse_pdf_date(self, date_str: str) -> Optional[int]:
        """Parse PDF date string (D:YYYYMMDDHHMMSS)"""
        if not date_str:
            return None
        match = re.search(r'D:(\d{4})', date_str)
        if match:
            return int(match.group(1))
        return None
    
    def _get_filename(self, path: str) -> str:
        """Extract filename from path"""
        return path.split('/')[-1].split('\\')[-1]
    
    def _get_filename_without_ext(self, path: str) -> str:
        """Extract filename without extension"""
        filename = self._get_filename(path)
        return filename.rsplit('.', 1)[0] if '.' in filename else filename


def format_apa_reference(data: BibliographicData) -> str:
    """Format BibliographicData as APA 7th edition reference"""
    
    # Format authors
    if len(data.authors) == 0:
        authors_str = ""
    elif len(data.authors) == 1:
        authors_str = data.authors[0]
    elif len(data.authors) == 2:
        authors_str = f"{data.authors[0]}, & {data.authors[1]}"
    else:
        # 3+ authors: First Author et al.
        authors_str = f"{data.authors[0]} et al."
    
    # Format year
    year_str = f"({data.year})." if data.year else "(n.d.)."
    
    # Format based on source type
    if data.source_type == "journal" and data.journal:
        # Journal article
        parts = [
            authors_str,
            year_str,
            data.title,
            f"*{data.journal}*",
        ]
        if data.volume:
            vol_issue = f"{data.volume}"
            if data.issue:
                vol_issue += f"({data.issue})"
            parts.append(vol_issue)
        if data.pages:
            parts.append(data.pages)
        if data.doi:
            parts.append(f"https://doi.org/{data.doi}")
        
        return " ".join([p for p in parts if p])
    
    elif data.source_type == "webpage":
        # Webpage
        parts = [
            authors_str,
            year_str,
            data.title,
        ]
        if data.website_name:
            parts.append(data.website_name)
        if data.url:
            parts.append(data.url)
        
        return " ".join([p for p in parts if p])
    
    else:
        # Generic / Unknown - use filename as fallback
        if data.authors or data.year:
            parts = [
                authors_str,
                year_str,
                data.title or data.filename,
            ]
            return " ".join([p for p in parts if p])
        else:
            # No metadata extracted, use filename
            return data.filename


# Usage example
if __name__ == "__main__":
    extractor = MetadataExtractor()
    
    # Example: Extract from a PDF
    # data = extractor.extract_from_pdf("/path/to/paper.pdf")
    # apa_ref = format_apa_reference(data)
    # print(apa_ref)
    # Output: Smith, J. D., & Jones, M. A. (2023). Title of article. *Journal Name*, 15(2), 45-67.
```

### Phase 2: Backend Integration

#### 2.1 Update Document Upload to Extract Metadata

```python
# In pgvector_api.py or main.py

from metadata_extractor import MetadataExtractor, format_apa_reference

extractor = MetadataExtractor()

@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile):
    # Save file
    doc_id = await save_file(file)
    file_path = get_file_path(doc_id)
    
    # Extract metadata based on file type
    if file.filename.endswith('.pdf'):
        metadata = extractor.extract_from_pdf(file_path)
    elif file.filename.endswith('.html') or file.filename.endswith('.htm'):
        metadata = extractor.extract_from_html(file_path)
    else:
        metadata = extractor.extract_from_txt(file_path)
    
    # Store metadata in database
    await store_document_metadata(doc_id, metadata)
    
    # Continue with chunking/indexing
    await index_document(doc_id)
    
    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "metadata": {
            "title": metadata.title,
            "authors": metadata.authors,
            "year": metadata.year,
            "source_type": metadata.source_type
        },
        "status": "processing"
    }
```

#### 2.2 Update Query Response to Return APA References

```python
# In pgvector_api.py - modify the chat endpoint

@app.post("/api/v1/chat")
async def chat(request: dict):
    # ... existing query logic ...
    
    # Get metadata for each source chunk
    unique_sources = list(set([r.get("source", "unknown") for r in filtered_result]))
    
    # Build source list with APA formatted references
    source_list = []
    apa_references = []
    
    for source_filename in unique_sources:
        # Get stored metadata for this document
        metadata = await get_document_metadata(source_filename)
        
        if metadata:
            # Format as APA reference
            apa_ref = format_apa_reference(metadata)
            apa_references.append(apa_ref)
            
            source_list.append({
                "filename": source_filename,
                "apa_reference": apa_ref,
                "metadata": {
                    "title": metadata.title,
                    "authors": metadata.authors,
                    "year": metadata.year
                }
            })
        else:
            # No metadata, use filename as fallback
            apa_references.append(source_filename)
            source_list.append({
                "filename": source_filename,
                "apa_reference": source_filename,
                "metadata": None
            })
    
    return {
        "response": llm_response,
        "answer": llm_response,
        "sources": apa_references,  # Now returns APA formatted references
        "source_details": source_list,
        "confidence": round(confidence, 2)
    }
```

#### 2.3 Database Schema for Metadata

```sql
-- Add metadata table
CREATE TABLE document_metadata (
    doc_id VARCHAR(255) PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    
    -- Bibliographic data (APA 7th edition)
    title VARCHAR(1000),
    authors JSON,  -- ["Smith, J. D.", "Jones, M. A."]
    publication_year INTEGER,
    source_type VARCHAR(50),  -- journal, book, webpage, report, unknown
    
    -- Journal specific
    journal_name VARCHAR(500),
    volume VARCHAR(50),
    issue VARCHAR(50),
    pages VARCHAR(50),
    doi VARCHAR(255),
    
    -- Book/Report specific
    publisher VARCHAR(500),
    edition VARCHAR(50),
    
    -- Webpage specific
    website_name VARCHAR(500),
    url VARCHAR(1000),
    access_date DATE,
    
    -- APA formatted reference (cached)
    apa_reference TEXT,
    
    -- Extraction metadata
    extraction_confidence FLOAT,
    extraction_method VARCHAR(50),  -- pdf_meta, text_pattern, grobid, manual
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Phase 3: Frontend Display

#### 3.1 Update Frontend Types

```typescript
// src/api/types.ts

export interface SourceDocument {
  filename: string;
  apa_reference: string;  // Full APA formatted reference
  metadata?: {
    title?: string;
    authors?: string[];
    year?: number;
  };
}

export interface QueryResponse {
  response?: string;
  answer?: string;
  sources?: SourceDocument[] | string[] | number;  // Can be APA refs or legacy
  source_documents?: SourceDocument[] | string[] | number;
  detail?: string;
}
```

#### 3.2 Update References Display

```typescript
// In QueryTab.ts - format references for display

function formatReferences(sources: any[]): string {
  if (sources.length === 0) return '';
  
  let refs = '\n\n\n## References\n\n';
  
  sources.forEach((src, idx) => {
    if (typeof src === 'string') {
      // Check if it's already an APA formatted reference
      if (src.includes('(') && (src.includes(').') || src.includes('*'))) {
        refs += `${idx + 1}. ${src}\n\n`;
      } else {
        // Just a filename
        refs += `${idx + 1}. ${src}\n`;
      }
    } else if (src.apa_reference) {
      // Structured source with APA reference
      refs += `${idx + 1}. ${src.apa_reference}\n\n`;
    } else if (src.filename) {
      // Fallback to filename
      refs += `${idx + 1}. ${src.filename}\n`;
    }
  });
  
  return refs;
}
```

## Expected Output Example

### With Metadata Extracted:
```
## References

1. Chen, W., & Liu, Y. (2024). Advanced packaging technologies for high-bandwidth memory. 
   *IEEE Transactions on Semiconductor Manufacturing*, 37(2), 145-158. 
   https://doi.org/10.1109/TSM.2024.1234567

2. Smith, J. D. et al. (2023). *High Bandwidth Memory: Architecture and Applications* (2nd ed.). 
   Academic Press.

3. Hybrid bonding for 3D integration. (n.d.). Semiconductor Engineering. 
   https://semiengineering.com/hybrid-bonding

4. HBM行业深度.txt
```

## Implementation Priority

1. **Phase 1** (Immediate): 
   - Create `metadata_extractor.py` with basic text pattern extraction
   - Extract DOI, year, title from first 2000 chars
   - Store metadata in database

2. **Phase 2** (Week 2):
   - Add PDF metadata extraction (PyPDF2)
   - Add HTML meta tag parsing
   - Format APA references

3. **Phase 3** (Week 3-4):
   - Integrate GROBID for academic papers
   - Add LLM-based extraction for complex documents
   - Manual metadata editing UI

## Dependencies to Add

```txt
# requirements.txt
pypdf>=4.0.0
beautifulsoup4>=4.12.0
pdfplumber>=0.10.0
requests>=2.31.0  # For DOI resolution via CrossRef
```

## Notes

- **Option 1 (Preferred)**: Extract and format APA references in backend
- **Fallback**: If no metadata, display filename
- **Confidence threshold**: Only format as APA if confidence > 0.5
- **Manual override**: Allow users to edit metadata via UI
