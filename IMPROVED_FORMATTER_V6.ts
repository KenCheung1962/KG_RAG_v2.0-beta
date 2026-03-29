/**
 * IMPROVED FORMATTER v6 - Robust handling of malformed input
 * 
 * Issues Fixed:
 * 1. Remove stray ## # characters
 * 2. Fix headings merged with numbers (#Extreme 1 Ultraviolet)
 * 3. Separate headings and content properly
 * 4. Remove ALL inline source listings and duplicate References
 * 5. Clean formatting artifacts
 */

/**
 * Format query response with improved styling - ROBUST VERSION
 */
export function formatQueryResponse(text: string): string {
  if (!text) return '';
  
  let cleaned = text;
  
  // ======================
  // STEP 1: Emergency cleanup of malformed patterns
  // ======================
  
  // Remove stray ## # patterns
  cleaned = cleaned.replace(/##\s*#\s*/g, '');
  cleaned = cleaned.replace(/#\s*#\s*/g, '');
  
  // Remove standalone # or ## on their own lines
  cleaned = cleaned.replace(/\n#\s*\n/g, '\n');
  cleaned = cleaned.replace(/\n##\s*\n/g, '\n');
  
  // ======================
  // STEP 2: Fix headings merged with numbers
  // ======================
  
  // Pattern: #Extreme 1 Ultraviolet... -> ## Extreme Ultraviolet...
  cleaned = cleaned.replace(/^(#+)([A-Za-z]+)\s*(\d+)\s+/gm, (match, hashes, word, num) => {
    return `${hashes} ${word} ${num} `;
  });
  
  // Pattern: #HeadingContent (no space) -> # Heading Content
  cleaned = cleaned.replace(/^(#{1,6})([A-Z][a-z]+)([A-Z])/gm, '$1 $2$3');
  
  // ======================
  // STEP 3: Remove ALL References sections with source listings
  // ======================
  
  // Remove inline ##References section (including numbered source listings)
  // Match: ##References followed by numbers and source listings
  cleaned = cleaned.replace(/##+\s*References?[\s\S]*?(?=##+\s|$)/i, '');
  
  // Remove "Source X: filename" patterns anywhere
  cleaned = cleaned.replace(/\n?\s*Source\s*\d+:\s*[^\n]+/gi, '');
  cleaned = cleaned.replace(/\n?\s*the\s+literature:\s*[^\n]+/gi, '');
  
  // Remove standalone source listings (just numbers at start of line followed by source info)
  cleaned = cleaned.replace(/\n\s*\d+\.?\s*Source\s*\d+:\s*[^\n]+/gi, '');
  
  // ======================
  // STEP 4: Store Sources section at end
  // ======================
  
  let sourcesSection = '';
  const sourcesMatch = cleaned.match(/Sources:([\s\S]*)$/i);
  if (sourcesMatch) {
    sourcesSection = sourcesMatch[1].trim();
  }
  
  // Remove Sources: section from main text (we'll add it back at end)
  cleaned = cleaned.replace(/Sources:[\s\S]*$/i, '');
  
  // ======================
  // STEP 5: Extract reference mappings from original
  // ======================
  
  const references: string[] = [];
  const refPattern = /(?:Source\s*(\d+):|(\d+)\.?\s+)([^\n]+?\.(?:txt|pdf|docx?|md|json|csv))/gi;
  let match;
  while ((match = refPattern.exec(text)) !== null) {
    const num = match[1] || match[2];
    const filename = match[3].trim();
    if (num && filename && !references.includes(filename)) {
      references[parseInt(num) - 1] = filename;
    }
  }
  
  // Find literature file
  const litMatch = text.match(/the\s+literature:\s*([^\n]+?\.(?:txt|pdf|docx?|md|json))/i);
  const literatureFile = litMatch ? litMatch[1].trim() : '';
  
  // ======================
  // STEP 6: More aggressive cleaning
  // ======================
  
  // Remove any remaining "Source X" or "the literature" mentions
  cleaned = cleaned.replace(/\(?Source\s+\d+\)?\.?/gi, '');
  cleaned = cleaned.replace(/the\s+literature/gi, 'the reference material');
  
  // Clean up excessive whitespace
  cleaned = cleaned.replace(/\n{4,}/g, '\n\n\n');
  cleaned = cleaned.replace(/[ \t]{3,}/g, ' ');
  
  // ======================
  // STEP 7: SEPARATE HEADINGS FROM CONTENT
  // ======================
  
  // CRITICAL: Add newline after heading if content follows immediately
  // Pattern: ##Heading Content -> ##Heading\nContent
  cleaned = cleaned.replace(/^(#{1,6}\s+[^\n]+?)([A-Z][a-zA-Z][^.!?]*?[a-z])([A-Z])/gm, 
    (match, heading, content, nextLetter) => {
      return heading + '\n' + content + nextLetter;
    });
  
  // Alternative: Find periods or sentence ends followed immediately by #
  cleaned = cleaned.replace(/([.!?])(#{1,6}\s)/g, '$1\n$2');
  
  // Ensure heading is on its own line
  cleaned = cleaned.replace(/([a-z])(#{1,6}\s)/gi, '$1\n$2');
  
  // ======================
  // STEP 8: Convert headings to HTML
  // ======================
  
  cleaned = cleaned.replace(/^(#{1,6})\s+(.+?)$/gm, (match, hashes, content) => {
    const level = Math.min(hashes.length, 6);
    const cleanContent = content.trim();
    
    // Skip References headers
    if (/^References?$/i.test(cleanContent)) {
      return '';
    }
    
    // Skip empty or minimal content
    if (cleanContent.length < 2) {
      return '';
    }
    
    return `<query-h${level} class="query-h${level}">${cleanContent}</query-h${level}>`;
  });
  
  // ======================
  // STEP 9: Clean up and format
  // ======================
  
  // Remove empty lines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  
  // Add proper spacing between sections (after closing heading tags)
  cleaned = cleaned.replace(/(<\/query-h[1-6]>)([A-Z])/g, '$1<br><br>$2');
  
  // Bold and italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  
  // Bullet points
  cleaned = cleaned.replace(/^- (.+)$/gm, '• $1');
  
  // Convert newlines to <br>
  cleaned = cleaned.replace(/\n/g, '<br>');
  
  // Clean up excessive breaks
  cleaned = cleaned.replace(/(<br>){4,}/g, '<br><br><br>');
  
  // ======================
  // STEP 10: Add References section
  // ======================
  
  const uniqueRefs = references.filter(r => r && r.length > 3);
  
  if (uniqueRefs.length > 0) {
    cleaned += '<br><br><query-h2 class="query-h2 references-header">📚 References</query-h2><br><br>';
    
    uniqueRefs.forEach((ref, index) => {
      cleaned += `<div class="reference-item"><span class="ref-number">${index + 1}.</span> ${ref}</div>`;
    });
  }
  
  // ======================
  // STEP 11: Add Sources section (for verification)
  // ======================
  
  if (sourcesSection) {
    cleaned += '<br><br><query-h3 class="query-h3 sources-header">🔍 Sources (Verification)</query-h3><br>';
    cleaned += '<div class="sources-verification">';
    
    const sourceLines = sourcesSection.split(/\n|(?=\d+\.\s)/).filter(line => line.trim());
    
    if (sourceLines.length > 0) {
      sourceLines.forEach(line => {
        const trimmed = line.trim();
        if (trimmed && trimmed.length > 2) {
          cleaned += `<div class="source-item-verify">${trimmed}</div>`;
        }
      });
    } else if (sourcesSection.length > 2) {
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

.query-answer query-h1,
.query-answer query-h2,
.query-answer query-h3,
.query-answer query-h4 {
  display: block;
  font-weight: 700;
  margin-bottom: 12px;
}

.query-answer query-h1 {
  font-size: 1.5em;
  color: #00d4ff;
  margin-top: 24px;
  padding-bottom: 8px;
  border-bottom: 2px solid #00d4ff;
}

.query-answer query-h2 {
  font-size: 1.25em;
  color: #ffffff;
  margin-top: 20px;
  padding: 6px 0;
  border-bottom: 1px solid #555;
}

.query-answer query-h3 {
  font-size: 1.1em;
  color: #e0e0e0;
  margin-top: 16px;
  padding-left: 10px;
  border-left: 3px solid #00d4ff;
}

.query-answer query-h4 {
  font-size: 1em;
  color: #b0b0b0;
  margin-top: 12px;
}
*/
