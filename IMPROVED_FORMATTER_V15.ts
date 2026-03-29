/**
 * IMPROVED FORMATTER v15 - Clean headings without #, bold, size-appropriate, word limits
 * 
 * Heading Rules:
 * - H1 (Title): Max 6 words, largest font, bold
 * - H2 (Subtitle): Max 8 words, large font, bold  
 * - H3 (Section): Max 10 words, medium font, bold
 * - NO # characters in output
 * - NO period at start of paragraphs
 */

/**
 * Format query response with improved styling
 */
export function formatQueryResponse(text: string): string {
  if (!text) return '';

  const originalText = text;
  let cleaned = text;

  // ======================
  // STEP 1: Fix period at start of paragraphs
  // ======================
  
  // Join lines where period got separated from previous sentence
  cleaned = cleaned.replace(/([a-zA-Z])\n\s*\.\s+/g, '$1. ');
  cleaned = cleaned.replace(/([a-zA-Z])\r?\n\.\s+/g, '$1. ');
  
  // Remove standalone periods at line start
  cleaned = cleaned.replace(/^\s*\.\s+/gm, '');
  cleaned = cleaned.replace(/\n\.\s+/g, '\n');

  // ======================
  // STEP 2: Remove malformed ##References with Source X:
  // ======================
  
  cleaned = cleaned.replace(
    /##\s*References\s*\n?\d*\s*Source\s+\d+:[\s\S]*?(?=\n##|\nSources:|$)/gi,
    ''
  );

  // Remove inline source listings
  cleaned = cleaned.replace(/Source\s+\d+:\s*[^\n]+/gi, '');
  cleaned = cleaned.replace(/the\s+literature:\s*[^\n]+/gi, '');
  cleaned = cleaned.replace(/the\s+literature/gi, 'the reference material');

  // Clean up artifacts
  cleaned = cleaned.replace(/##\s*#\s*/g, '');

  // ======================
  // STEP 3: Store Sources section
  // ======================
  
  let sourcesSection = '';
  const sourcesMatch = cleaned.match(/Sources:([\s\S]*)$/i);
  if (sourcesMatch) {
    sourcesSection = sourcesMatch[1].trim();
  }
  cleaned = cleaned.replace(/Sources:[\s\S]*$/i, '');

  // ======================
  // STEP 4: Extract reference mappings from ORIGINAL text
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
  // STEP 5: Pre-process headings (fix spacing issues)
  // ======================
  
  // Fix headings without space after #
  cleaned = cleaned.replace(/^(#{1,6})([A-Za-z])/gm, '$1 $2');
  
  // Fix headings merged with numbers (#Extreme1 -> # Extreme 1)
  cleaned = cleaned.replace(/^(#+)([A-Za-z]+)\s*(\d+)\s+/gm, '$1 $2 $3 ');
  
  // Fix headings where content runs together (#HeadingContent -> # Heading Content)
  cleaned = cleaned.replace(/^(#{1,6})([A-Z][a-z]+)([A-Z])/gm, '$1 $2$3');

  // ======================
  // STEP 6: Separate headings from content
  // ======================
  
  cleaned = cleaned.replace(/([.!?])(#{1,6}\s)/g, '$1\n$2');
  cleaned = cleaned.replace(/([a-z])(#{1,6}\s)/gi, '$1\n$2');

  // ======================
  // STEP 7: Convert headings to HTML - NO #, BOLD, SIZE-APPROPRIATE, WORD LIMITS
  // ======================
  
  cleaned = cleaned.replace(/^(#{1,6})\s+(.+?)$/gm, (match, hashes, content) => {
    const level = hashes.length;
    let cleanContent = content.trim();
    
    // Skip References headers (we'll add our own styled one)
    if (/^References?$/i.test(cleanContent)) {
      return '';
    }
    
    if (cleanContent.length < 2) {
      return '';
    }
    
    // WORD LIMITS based on heading level
    const words = cleanContent.split(/\s+/);
    let maxWords = 10;
    
    if (level === 1) {
      maxWords = 6; // Title: very short
    } else if (level === 2) {
      maxWords = 8; // Subtitle: short
    } else {
      maxWords = 10; // Section headers: moderate
    }
    
    if (words.length > maxWords) {
      cleanContent = words.slice(0, maxWords).join(' ') + '...';
    }
    
    // Use appropriate heading tag (h1-h3 only, h4+ become h3)
    const displayLevel = Math.min(level, 3);
    
    return `<query-h${displayLevel} class="query-h${displayLevel}">${cleanContent}</query-h${displayLevel}>`;
  });

  // ======================
  // STEP 8: Clean up and format
  // ======================
  
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  
  // Add spacing after headings
  cleaned = cleaned.replace(/(<\/query-h[1-3]>)([A-Z])/g, '$1<br><br>$2');
  
  // Final cleanup: remove any ". " that might still appear at start
  cleaned = cleaned.replace(/<br>\s*\.\s+/gi, '<br>');
  cleaned = cleaned.replace(/<br><br>\s*\.\s+/gi, '<br><br>');
  
  // Bold and italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Convert newlines to <br>
  cleaned = cleaned.replace(/\n/g, '<br>');
  cleaned = cleaned.replace(/(<br>){4,}/g, '<br><br><br>');

  // ======================
  // STEP 9: Add clean "Reference" section at end
  // ======================
  
  const uniqueRefs = references.filter(r => r && r.length > 3);
  
  if (uniqueRefs.length > 0) {
    // Use h1 for Reference section (biggest, boldest)
    cleaned += '<br><br><query-h1 class="query-h1 reference-main-header">📚 Reference</query-h1><br><br>';
    
    uniqueRefs.forEach((ref, index) => {
      cleaned += `<div class="reference-item"><span class="ref-number">${index + 1}.</span> ${ref}</div>`;
    });
  }

  // ======================
  // STEP 10: Add Sources section for verification
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
// CSS STYLES - BOLD, SIZE-APPROPRIATE, NO #
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

// Main Reference header - biggest, boldest
.query-answer .reference-main-header {
  margin-top: 32px !important;
  padding-top: 16px;
  border-top: 2px solid #4CAF50;
  border-bottom: 2px solid #4CAF50;
  padding-bottom: 8px;
  text-align: center;
  font-size: 1.8em !important;
  font-weight: 800 !important;
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

// HEADINGS - NO #, BOLD, SIZE-APPROPRIATE
.query-answer query-h1,
.query-answer query-h2,
.query-answer query-h3 {
  display: block;
  font-weight: 700;
}

// H1 - Title (max 6 words)
.query-answer query-h1 {
  font-size: 1.8em;
  font-weight: 800;
  color: #00d4ff;
  margin: 28px 0 18px 0;
  padding-bottom: 10px;
  border-bottom: 3px solid #00d4ff;
}

// H2 - Subtitle (max 8 words)
.query-answer query-h2 {
  font-size: 1.4em;
  font-weight: 700;
  color: #ffffff;
  margin: 22px 0 14px 0;
  padding: 8px 0;
  border-bottom: 2px solid #555;
}

// H3 - Section (max 10 words)
.query-answer query-h3 {
  font-size: 1.15em;
  font-weight: 600;
  color: #e0e0e0;
  margin: 18px 0 12px 0;
  padding-left: 12px;
  border-left: 4px solid #00d4ff;
}
*/
