/**
 * IMPROVED FORMATTER v7 - Keep clean References section, fix content starting with "."
 * 
 * Issues Fixed:
 * 1. Content should not start with "."
 * 2. Keep the LAST clean References section (numbered list)
 * 3. Remove only malformed inline References sections
 */

/**
 * Format query response with improved styling
 */
export function formatQueryResponse(text: string): string {
  if (!text) return '';

  let cleaned = text;

  // ======================
  // STEP 1: Remove stray ## # patterns
  // ======================
  
  cleaned = cleaned.replace(/##\s*#\s*/g, '');
  cleaned = cleaned.replace(/#\s*#\s*/g, '');

  // ======================
  // STEP 2: Fix headings merged with numbers
  // ======================
  
  // Pattern: #Extreme 1 Ultraviolet -> # Extreme 1 Ultraviolet
  cleaned = cleaned.replace(/^(#+)([A-Za-z]+)\s*(\d+)\s+/gm, '$1 $2 $3 ');
  cleaned = cleaned.replace(/^(#{1,6})([A-Z][a-z]+)([A-Z])/gm, '$1 $2$3');

  // ======================
  // STEP 3: Remove ONLY the malformed inline References section
  // ======================
  
  // Remove the malformed ##References8063 Source X: ... section
  // This matches ##References followed immediately by numbers and source listings (not a clean numbered list)
  cleaned = cleaned.replace(/##+\s*References?\d+\s*Source[\s\S]*?(?=##+\s|$)/i, '');
  
  // Remove inline "Source X: filename" patterns from body text
  cleaned = cleaned.replace(/Source\s+\d+:\s*[^\n]+/gi, '');
  cleaned = cleaned.replace(/the\s+literature:\s*[^\n]+/gi, '');

  // ======================
  // STEP 4: Store Sources section
  // ======================
  
  let sourcesSection = '';
  const sourcesMatch = cleaned.match(/Sources:([\s\S]*)$/i);
  if (sourcesMatch) {
    sourcesSection = sourcesMatch[1].trim();
  }
  cleaned = cleaned.replace(/Sources:[\s\S]*$/i, '');

  // ======================
  // STEP 5: Extract reference mappings
  // ======================
  
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

  // ======================
  // STEP 6: SEPARATE HEADINGS FROM CONTENT (carefully)
  // ======================
  
  // Add newline after sentence-ending punctuation before heading
  cleaned = cleaned.replace(/([.!?])(#{1,6}\s)/g, '$1\n$2');
  
  // Add newline after lowercase letter before heading (end of paragraph)
  cleaned = cleaned.replace(/([a-z])(#{1,6}\s)/gi, '$1\n$2');

  // ======================
  // STEP 7: Convert headings to HTML
  // ======================
  
  cleaned = cleaned.replace(/^(#{1,6})\s+(.+?)$/gm, (match, hashes, content) => {
    const level = hashes.length;
    const cleanContent = content.trim();
    
    // Skip if it looks like a References header (we'll handle separately)
    if (/^References?$/i.test(cleanContent)) {
      return match; // Keep it for now, will be processed later
    }
    
    if (cleanContent.length < 2) {
      return '';
    }
    
    return `<query-h${level} class="query-h${level}">${cleanContent}</query-h${level}>`;
  });

  // ======================
  // STEP 8: Clean up and format
  // ======================
  
  // Remove empty lines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  
  // Add spacing after headings (before content)
  cleaned = cleaned.replace(/(<\/query-h[1-6]>)([A-Z])/g, '$1<br><br>$2');
  
  // CRITICAL FIX: Remove content that starts with "." (stray punctuation)
  // This happens when a period gets separated from its sentence
  cleaned = cleaned.replace(/<br>\s*\.\s+/g, '. ');
  cleaned = cleaned.replace(/^\s*\.\s+/gm, '');
  
  // Bold and italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Convert newlines to <br>
  cleaned = cleaned.replace(/\n/g, '<br>');
  
  // Clean up excessive breaks
  cleaned = cleaned.replace(/(<br>){4,}/g, '<br><br><br>');
  
  // Fix any remaining "." at start of content
  cleaned = cleaned.replace(/(<query-h[1-6][^>]*>[^<]+<\/query-h[1-6]>)(<br>)*\s*\.\s*/g, '$1$2');

  // ======================
  // STEP 9: Format the References section (keep it, don't replace)
  // ======================
  
  // Find existing References section and format it nicely
  cleaned = cleaned.replace(/##+\s*References?\s*<br>/i, '<br><br><query-h2 class="query-h2 references-header">📚 References</query-h2><br><br>');
  
  // Format numbered references in the existing section
  cleaned = cleaned.replace(/(\d+)\.\s+([^<\n]+?\.(?:txt|pdf|docx?|md|json))/gi, 
    '<div class="reference-item"><span class="ref-number">$1.</span> $2</div>');

  // ======================
  // STEP 10: Add Sources section for verification
  // ======================
  
  if (sourcesSection) {
    cleaned += '<br><br><query-h3 class="query-h3 sources-header">🔍 Sources (Verification)</query-h3><br>';
    cleaned += '<div class="sources-verification">';
    
    const sourceLines = sourcesSection.split(/\n/).filter(line => line.trim());
    
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
