#!/usr/bin/env python3
"""
Metadata Extractor Module for KG RAG System
Extracts bibliographic metadata in APA 7th edition format from documents.

Supports: PDF, HTML, TXT, MD files
"""

import re
import os
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

# Optional imports - handle gracefully if not installed
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    print("Warning: pypdf not installed. PDF metadata extraction limited.")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    print("Warning: beautifulsoup4 not installed. HTML metadata extraction limited.")


@dataclass
class BibliographicData:
    """APA 7th edition bibliographic data structure"""
    # Core fields
    authors: List[str]
    year: Optional[int]
    title: str
    source_type: str  # "journal", "book", "webpage", "report", "conference", "unknown"
    
    # Journal article fields
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    
    # Book/Report fields
    publisher: Optional[str] = None
    edition: Optional[str] = None
    isbn: Optional[str] = None
    
    # Webpage fields
    website_name: Optional[str] = None
    url: Optional[str] = None
    access_date: Optional[str] = None
    
    # Fallback
    filename: str = ""
    
    # Quality metrics
    extraction_confidence: float = 0.0
    extraction_method: str = "unknown"  # "pdf_meta", "text_pattern", "html_meta", "grobid", "manual"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def is_complete(self) -> bool:
        """Check if we have minimum viable metadata"""
        return bool(self.title and (self.authors or self.year))


class MetadataExtractor:
    """
    Extract bibliographic metadata from various document formats.
    
    Usage:
        extractor = MetadataExtractor()
        data = extractor.extract("/path/to/document.pdf")
        apa_ref = format_apa_reference(data)
    """
    
    # Common patterns for bibliographic extraction
    DOI_PATTERN = re.compile(r'10\.\d{4,}(?:\.\d+)*/[^\s"<>]+', re.IGNORECASE)
    YEAR_PATTERN = re.compile(r'\b(19\d{2}|20\d{2})\b')
    ISBN_PATTERN = re.compile(r'(?:ISBN[-:]?\s*)?(?:97[89][-\s]?)?\d[-\s]?\d{3}[-\s]?\d{5}[-\s]?\d', re.IGNORECASE)
    
    # Journal name patterns
    JOURNAL_PATTERNS = [
        re.compile(r'Journal\s+of\s+[\w\s]+', re.IGNORECASE),
        re.compile(r'Proceedings\s+of\s+[\w\s]+', re.IGNORECASE),
        re.compile(r'IEEE\s+[\w\s]+', re.IGNORECASE),
        re.compile(r'ACM\s+[\w\s]+', re.IGNORECASE),
        re.compile(r'Nature\s+[\w\s]*', re.IGNORECASE),
        re.compile(r'Science\s+[\w\s]*', re.IGNORECASE),
        re.compile(r'[\w\s]+Review', re.IGNORECASE),
        re.compile(r'[\w\s]+Letters', re.IGNORECASE),
        re.compile(r'[\w\s]+Transactions', re.IGNORECASE),
    ]
    
    # Author patterns
    AUTHOR_PATTERNS = [
        # "Smith, J. D." or "Smith, John D."
        re.compile(r'([A-Z][a-zA-Z\-]+,\s+(?:[A-Z]\.?\s*)+(?:[A-Z][a-zA-Z\-]+)?)'),
        # "J. D. Smith" format
        re.compile(r'((?:[A-Z]\.?\s*)+[A-Z][a-zA-Z\-]+)'),
    ]
    
    def __init__(self):
        """Initialize the extractor"""
        self.stats = {
            "processed": 0,
            "successful": 0,
            "failed": 0,
        }
    
    def extract(self, file_path: str) -> BibliographicData:
        """
        Extract metadata from a file (auto-detect format).
        
        Args:
            file_path: Path to the document
            
        Returns:
            BibliographicData object with extracted metadata
        """
        path = Path(file_path)
        
        if not path.exists():
            return BibliographicData(
                authors=[],
                year=None,
                title=path.name,
                source_type="unknown",
                filename=path.name,
                extraction_confidence=0.0,
                extraction_method="error"
            )
        
        # Dispatch based on file extension
        ext = path.suffix.lower()
        
        if ext == '.pdf':
            return self.extract_from_pdf(file_path)
        elif ext in ['.html', '.htm']:
            return self.extract_from_html(file_path)
        elif ext in ['.txt', '.md', '.rst']:
            return self.extract_from_text(file_path)
        else:
            # Try text extraction as fallback
            return self.extract_from_text(file_path)
    
    def extract_from_pdf(self, file_path: str) -> BibliographicData:
        """
        Extract metadata from PDF files.
        
        Tries:
        1. PDF metadata (Title, Author, CreationDate)
        2. Text analysis of first page
        3. Pattern matching for DOI, year, etc.
        """
        filename = self._get_filename(file_path)
        
        if not PYPDF_AVAILABLE:
            # Fallback to text extraction if pypdf not available
            return self._extract_pdf_as_text(file_path)
        
        try:
            reader = pypdf.PdfReader(file_path)
            meta = reader.metadata
            
            # Extract from PDF metadata
            title = self._clean_text(meta.get('/Title', '')) if meta else ''
            author_str = self._clean_text(meta.get('/Author', '')) if meta else ''
            creation_date = meta.get('/CreationDate', '') if meta else ''
            
            # Parse year from PDF date format (D:YYYYMMDDHHMMSS)
            year = self._parse_pdf_date(creation_date)
            
            # Get first page text for additional extraction
            first_page_text = ""
            if len(reader.pages) > 0:
                try:
                    first_page_text = reader.pages[0].extract_text() or ""
                except Exception:
                    pass
            
            # If no metadata from PDF info, try text extraction
            if not title or not author_str:
                text_extracted = self._extract_from_text(first_page_text[:5000])
                
                if not title:
                    title = text_extracted.get('title', '')
                if not author_str and text_extracted.get('authors'):
                    author_str = ', '.join(text_extracted.get('authors', []))
            
            # Look for DOI in first few pages
            doi = None
            for page in reader.pages[:3]:
                try:
                    text = page.extract_text() or ""
                    doi_match = self.DOI_PATTERN.search(text)
                    if doi_match:
                        doi = doi_match.group()
                        break
                except Exception:
                    continue
            
            # Detect source type
            source_type = self._detect_source_type(title, first_page_text)
            
            # Extract additional fields based on source type
            journal = None
            volume = None
            issue = None
            pages = None
            
            if source_type == "journal":
                journal, volume, issue, pages = self._extract_journal_info(first_page_text[:3000])
            
            # Calculate confidence
            confidence = 0.0
            if title:
                confidence += 0.3
            if author_str:
                confidence += 0.3
            if year:
                confidence += 0.2
            if doi:
                confidence += 0.2
            
            return BibliographicData(
                authors=self._parse_authors(author_str),
                year=year,
                title=title or self._filename_to_title(filename),
                source_type=source_type,
                journal=journal,
                volume=volume,
                issue=issue,
                pages=pages,
                doi=doi,
                filename=filename,
                extraction_confidence=confidence,
                extraction_method="pdf_meta" if (title and author_str) else "pdf_text"
            )
            
        except Exception as e:
            print(f"Error extracting PDF {file_path}: {e}")
            return BibliographicData(
                authors=[],
                year=None,
                title=self._filename_to_title(filename),
                source_type="unknown",
                filename=filename,
                extraction_confidence=0.0,
                extraction_method="error"
            )
    
    def extract_from_html(self, file_path: str) -> BibliographicData:
        """
        Extract metadata from HTML files.
        
        Tries:
        1. Meta tags (author, description, citation_*)
        2. Title tag
        3. Open Graph tags
        """
        filename = self._get_filename(file_path)
        
        if not BS4_AVAILABLE:
            # Fallback to text extraction
            return self.extract_from_text(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            # Extract title
            title = ""
            
            # Try citation_title first (Google Scholar, academic sites)
            citation_title = soup.find('meta', attrs={'name': 'citation_title'})
            if citation_title:
                title = citation_title.get('content', '')
            
            # Fallback to DC.title
            if not title:
                dc_title = soup.find('meta', attrs={'name': 'DC.title'})
                if dc_title:
                    title = dc_title.get('content', '')
            
            # Fallback to og:title
            if not title:
                og_title = soup.find('meta', attrs={'property': 'og:title'})
                if og_title:
                    title = og_title.get('content', '')
            
            # Fallback to title tag
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.text.strip()
            
            # Extract authors
            authors = []
            
            # Try citation_author (academic sites)
            citation_authors = soup.find_all('meta', attrs={'name': 'citation_author'})
            if citation_authors:
                authors = [a.get('content', '') for a in citation_authors if a.get('content')]
            
            # Try DC.creator
            if not authors:
                dc_creators = soup.find_all('meta', attrs={'name': 'DC.creator'})
                authors = [c.get('content', '') for c in dc_creators if c.get('content')]
            
            # Try meta author
            if not authors:
                author_meta = soup.find('meta', attrs={'name': 'author'})
                if author_meta:
                    author_str = author_meta.get('content', '')
                    authors = self._parse_authors(author_str)
            
            # Extract year
            year = None
            
            # Try citation_date
            citation_date = soup.find('meta', attrs={'name': 'citation_date'})
            if citation_date:
                date_str = citation_date.get('content', '')
                year_match = self.YEAR_PATTERN.search(date_str)
                if year_match:
                    year = int(year_match.group(1))
            
            # Try DC.date
            if not year:
                dc_date = soup.find('meta', attrs={'name': 'DC.date'})
                if dc_date:
                    date_str = dc_date.get('content', '')
                    year_match = self.YEAR_PATTERN.search(date_str)
                    if year_match:
                        year = int(year_match.group(1))
            
            # Extract website name
            website_name = ""
            og_site = soup.find('meta', attrs={'property': 'og:site_name'})
            if og_site:
                website_name = og_site.get('content', '')
            
            if not website_name:
                # Try to get from URL or title
                title_text = soup.find('title')
                if title_text:
                    parts = title_text.text.split(' - ')
                    if len(parts) > 1:
                        website_name = parts[-1].strip()
            
            # Calculate confidence
            confidence = 0.0
            if title:
                confidence += 0.4
            if authors:
                confidence += 0.3
            if year:
                confidence += 0.2
            if website_name:
                confidence += 0.1
            
            return BibliographicData(
                authors=[self._format_author_name(a) for a in authors],
                year=year,
                title=title or self._filename_to_title(filename),
                source_type="webpage",
                website_name=website_name,
                filename=filename,
                extraction_confidence=confidence,
                extraction_method="html_meta"
            )
            
        except Exception as e:
            print(f"Error extracting HTML {file_path}: {e}")
            return self.extract_from_text(file_path)
    
    def extract_from_text(self, file_path: str) -> BibliographicData:
        """
        Extract metadata from text files (txt, md, etc.).
        Uses pattern matching on first 5000 characters.
        """
        filename = self._get_filename(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(5000)  # First 5000 chars
            
            return self._extract_from_text(content, filename)
            
        except Exception as e:
            print(f"Error extracting text {file_path}: {e}")
            return BibliographicData(
                authors=[],
                year=None,
                title=self._filename_to_title(filename),
                source_type="unknown",
                filename=filename,
                extraction_confidence=0.0,
                extraction_method="error"
            )
    
    def _extract_from_text(self, text: str, filename: str = "") -> BibliographicData:
        """
        Extract bibliographic info from raw text using pattern matching.
        """
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
        }
        
        # Look for DOI
        doi_match = self.DOI_PATTERN.search(text)
        if doi_match:
            result['doi'] = doi_match.group()
        
        # Look for year (19xx or 20xx) - prioritize years near beginning
        year_matches = list(self.YEAR_PATTERN.finditer(text[:2000]))
        if year_matches:
            # Take first year found
            result['year'] = int(year_matches[0].group(1))
        
        # Extract title (usually first substantial line)
        lines = text.split('\n')
        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()
            # Skip empty lines, short lines, and lines with just formatting
            if len(line) >= 20 and len(line) <= 200:
                # Skip lines that look like headers/footers
                if not re.match(r'^(page|chapter|\d+|fig|table)', line, re.IGNORECASE):
                    result['title'] = line
                    break
        
        # Look for journal patterns
        for pattern in self.JOURNAL_PATTERNS:
            match = pattern.search(text[:3000])
            if match:
                result['journal'] = match.group().strip()
                result['source_type'] = 'journal'
                break
        
        # Look for author patterns in first 1000 chars
        author_section = text[:1000]
        for pattern in self.AUTHOR_PATTERNS:
            matches = pattern.findall(author_section)
            if matches:
                # Filter out false positives
                potential_authors = [m.strip() for m in matches if len(m) > 5]
                if potential_authors:
                    result['authors'] = potential_authors[:3]  # Max 3 authors
                    break
        
        # Detect source type if not already set
        if result['source_type'] == 'unknown':
            result['source_type'] = self._detect_source_type(result['title'], text)
        
        # Calculate confidence
        confidence = 0.0
        if result['title']:
            confidence += 0.3
        if result['authors']:
            confidence += 0.3
        if result['year']:
            confidence += 0.2
        if result['journal']:
            confidence += 0.2
        
        return BibliographicData(
            authors=[self._format_author_name(a) for a in result['authors']],
            year=result['year'],
            title=result['title'] or self._filename_to_title(filename),
            source_type=result['source_type'],
            journal=result['journal'],
            volume=result['volume'],
            issue=result['issue'],
            pages=result['pages'],
            doi=result['doi'],
            filename=filename,
            extraction_confidence=confidence,
            extraction_method="text_pattern"
        )
    
    def _extract_pdf_as_text(self, file_path: str) -> BibliographicData:
        """Fallback extraction when pypdf not available - try to read as text"""
        filename = self._get_filename(file_path)
        
        try:
            # Try to read first few KB as text (may contain some extractable text)
            with open(file_path, 'rb') as f:
                raw = f.read(10000)
                # Try to decode, ignoring binary garbage
                text = raw.decode('utf-8', errors='ignore')
                # Clean up null bytes and control characters
                text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
            
            return self._extract_from_text(text, filename)
            
        except Exception:
            return BibliographicData(
                authors=[],
                year=None,
                title=self._filename_to_title(filename),
                source_type="unknown",
                filename=filename,
                extraction_confidence=0.0,
                extraction_method="fallback"
            )
    
    # Helper methods
    
    def _parse_authors(self, author_string: str) -> List[str]:
        """Parse author string into list of formatted author names"""
        if not author_string:
            return []
        
        # Split by common separators
        # Handle: "Smith, J., Jones, M." or "Smith, J. and Jones, M." or "J. Smith; M. Jones"
        separators = r',|;|\band\b|\&'
        raw_authors = re.split(separators, author_string)
        
        parsed = []
        for author in raw_authors:
            author = author.strip()
            if not author or len(author) < 2:
                continue
            
            formatted = self._format_author_name(author)
            if formatted:
                parsed.append(formatted)
        
        return parsed
    
    def _format_author_name(self, name: str) -> str:
        """
        Format author name to APA style: "Last, F. M."
        
        Handles:
        - "John Smith" -> "Smith, J."
        - "Smith, John" -> "Smith, J."
        - "J. Smith" -> "Smith, J."
        - "Smith, J. D." -> "Smith, J. D." (already formatted)
        """
        if not name:
            return ""
        
        name = name.strip()
        
        # Already in "Last, F." format
        if ',' in name:
            parts = name.split(',', 1)
            if len(parts) == 2:
                last = parts[0].strip()
                first = parts[1].strip()
                # Clean up initials
                initials = re.sub(r'[^A-Z\.\s]', '', first.upper())
                initials = ' '.join([i + '.' for i in initials.replace('.', '').split()])
                return f"{last}, {initials}".strip()
        
        # Try to parse "First Last" format
        parts = name.split()
        if len(parts) >= 2:
            # Assume last part is last name
            last = parts[-1]
            first_parts = parts[:-1]
            
            # Convert first names to initials
            initials = []
            for part in first_parts:
                # Handle "J.D." or "J. D."
                clean = part.replace('.', '').strip()
                if clean:
                    initials.append(clean[0].upper() + '.')
            
            return f"{last}, {''.join(initials)}"
        
        return name
    
    def _parse_pdf_date(self, date_str: str) -> Optional[int]:
        """Parse PDF date string (D:YYYYMMDDHHMMSS) to year"""
        if not date_str:
            return None
        
        # Try D:YYYYMMDDHHMMSS format
        match = re.search(r'D:(\d{4})', date_str)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2100:
                return year
        
        # Try regular year pattern
        match = self.YEAR_PATTERN.search(str(date_str))
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2100:
                return year
        
        return None
    
    def _detect_source_type(self, title: str, text: str) -> str:
        """Detect the type of source based on content patterns"""
        text_lower = (text or "").lower()
        title_lower = (title or "").lower()
        
        # Check for conference indicators
        if any(word in title_lower for word in ['proceedings', 'conference', 'symposium', 'workshop']):
            return "conference"
        
        # Check for journal indicators
        if any(word in text_lower[:2000] for word in ['journal', 'volume', 'issue', 'doi.org']):
            return "journal"
        
        # Check for book indicators
        if any(word in title_lower for word in ['book', 'handbook', 'textbook']):
            return "book"
        
        # Check for report indicators
        if any(word in title_lower for word in ['report', 'technical report', 'white paper']):
            return "report"
        
        # Default
        return "unknown"
    
    def _extract_journal_info(self, text: str) -> tuple:
        """Extract journal name, volume, issue, pages from text"""
        journal = None
        volume = None
        issue = None
        pages = None
        
        # Try to find journal citation pattern
        # Pattern: "Journal Name, 15(2), 123-145"
        pattern = re.compile(
            r'([A-Za-z\s\-]+)[,;]?\s*(\d+)\s*\((\d+)\)[,;]?\s*(\d+[-–]\d+)',
            re.IGNORECASE
        )
        match = pattern.search(text)
        if match:
            journal = match.group(1).strip()
            volume = match.group(2)
            issue = match.group(3)
            pages = match.group(4)
        
        return journal, volume, issue, pages
    
    def _get_filename(self, path: str) -> str:
        """Extract filename from path"""
        return Path(path).name
    
    def _filename_to_title(self, filename: str) -> str:
        """Convert filename to human-readable title"""
        # Remove extension
        name = Path(filename).stem
        
        # Replace underscores and hyphens with spaces
        name = name.replace('_', ' ').replace('-', ' ')
        
        # Remove common prefixes
        prefixes = ['draft', 'final', 'v1', 'v2', 'v3', 'copy', 'new']
        for prefix in prefixes:
            if name.lower().startswith(prefix + ' '):
                name = name[len(prefix)+1:]
        
        # Capitalize words
        return name.strip().title()
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        if not text:
            return ""
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()


def format_apa_reference(data: BibliographicData) -> str:
    """
    Format BibliographicData as APA 7th edition reference.
    
    Examples:
        - Journal: Smith, J. D. (2023). Title. *Journal*, 15(2), 45-67. https://doi.org/xxx
        - Book: Smith, J. D. (2023). *Title* (2nd ed.). Publisher.
        - Webpage: Smith, J. D. (2023). Title. Site Name. URL
        - Unknown: filename.txt (fallback)
    """
    # If low confidence and no real metadata, just return filename
    if data.extraction_confidence < 0.3 and not (data.authors or data.year):
        return data.filename
    
    # Format authors
    if not data.authors:
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
    
    # Build reference based on source type
    parts = []
    
    if authors_str:
        parts.append(authors_str)
    
    parts.append(year_str)
    
    # Title (italicized for books, plain for articles)
    if data.source_type == "book" and data.title:
        parts.append(f"*{data.title}*")
    elif data.title:
        parts.append(data.title)
    
    # Source-specific formatting
    if data.source_type == "journal" and data.journal:
        parts.append(f"*{data.journal}*")
        if data.volume:
            vol_issue = data.volume
            if data.issue:
                vol_issue += f"({data.issue})"
            parts.append(vol_issue)
        if data.pages:
            parts.append(data.pages)
        if data.doi:
            parts.append(f"https://doi.org/{data.doi}")
    
    elif data.source_type == "webpage":
        if data.website_name:
            parts.append(data.website_name)
        if data.url:
            parts.append(data.url)
    
    elif data.source_type == "book":
        if data.edition:
            parts.append(f"({data.edition} ed.)")
        if data.publisher:
            parts.append(data.publisher)
    
    # Filter out empty parts and join
    result = " ".join([p for p in parts if p])
    
    # Fallback if formatting failed
    if not result or result == year_str:
        return data.filename
    
    return result


def batch_extract(file_paths: List[str]) -> List[BibliographicData]:
    """
    Extract metadata from multiple files.
    
    Args:
        file_paths: List of file paths
        
    Returns:
        List of BibliographicData objects
    """
    extractor = MetadataExtractor()
    results = []
    
    for path in file_paths:
        try:
            data = extractor.extract(path)
            results.append(data)
        except Exception as e:
            print(f"Error processing {path}: {e}")
            # Add error entry
            results.append(BibliographicData(
                authors=[],
                year=None,
                title=Path(path).name,
                source_type="unknown",
                filename=Path(path).name,
                extraction_confidence=0.0,
                extraction_method="error"
            ))
    
    return results


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Metadata Extractor - APA 7th Edition")
    print("=" * 60)
    print()
    
    if len(sys.argv) > 1:
        # Process files from command line
        file_paths = sys.argv[1:]
        
        print(f"Processing {len(file_paths)} file(s)...\n")
        
        for path in file_paths:
            print(f"File: {path}")
            print("-" * 40)
            
            extractor = MetadataExtractor()
            data = extractor.extract(path)
            
            print(f"Title: {data.title}")
            print(f"Authors: {', '.join(data.authors) if data.authors else 'Not found'}")
            print(f"Year: {data.year or 'Not found'}")
            print(f"Type: {data.source_type}")
            print(f"Confidence: {data.extraction_confidence:.2f}")
            print(f"Method: {data.extraction_method}")
            print()
            
            apa_ref = format_apa_reference(data)
            print(f"APA Reference:")
            print(f"  {apa_ref}")
            print()
            print("=" * 60)
    else:
        print("Usage: python metadata_extractor.py <file1> [file2] ...")
        print()
        print("Example:")
        print("  python metadata_extractor.py document.pdf article.html")
        print()
        
        # Demo with sample text
        print("Demo with sample text extraction:")
        print("-" * 40)
        
        sample_text = """
        High Bandwidth Memory (HBM) Architecture for AI Applications
        
        John Smith, Jane Doe, and Bob Johnson
        
        Department of Computer Engineering, MIT
        
        Published in: Journal of Semiconductor Technology, 2024
        DOI: 10.1109/JST.2024.1234567
        
        Abstract:
        This paper discusses HBM architecture...
        """
        
        extractor = MetadataExtractor()
        data = extractor._extract_from_text(sample_text, "sample_paper.txt")
        
        print(f"Title: {data.title}")
        print(f"Authors: {', '.join(data.authors) if data.authors else 'Not found'}")
        print(f"Year: {data.year or 'Not found'}")
        print(f"DOI: {data.doi or 'Not found'}")
        print()
        
        apa_ref = format_apa_reference(data)
        print(f"APA Reference:")
        print(f"  {apa_ref}")
