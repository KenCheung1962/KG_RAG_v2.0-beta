/**
 * IMPROVED FORMATTER v3 - Keeps Sources section for double-checking
 * 
 * Issues Fixed:
 * 1. Headings without spaces (##Executive -> ## Executive)
 * 2. Multiple/double references sections consolidated
 * 3. "the literature" citation handling
 * 4. Merged heading-content issues
 * 5. Sources section PRESERVED at end for verification
 */

/**
 * Format query response with improved styling - KEEPS SOURCES SECTION
 */
export function formatQueryResponse(text: string): string {
  if (!text) return '';
  
  let cleaned = text;
  
  // ======================
  // PRE-PROCESSING: Fix malformed content
  // ======================
  
  // Fix headings merged with numbers (##References8791 -> ## References)
  cleaned = cleaned.replace(/^(#{1,6})([A-Za-z]+)(\d+)/gm, '$1 $2$3');
  
  // Fix headings without space after # (##Executive -> ## Executive)
  cleaned = cleaned.replace(/^(#{1,6})([A-Za-z])/gm, '$1 $2');
  
  // Store original sources section before cleaning (to preserve for end)
  let sourcesSection = '';
  const sourcesMatch = cleaned.match(/Sources:([\s\S]*)$/i);
  if (sourcesMatch) {
    sourcesSection = sourcesMatch[1].trim();
  }
  
  // Store inline source listings for reference mapping
  const sourceMap = new Map<string, string>();
  const sourceListingPattern = /Source\s*(\d+):\s*([^\n]+)/gi;
  let match;
  while ((match = sourceListingPattern.exec(cleaned)) !== null) {
    sourceMap.set(match[1], match[2].trim());
  }
  
  // Also check "the literature: filename" pattern
  const litMatch = cleaned.match(/the\s+literature:\s*([^\n]+)/i);
  let literatureFile = '';
  if (litMatch) {
    literatureFile = litMatch[1].trim();
  }
  
  // ======================
  // CITATION STANDARDIZATION
  // ======================
  
  // Convert "Source X" to [X]
  cleaned = cleaned.replace(/\(?Source\s+(\d+)\)?/gi, '[$1]');
  
  // Handle "Source X, Source Y" -> [X], [Y]
  cleaned = cleaned.replace(/\[(\d+)\]\s*,\s*\[(\d+)\]/g, '[$1], [$2]');
  
  // Handle "the literature" - convert to [LIT] then to citation number
  const hasLiterature = /the literature/gi.test(cleaned);
  if (hasLiterature) {
    cleaned = cleaned.replace(/the literature/gi, '[LIT]');
  }
  
  // ======================
  // HEADING FORMATTING
  // ======================
  
  // Insert newline before heading markers
  cleaned = cleaned.replace(/(?<![\n])([.!?:])(#{1,6}\s)/g, '$1\n$2');
  
  // Convert markdown headings to HTML (REMOVES the # characters)
  cleaned = cleaned.replace(/^(#{1,6})\s+(.+?)$/gm, (match, hashes, content) => {
    const level = hashes.length;
    const className = `query-h${level}`;
    const cleanContent = content.trim();
    return `<${className} class="${className}">${cleanContent}</${className}>`;
  });
  
  // ======================
  // CLEANUP: Remove inline reference listings from body
  // ======================
  
  // Remove inline source listings (keep them in Sources section only)
  cleaned = cleaned.replace(/\s*Source\s*\d+:\s*[^\n]+/gi, '');
  cleaned = cleaned.replace(/\s*the\s+literature:\s*[^\n]+/gi, '');
  
  // Remove malformed References sections (but keep Sources:)
  cleaned = cleaned.replace(/<query-h[1-6][^>]*>\s*References?\d*\s*<\/query-h[1-6]>/gi, '');
  
  // Clean up empty lines
  cleaned = cleaned.replace(/\n{4,}/g, '\n\n\n');
  
  // ======================
  // INLINE FORMATTING
  // ======================
  
  // Format citation numbers [X]
  cleaned = cleaned.replace(/\[(\d+)\]/g, '<span class="citation-ref">[$1]</span>');
  
  // Handle [LIT] - replace with appropriate citation number
  // Determine which number corresponds to literature file
  let litCitationNum = 0;
  const references: string[] = [];
  
  // Build ordered reference list
  sourceMap.forEach((filename, num) => {
    references[parseInt(num) - 1] = filename;
    if (filename === literatureFile || filename.includes('Literature') || filename.includes('Light Source')) {
      litCitationNum = parseInt(num);
    }
  });
  
  // If literature file wasn't in numbered sources, add it
  if (litCitationNum === 0 && literatureFile) {
    litCitationNum = references.length + 1;
    references.push(literatureFile);
  }
  
  // Replace [LIT] with proper citation
  if (litCitationNum > 0) {
    cleaned = cleaned.replace(/\[LIT\]/g, `<span class="citation-ref">[${litCitationNum}]</span>`);
  } else {
    cleaned = cleaned.replace(/\[LIT\]/g, '');
  }
  
  // Bold and italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  
  // Bullet points
  cleaned = cleaned.replace(/^- (.+)$/gm, '• $1');
  
  // Convert newlines to <br>
  cleaned = cleaned.replace(/\n/g, '<br>');
  cleaned = cleaned.replace(/(<br>){4,}/g, '<br><br><br>');
  
  // ======================
  // ADD REFERENCES SECTION
  // ======================
  
  if (references.length > 0) {
    cleaned += '<br><br><query-h2 class="query-h2 references-header">📚 References</query-h2><br><br>';
    
    references.forEach((ref, index) => {
      if (ref) {
        cleaned += `<div class="reference-item"><span class="ref-number">${index + 1}.</span> ${ref}</div>`;
      }
    });
  }
  
  // ======================
  // ADD SOURCES SECTION (for double-check)
  // ======================
  
  if (sourcesSection) {
    cleaned += '<br><br><query-h3 class="query-h3 sources-header">🔍 Sources (Verification)</query-h3><br>';
    cleaned += '<div class="sources-verification">';
    
    // Parse and format sources section
    const sourceLines = sourcesSection.split(/\n|(?=\d+\.\s)/).filter(line => line.trim());
    
    if (sourceLines.length > 0) {
      sourceLines.forEach(line => {
        const trimmed = line.trim();
        if (trimmed) {
          cleaned += `<div class="source-item-verify">${trimmed}</div>`;
        }
      });
    } else {
      // If no line breaks, just show the whole thing
      cleaned += `<div class="source-item-verify">${sourcesSection}</div>`;
    }
    
    cleaned += '</div>';
  }
  
  return cleaned;
}

// ======================
// UPDATED CSS STYLES
// ======================
/*
Add these styles to your existing CSS:

/
// Citation badges
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
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.query-answer .citation-ref:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
}

// References section styling
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
  text-align: left;
}

.query-answer .reference-item .ref-number {
  font-weight: 700;
  color: #4CAF50;
  min-width: 24px;
  flex-shrink: 0;
}

// Sources verification section (for double-check)
.query-answer .sources-header {
  margin-top: 24px !important;
  color: #ff9800 !important;  // Orange to distinguish from References
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

// Custom Heading Tags (no # characters)
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
