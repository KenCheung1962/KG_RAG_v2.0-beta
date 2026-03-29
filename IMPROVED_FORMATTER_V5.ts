/**
 * IMPROVED FORMATTER v5 - Separate lines for headings and content
 * 
 * Issues Fixed:
 * 1. Headings and content on same line -> separate lines
 * 2. Remove inline ##References section with source listings
 * 3. Ensure NO # or ## characters appear in headings
 * 4. Keep Sources section at end for verification
 */

/**
 * Format query response with improved styling
 */
export function formatQueryResponse(text: string): string {
  if (!text) return '';
  
  let cleaned = text;
  
  // ======================
  // STEP 1: Remove problematic inline sections BEFORE processing
  // ======================
  
  // Remove the inline ##References section (with source listings like "8063 Source 2: ...")
  cleaned = cleaned.replace(/##+\s*References?\d*\s*[\n\r]+\d+[\s\S]*?(?=##+\s|##+\s*\n|## References|$)/i, '');
  
  // Remove inline source listings pattern
  cleaned = cleaned.replace(/\d*\s*Source\s*\d+:\s*[^\n]+/gi, '');
  cleaned = cleaned.replace(/the\s+literature:\s*[^\n]+/gi, '');
  
  // Clean up stray numbers before source listings
  cleaned = cleaned.replace(/\d{3,}\s+(?=Source\s+\d)/gi, '');
  
  // ======================
  // STEP 2: Store Sources section before cleaning
  // ======================
  
  let sourcesSection = '';
  const sourcesMatch = cleaned.match(/Sources:([\s\S]*)$/i);
  if (sourcesMatch) {
    sourcesSection = sourcesMatch[1].trim();
  }
  
  // Build reference mapping
  const references: string[] = [];
  const refPattern = /(?:Source\s*(\d+):|(\d+)\.\s+)([^\n]+?\.(?:txt|pdf|docx?|md|json|csv))/gi;
  let match;
  while ((match = refPattern.exec(text)) !== null) {
    const num = match[1] || match[2];
    const filename = match[3].trim();
    if (num && filename && !references.includes(filename)) {
      references[parseInt(num) - 1] = filename;
    }
  }
  
  // Extract literature file
  const litMatch = text.match(/the\s+literature:\s*([^\n]+?\.(?:txt|pdf|docx?|md|json))/i);
  let literatureFile = litMatch ? litMatch[1].trim() : '';
  
  // ======================
  // STEP 3: Pre-processing fixes
  // ======================
  
  // Fix headings without space after # (##Executive -> ## Executive)
  cleaned = cleaned.replace(/^(#{1,6})([A-Za-z])/gm, '$1 $2');
  
  // Fix headings merged with numbers
  cleaned = cleaned.replace(/^(#{1,6})([A-Za-z]+)(\d+)/gm, '$1 $2$3');
  
  // ======================
  // STEP 4: Citation standardization
  // ======================
  
  // Convert "Source X" to [X]
  cleaned = cleaned.replace(/\(?Source\s+(\d+)\)?/gi, '[$1]');
  
  // Handle multiple citations
  cleaned = cleaned.replace(/\[(\d+)\]\s*,\s*\[(\d+)\]/g, '[$1], [$2]');
  
  // Handle "the literature"
  const litIndex = literatureFile ? 
    references.findIndex(r => r === literatureFile) + 1 || references.length + 1 : 0;
  
  if (litIndex > 0) {
    cleaned = cleaned.replace(/the literature/gi, `[${litIndex}]`);
  }
  
  // ======================
  // STEP 5: Clean up remaining source patterns
  // ======================
  
  cleaned = cleaned.replace(/\s*Source\s*\d+:\s*[^\n.]*/gi, '');
  cleaned = cleaned.replace(/\n{4,}/g, '\n\n\n');
  cleaned = cleaned.replace(/[ \t]{2,}/g, ' ');
  
  // ======================
  // STEP 6: HEADING FORMATTING - CRITICAL FIX FOR SEPARATE LINES
  // ======================
  
  // First, ensure there's a newline between heading and content
  // Pattern: (## Heading)(Content with no newline) -> add newline
  cleaned = cleaned.replace(/^(#{1,6}\s+.+?)([A-Z][a-zA-Z])/gm, (match, heading, contentStart) => {
    // Check if there's already a newline after the heading
    if (!heading.endsWith('\n')) {
      return heading + '\n' + contentStart;
    }
    return match;
  });
  
  // Alternative approach: add newline after heading markers that don't have one
  cleaned = cleaned.replace(/(#{1,6}\s+.+?)(?=[A-Z][a-z]+\s+[a-z])/g, '$1\n');
  
  // Convert markdown headings to HTML with line breaks after
  cleaned = cleaned.replace(/^(#{1,6})\s+(.+?)$/gm, (match, hashes, content) => {
    const level = hashes.length;
    const cleanContent = content.trim();
    
    // Skip References headings
    if (/^References?$/i.test(cleanContent)) {
      return '';
    }
    
    // Return heading with explicit line breaks after
    return `<query-h${level} class="query-h${level}">${cleanContent}</query-h${level}><br><br>`;
  });
  
  // Clean up excessive line breaks
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  cleaned = cleaned.replace(/(<br>){3,}/g, '<br><br>');
  
  // ======================
  // STEP 7: INLINE FORMATTING
  // ======================
  
  // Format citation badges
  cleaned = cleaned.replace(/\[(\d+)\]/g, '<span class="citation-ref">[$1]</span>');
  
  // Bold and italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  
  // Bullet points
  cleaned = cleaned.replace(/^- (.+)$/gm, '• $1');
  cleaned = cleaned.replace(/^\* (.+)$/gm, '• $1');
  
  // Convert newlines to <br>
  cleaned = cleaned.replace(/\n/g, '<br>');
  cleaned = cleaned.replace(/(<br>){4,}/g, '<br><br><br>');
  
  // ======================
  // STEP 8: ADD CLEAN REFERENCES SECTION
  // ======================
  
  const uniqueRefs = references.filter(r => r);
  
  if (uniqueRefs.length > 0) {
    cleaned += '<br><br><query-h2 class="query-h2 references-header">📚 References</query-h2><br><br>';
    
    uniqueRefs.forEach((ref, index) => {
      cleaned += `<div class="reference-item"><span class="ref-number">${index + 1}.</span> ${ref}</div>`;
    });
  }
  
  // ======================
  // STEP 9: ADD SOURCES SECTION
  // ======================
  
  if (sourcesSection) {
    cleaned += '<br><br><query-h3 class="query-h3 sources-header">🔍 Sources (Verification)</query-h3><br>';
    cleaned += '<div class="sources-verification">';
    
    const sourceLines = sourcesSection.split(/\n|(?=\d+\.\s)/).filter(line => line.trim());
    
    if (sourceLines.length > 0) {
      sourceLines.forEach(line => {
        const trimmed = line.trim();
        if (trimmed) {
          cleaned += `<div class="source-item-verify">${trimmed}</div>`;
        }
      });
    } else {
      cleaned += `<div class="source-item-verify">${sourcesSection}</div>`;
    }
    
    cleaned += '</div>';
  }
  
  return cleaned;
}

// ======================
// CSS STYLES
// ======================
/*
.query-answer .citation-ref {
  display: inline-block;
  background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
  color: white;
  font-size: 0.75em;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  margin: 0 2px;
  vertical-align: super;
  line-height: 1;
}

.query-answer .references-header {
  margin-top: 32px !important;
  padding-top: 16px;
  border-top: 2px solid #4CAF50;
  border-bottom: none !important;
}

.query-answer .reference-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 14px;
  margin: 6px 0;
  background: rgba(76, 175, 80, 0.08);
  border-radius: 6px;
  border-left: 3px solid #4CAF50;
  font-size: 0.9em;
}

.query-answer .reference-item .ref-number {
  font-weight: 700;
  color: #4CAF50;
  min-width: 24px;
  flex-shrink: 0;
}

.query-answer .sources-header {
  margin-top: 24px !important;
  color: #ff9800 !important;
  border-left: 3px solid #ff9800 !important;
}

.query-answer .sources-verification {
  background: rgba(255, 152, 0, 0.05);
  border: 1px dashed rgba(255, 152, 0, 0.3);
  border-radius: 8px;
  padding: 12px;
  margin-top: 8px;
}

.query-answer .source-item-verify {
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
  color: #aaa;
  padding: 4px 0;
  border-bottom: 1px dotted rgba(255, 255, 255, 0.1);
  word-break: break-all;
}

.query-answer .source-item-verify:last-child {
  border-bottom: none;
}

// Custom heading tags - display as block with margins
.query-answer query-h1,
.query-answer query-h2,
.query-answer query-h3,
.query-answer query-h4 {
  display: block;
  font-weight: 700;
}

.query-answer query-h1 {
  font-size: 1.5em;
  color: #00d4ff;
  margin: 24px 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid #00d4ff;
}

.query-answer query-h2 {
  font-size: 1.25em;
  color: #ffffff;
  margin: 20px 0 12px 0;
  padding: 6px 0;
  border-bottom: 1px solid #555;
}

.query-answer query-h3 {
  font-size: 1.1em;
  color: #e0e0e0;
  margin: 16px 0 10px 0;
  padding-left: 10px;
  border-left: 3px solid #00d4ff;
}

.query-answer query-h4 {
  font-size: 1em;
  color: #b0b0b0;
  margin: 12px 0 8px 0;
}
*/
