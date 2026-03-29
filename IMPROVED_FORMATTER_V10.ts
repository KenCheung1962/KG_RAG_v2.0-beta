/**
 * IMPROVED FORMATTER v10 - Remove LLM-generated inline References section
 * 
 * Issues Fixed:
 * 1. Detect and REMOVE LLM-generated inline ##References section completely
 * 2. "Reference" (singular) at end, bold, bigger font
 * 3. No ". " at start of paragraphs
 * 4. No # in headings, max 8 words
 */

/**
 * Format query response with improved styling
 */
export function formatQueryResponse(text: string): string {
  if (!text) return '';

  let cleaned = text;

  // ======================
  // STEP 1: AGGRESSIVE REMOVAL OF LLM-GENERATED INLINE REFERENCES
  // ======================
  
  // Pattern: ##References followed by numbers and source listings
  // This matches the LLM-generated inline references block
  cleaned = cleaned.replace(/##+\s*References?[\s\S]*?(?=##+\s*\n|##+\s+[A-Z]|\n##+\s*$|$)/i, '');
  
  // Also remove if it's at the very end (before Sources: or end of text)
  cleaned = cleaned.replace(/##+\s*References?[\s\S]*?(?=Sources:|$)/i, '');
  
  // Remove specific pattern: ##References number Source X: filename...
  cleaned = cleaned.replace(/##+\s*References?\s*\d*[\s\S]*?the\s+literature:[^\n]+/gi, '');
  
  // Remove all "Source X: filename.txt" patterns from body
  cleaned = cleaned.replace(/Source\s+\d+:\s*[^\n]+/gi, '');
  
  // Remove all "the literature: filename.txt" patterns from body
  cleaned = cleaned.replace(/the\s+literature:\s*[^\n]+/gi, '');
  
  // Remove stray numbers that were before source listings (like "7785")
  cleaned = cleaned.replace(/\n?\s*\d{3,}\s*(?=Source\s+\d)/gi, '');

  // ======================
  // STEP 2: Clean up stray characters
  // ======================
  
  cleaned = cleaned.replace(/##\s*#\s*/g, '');
  cleaned = cleaned.replace(/#\s*#\s*/g, '');

  // ======================
  // STEP 3: Fix headings merged with numbers
  // ======================
  
  cleaned = cleaned.replace(/^(#+)([A-Za-z]+)\s*(\d+)\s+/gm, '$1 $2 $3 ');
  cleaned = cleaned.replace(/^(#{1,6})([A-Z][a-z]+)([A-Z])/gm, '$1 $2$3');

  // ======================
  // STEP 4: Store Sources section at end
  // ======================
  
  let sourcesSection = '';
  const sourcesMatch = cleaned.match(/Sources:([\s\S]*)$/i);
  if (sourcesMatch) {
    sourcesSection = sourcesMatch[1].trim();
  }
  cleaned = cleaned.replace(/Sources:[\s\S]*$/i, '');

  // ======================
  // STEP 5: Extract reference mappings from ORIGINAL text
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
  // STEP 6: Remove ". " from start of content
  // ======================
  
  cleaned = cleaned.replace(/\n\.\s+/g, '\n');
  cleaned = cleaned.replace(/^\s*\.\s+/gm, '');
  cleaned = cleaned.replace(/(<br>)\.\s+/gi, '$1');

  // ======================
  // STEP 7: Separate headings from content
  // ======================
  
  cleaned = cleaned.replace(/([.!?])(#{1,6}\s)/g, '$1\n$2');
  cleaned = cleaned.replace(/([a-z])(#{1,6}\s)/gi, '$1\n$2');

  // ======================
  // STEP 8: Convert headings to HTML - MAX 8 WORDS, NO #
  // ======================
  
  cleaned = cleaned.replace(/^(#{1,6})\s+(.+?)$/gm, (match, hashes, content) => {
    const level = hashes.length;
    let cleanContent = content.trim();
    
    // Remove any References headers (LLM might have added them)
    if (/^References?$/i.test(cleanContent)) {
      return '';
    }
    
    if (cleanContent.length < 2) {
      return '';
    }
    
    // TRUNCATE TO MAX 8 WORDS
    const words = cleanContent.split(/\s+/);
    if (words.length > 8) {
      cleanContent = words.slice(0, 8).join(' ') + '...';
    }
    
    return `<query-h${level} class="query-h${level}">${cleanContent}</query-h${level}>`;
  });

  // ======================
  // STEP 9: Clean up and format
  // ======================
  
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  
  // Add spacing after headings
  cleaned = cleaned.replace(/(<\/query-h[1-6]>)([A-Z])/g, '$1<br><br>$2');
  
  // Remove any remaining ". " at start
  cleaned = cleaned.replace(/<br>\s*\.\s+/gi, '<br>');
  cleaned = cleaned.replace(/<br><br>\s*\.\s+/gi, '<br><br>');
  
  // Bold and italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Convert newlines
  cleaned = cleaned.replace(/\n/g, '<br>');
  cleaned = cleaned.replace(/(<br>){4,}/g, '<br><br><br>');

  // ======================
  // STEP 10: Add clean "Reference" section at end
  // ======================
  
  const uniqueRefs = references.filter(r => r && r.length > 3);
  
  if (uniqueRefs.length > 0) {
    cleaned += '<br><br><query-h1 class="query-h1 reference-main-header">📚 Reference</query-h1><br><br>';
    
    uniqueRefs.forEach((ref, index) => {
      cleaned += `<div class="reference-item"><span class="ref-number">${index + 1}.</span> ${ref}</div>`;
    });
  }

  // ======================
  // STEP 11: Add Sources section for verification
  // ======================
  
  if (sourcesSection) {
    cleaned += '<br><br><query-h3 class="query-h3 sources-header">🔍 Sources (Verification)</query-h3><br>';
    cleaned += '<div class="sources-verification">';
    
    sourcesSection.split(/\n/).forEach(line => {
      if (line.trim()) cleaned += `<div class="source-item-verify">${line.trim()}</div>`;
    });
    
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

.query-answer .reference-main-header {
  margin-top: 32px !important;
  padding-top: 16px;
  border-top: 2px solid #4CAF50;
  border-bottom: 2px solid #4CAF50;
  padding-bottom: 8px;
  text-align: center;
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
  font-size: 1.6em;
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
