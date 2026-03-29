#!/usr/bin/env python3
"""
Test script for metadata_extractor.py
Demonstrates APA 7th edition reference extraction.
"""

import sys
from metadata_extractor import MetadataExtractor, format_apa_reference, BibliographicData

def test_extractors():
    """Test the metadata extractor with various inputs"""
    
    print("=" * 70)
    print("Metadata Extractor Test Suite")
    print("=" * 70)
    print()
    
    extractor = MetadataExtractor()
    
    # Test 1: Sample academic paper text
    print("Test 1: Academic Paper Text")
    print("-" * 70)
    
    sample_text = """
    Advanced Packaging Technologies for High-Bandwidth Memory Systems
    
    Wei Chen, Yuki Tanaka, and Michael J. Anderson
    
    Department of Electrical Engineering, Stanford University
    
    Published in: IEEE Transactions on Semiconductor Manufacturing, 2024
    Vol. 37, No. 2, pp. 145-158
    DOI: 10.1109/TSM.2024.1234567
    
    Abstract:
    This paper presents novel packaging technologies...
    """
    
    data = extractor._extract_from_text(sample_text, "hbm_paper.txt")
    
    print(f"Title: {data.title}")
    print(f"Authors: {', '.join(data.authors) if data.authors else 'Not found'}")
    print(f"Year: {data.year or 'Not found'}")
    print(f"Source Type: {data.source_type}")
    print(f"Journal: {data.journal or 'Not found'}")
    print(f"DOI: {data.doi or 'Not found'}")
    print(f"Confidence: {data.extraction_confidence:.2f}")
    print()
    print("APA Reference:")
    print(f"  {format_apa_reference(data)}")
    print()
    
    # Test 2: Web article text
    print("Test 2: Web Article Text")
    print("-" * 70)
    
    web_text = """
    Understanding Hybrid Bonding for 3D IC Integration
    
    By: Sarah Johnson, Tech Reporter
    Posted: March 15, 2023
    
    Semiconductor Engineering
    
    Hybrid bonding is emerging as a key technology...
    """
    
    data2 = extractor._extract_from_text(web_text, "hybrid_bonding_article.html")
    
    print(f"Title: {data2.title}")
    print(f"Authors: {', '.join(data2.authors) if data2.authors else 'Not found'}")
    print(f"Year: {data2.year or 'Not found'}")
    print(f"Source Type: {data2.source_type}")
    print(f"Confidence: {data2.extraction_confidence:.2f}")
    print()
    print("APA Reference:")
    print(f"  {format_apa_reference(data2)}")
    print()
    
    # Test 3: Minimal metadata (low confidence)
    print("Test 3: Low Confidence (fallback to filename)")
    print("-" * 70)
    
    minimal_text = "This is just some random text without any clear metadata."
    
    data3 = extractor._extract_from_text(minimal_text, "random_notes.txt")
    
    print(f"Title: {data3.title}")
    print(f"Authors: {', '.join(data3.authors) if data3.authors else 'None'}")
    print(f"Year: {data3.year or 'None'}")
    print(f"Confidence: {data3.extraction_confidence:.2f}")
    print()
    print("APA Reference (should fallback to filename):")
    print(f"  {format_apa_reference(data3)}")
    print()
    
    # Test 4: Author name formatting
    print("Test 4: Author Name Formatting")
    print("-" * 70)
    
    test_names = [
        "John Smith",
        "Smith, John",
        "J. Smith",
        "Smith, J. D.",
        "John David Smith",
        "Dr. John Smith",
    ]
    
    for name in test_names:
        formatted = extractor._format_author_name(name)
        print(f"  '{name}' -> '{formatted}'")
    print()
    
    print("=" * 70)
    print("Tests completed!")
    print("=" * 70)


def demo_batch_processing():
    """Demonstrate batch processing"""
    
    print()
    print("=" * 70)
    print("Batch Processing Demo")
    print("=" * 70)
    print()
    
    # Create sample files (simulated)
    sample_files = [
        ("paper1.txt", """
            Machine Learning for Chip Design
            By Alice Johnson and Bob Smith
            Nature Electronics, 2023
            DOI: 10.1038/s41928-023-00987-x
        """),
        ("article.html", """
            <html>
            <head><title>The Future of AI Hardware</title></head>
            <body>
            <meta name="author" content="David Lee">
            <meta name="citation_date" content="2024-01-15">
            <h1>The Future of AI Hardware</h1>
            </body>
            </html>
        """),
        ("notes.txt", "Just some random notes without metadata"),
    ]
    
    # Create temporary files
    import tempfile
    import os
    
    temp_dir = tempfile.mkdtemp()
    file_paths = []
    
    for filename, content in sample_files:
        path = os.path.join(temp_dir, filename)
        with open(path, 'w') as f:
            f.write(content)
        file_paths.append(path)
    
    # Process files
    print(f"Processing {len(file_paths)} files...\n")
    
    from metadata_extractor import batch_extract
    
    results = batch_extract(file_paths)
    
    for i, (path, data) in enumerate(zip(file_paths, results), 1):
        filename = os.path.basename(path)
        print(f"{i}. {filename}")
        print(f"   APA: {format_apa_reference(data)}")
        print(f"   Confidence: {data.extraction_confidence:.2f}")
        print()
    
    # Cleanup
    for path in file_paths:
        os.remove(path)
    os.rmdir(temp_dir)


if __name__ == "__main__":
    test_extractors()
    demo_batch_processing()
