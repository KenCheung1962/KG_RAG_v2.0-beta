/**
 * IMPROVED FORMATTER v2 - Addresses specific formatting issues in the sample output
 * 
 * Issues Fixed:
 * 1. Headings without spaces (##Executive -> ## Executive)
 * 2. Multiple/double references sections
 * 3. "the literature" citation handling
 * 4. Merged heading-content issues
 * 5. Duplicate Sources: section removal
 */

/**
 * Format query response with improved styling - FIXED VERSION
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
  
  // Remove duplicate/merged References sections (keep only the first clean one)
  // Remove variations like "##References", "##References8791", etc.
  cleaned = cleaned.replace(/^#{1,6}\s*References?\d*\s*[:\-]?\s*\n/im, '\n## References\n');
  
  // ======================
  // CITATION STANDARDIZATION
  // ======================
  
  // Standardize "Source X" citations to [X]
  cleaned = cleaned.replace(/\(?Source\s+(\d+)\)?/gi, '[$1]');
  
  // Handle "Source X, Source Y" patterns -> [X], [Y]
  cleaned = cleaned.replace(/\[?(\d+)\]?\s*,\s*\[?(\d+)\]?/g, '[$1], [$2]');
  
  // Handle "the literature" citation - convert to numbered reference
  // First, mark all "the literature" occurrences
  const literatureMatches = cleaned.match(/the literature/gi) || [];
  if (literatureMatches.length > 0) {
    // Replace "the literature" with citation that will be numbered later
    cleaned = cleaned.replace(/the literature/gi, '[LIT]');
  }
  
  // ======================
  // HEADING FORMATTING
  // ======================
  
  // Insert newline before heading markers that don't have one
  cleaned = cleaned.replace(/(?<![\n])([.!?:])(#{1,6}\s)/g, '$1\n$2');
  
  // Convert markdown headings to HTML (REMOVES the # characters)
  cleaned = cleaned.replace(/^(#{1,6})\s+(.+?)$/gm, (match, hashes, content) => {
    const level = hashes.length;
    const className = `query-h${level}`;
    const cleanContent = content.trim();
    return `<${className} class="${className}">${cleanContent}</${className}>`;
  });
  
  // ======================
  // REFERENCES SECTION PROCESSING
  // ======================
  
  // Extract all reference information BEFORE formatting
  const references: string[] = [];
  
  // Find patterns like "Source X: filename.txt" or just filenames
  const refPattern = /Source\s*\d+:\s*([^\n]+)/gi;
  let refMatch;
  while ((refMatch = refPattern.exec(cleaned)) !== null) {
    const ref = refMatch[1].trim();
    if (!references.includes(ref)) {
      references.push(ref);
    }
  }
  
  // Also extract filenames mentioned in the text
  const filenamePattern = /([A-Za-z][A-Za-z0-9\s\-_]+\.(?:txt|pdf|doc|md|json))/gi;
  let filenameMatch;
  while ((filenameMatch = filenamePattern.exec(cleaned)) !== null) {
    const filename = filenameMatch[1].trim();
    // Only add if not already in references and looks like a real filename
    if (!references.includes(filename) && filename.length > 5) {
      references.push(filename);
    }
  }
  
  // Remove inline reference listings (Source X: filename.txt)
  cleaned = cleaned.replace(/\s*Source\s*\d+:\s*[^\n]+/gi, '');
  
  // Remove existing References sections (we'll add a clean one)
  cleaned = cleaned.replace(/<query-h[1-6][^>]*>\s*References?\s*<\/query-h[1-6]>[\s\S]*?(?=<query-h[1-6]>|$)/gi, '');
  
  // Remove "Sources:" section at the end
  cleaned = cleaned.replace(/Sources:[\s\S]*$/i, '');
  
  // Clean up empty lines and excessive whitespace
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  
  // ======================
  // REFERENCES SECTION CREATION
  // ======================
  
  // Add clean References section if we have references
  if (references.length > 0) {
    // Remove duplicates while preserving order
    const uniqueRefs = [...new Set(references)];
    
    cleaned += '\n\n<query-h2 class="query-h2 references-header">📚 References</query-h2>\n\n';
    
    uniqueRefs.forEach((ref, index) => {
      cleaned += `<div class="reference-item"><span class="ref-number">${index + 1}.</span> ${ref}</div>\n`;
    });
  }
  
  // ======================
  // INLINE FORMATTING
  // ======================
  
  // Format citation numbers
  cleaned = cleaned.replace(/\[(\d+)\]/g, '<span class="citation-ref">[$1]</span>');
  
  // Handle [LIT] placeholder - convert to actual citation after numbering
  // Find where "the literature" file is in references and use that number
  const litIndex = references.findIndex(r => r.toLowerCase().includes('literature') || 
                                               r.toLowerCase().includes('euv lithography light source'));
  if (litIndex !== -1) {
    cleaned = cleaned.replace(/\[LIT\]/g, `<span class="citation-ref">[${litIndex + 1}]</span>`);
  } else {
    // If not found, use a generic citation
    cleaned = cleaned.replace(/\[LIT\]/g, '<span class="citation-ref">[Lit]</span>');
  }
  
  // Bold and italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  
  // Bullet points
  cleaned = cleaned.replace(/^- (.+)$/gm, '• $1');
  
  // Convert newlines to <br>
  cleaned = cleaned.replace(/\n/g, '<br>');
  cleaned = cleaned.replace(/(<br>){3,}/g, '<br><br>');
  
  return cleaned;
}

/**
 * Alternative: Simpler approach for the backend to pre-process before sending
 */
export function preprocessResponseForFormatting(text: string): string {
  if (!text) return '';
  
  let processed = text;
  
  // Fix spacing in headings
  processed = processed.replace(/^(#{1,6})([A-Za-z])/gm, '$1 $2');
  
  // Standardize citations early
  processed = processed.replace(/\(?Source\s+(\d+)\)?/gi, '[$1]');
  processed = processed.replace(/the literature/gi, '[LIT]');
  
  // Clean up multiple spaces
  processed = processed.replace(/\s{2,}/g, ' ');
  
  return processed;
}

// ======================
// CSS STYLES (Same as before, with minor additions)
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
  cursor: pointer;
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
  text-align: left;
}

.query-answer .reference-item .ref-number {
  font-weight: 700;
  color: #4CAF50;
  min-width: 24px;
  flex-shrink: 0;
}

.query-answer query-h1 {
  font-size: 1.5em;
  color: #00d4ff;
  margin: 24px 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid #00d4ff;
  display: block;
  font-weight: 700;
}

.query-answer query-h2 {
  font-size: 1.25em;
  color: #ffffff;
  margin: 20px 0 12px 0;
  padding: 6px 0;
  border-bottom: 1px solid #555;
  display: block;
  font-weight: 700;
}

.query-answer query-h3 {
  font-size: 1.1em;
  color: #e0e0e0;
  margin: 16px 0 10px 0;
  padding-left: 10px;
  border-left: 3px solid #00d4ff;
  display: block;
  font-weight: 600;
}

.query-answer query-h4 {
  font-size: 1em;
  color: #b0b0b0;
  margin: 12px 0 8px 0;
  display: block;
  font-weight: 600;
}
*/
