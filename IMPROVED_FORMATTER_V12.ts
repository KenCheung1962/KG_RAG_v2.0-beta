/**
 * IMPROVED FORMATTER v12 - Keep clean References, remove only malformed LLM inline refs
 * 
 * KEEP: ## References\n1. filename\n2. filename (clean format)
 * REMOVE: ##References 6346 Source 1: filename Source 2: filename (malformed)
 */

/**
 * Format query response with improved styling
 */
export function formatQueryResponse(text: string): string {
  if (!text) return '';

  const originalText = text;
  let cleaned = text;

  // ======================
  // STEP 1: REMOVE ONLY MALFORMED LLM INLINE REFERENCES
  // ======================
  
  // Pattern 1: ##References immediately followed by a number (like 6346) and source listings
  // This is the malformed LLM-generated inline reference block
  cleaned = cleaned.replace(
    /##+\s*References?\s*\n?\s*\d+\s+Source[\s\S]*?(?=\n##+\s|\nSources:|Sources:|$)/i,
    ''
  );
  
  // Pattern 2: ##References with "Source X:" format (no clean numbered list)
  cleaned = cleaned.replace(
    /##+\s*References?\s*\n?\s*Source\s+\d+:[\s\S]*?(?=\n##+\s|\nSources:|Sources:|$)/i,
    ''
  );
  
  // Pattern 3: ##References with "the literature:" in it (LLM inline refs)
  cleaned = cleaned.replace(
    /##+\s*References?[\s\S]*?the\s+literature:[\s\S]*?(?=\n##+\s|\nSources:|Sources:|$)/i,
    ''
  );

  // ======================
  // STEP 2: Remove source listings from body text (but NOT from clean References section)
  // ======================
  
  // Remove "Source X: filename.txt" patterns (these are inline citations, not the clean list)
  cleaned = cleaned.replace(/Source\s+\d+:\s*[^\n]+?(?:\.txt|\.pdf|\.doc|\.md|\.json)/gi, '');
  
  // Remove "the literature: filename.txt" patterns
  cleaned = cleaned.replace(/the\s+literature:\s*[^\n]+?(?:\.txt|\.pdf|\.doc|\.md|\.json)/gi, '');
  
  // Remove inline citations like "(Source 1)" or just "Source 1"
  cleaned = cleaned.replace(/\(?Source\s+\d+\)?/gi, '');
  cleaned = cleaned.replace(/the\s+literature/gi, 'the reference material');

  // ======================
  // STEP 3: Clean up formatting artifacts
  // ======================
  
  cleaned = cleaned.replace(/##\s*#\s*/g, '');
  cleaned = cleaned.replace(/#\s*#\s*/g, '');
  cleaned = cleaned.replace(/\n#\s*\n/g, '\n');
  cleaned = cleaned.replace(/\n##\s*\n/g, '\n');
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

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
  // STEP 5: Extract reference mappings from ORIGINAL text
  // ======================
  
  const references: string[] = [];
  const refPattern = /(?:Source\s*(\d+):|(\d+)\.\s+)([^\n]+?\.(?:txt|pdf|docx?|md|json|csv))/gi;
  let match;
  while ((match = refPattern.exec(originalText)) !== null) {
    const num = match[1] || match[2];
    const filename = match[3].trim();
    if (num && filename && !references.includes(filename)) {
      references[parseInt(num) - 1] = filename;
    }
  }

  // ======================
  // STEP 6: Fix headings
  // ======================
  
  cleaned = cleaned.replace(/^(#+)([A-Za-z]+)\s*(\d+)\s+/gm, '$1 $2 $3 ');
  cleaned = cleaned.replace(/^(#{1,6})([A-Z][a-z]+)([A-Z])/gm, '$1 $2$3');

  // ======================
  // STEP 7: Remove ". " from start of content
  // ======================
  
  cleaned = cleaned.replace(/\n\.\s+/g, '\n');
  cleaned = cleaned.replace(/^\s*\.\s+/gm, '');
  cleaned = cleaned.replace(/(<br>)\.\s+/gi, '$1');

  // ======================
  // STEP 8: Separate headings from content
  // ======================
  
  cleaned = cleaned.replace(/([.!?])(#{1,6}\s)/g, '$1\n$2');
  cleaned = cleaned.replace(/([a-z])(#{1,6}\s)/gi, '$1\n$2');

  // ======================
  // STEP 9: Convert headings to HTML - MAX 8 WORDS
  // ======================
  
  cleaned = cleaned.replace(/^(#{1,6})\s+(.+?)$/gm, (match, hashes, content) => {
    const level = hashes.length;
    let cleanContent = content.trim();
    
    // Keep "References" headers - we'll format them nicely
    if (/^References?$/i.test(cleanContent)) {
      return match; // Keep for now
    }
    
    if (cleanContent.length < 2) return '';
    
    // Truncate to 8 words max
    const words = cleanContent.split(/\s+/);
    if (words.length > 8) {
      cleanContent = words.slice(0, 8).join(' ') + '...';
    }
    
    return `<query-h${level} class="query-h${level}">${cleanContent}</query-h${level}>`;
  });

  // ======================
  // STEP 10: Clean up and format
  // ======================
  
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  
  // Add spacing after headings
  cleaned = cleaned.replace(/(<\/query-h[1-6]>)([A-Z])/g, '$1<br><br>$2');
  
  // Remove ". " at start
  cleaned = cleaned.replace(/<br>\s*\.\s+/gi, '<br>');
  cleaned = cleaned.replace(/<br><br>\s*\.\s+/gi, '<br><br>');
  
  // Bold and italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Convert newlines
  cleaned = cleaned.replace(/\n/g, '<br>');
  cleaned = cleaned.replace(/(<br>){4,}/g, '<br><br><br>');

  // ======================
  // STEP 11: Format the clean References section
  // ======================
  
  // Convert "## References" to styled heading, keep the numbered list
  cleaned = cleaned.replace(
    /##+\s*References?\s*<br>/i,
    '<br><br><query-h1 class="query-h1 reference-main-header">📚 Reference</query-h1><br><br>'
  );
  
  // Format numbered references (1. filename.txt)
  cleaned = cleaned.replace(
    /(\d+)\.\s+([^<\n]+?\.(?:txt|pdf|docx?|md|json))/gi,
    '<div class="reference-item"><span class="ref-number">$1.</span> $2</div>'
  );

  // ======================
  // STEP 12: Add Sources section
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
