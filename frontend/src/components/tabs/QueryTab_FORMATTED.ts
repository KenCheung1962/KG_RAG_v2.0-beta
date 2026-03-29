/**
 * Format query response - EXACT OUTPUT FORMAT as specified
 * 
 * Format:
 * - Title: Answer-h1 (Cyan, bigger, bold) - max 6 words
 * - Executive Summary/Subtitles: Answer-h2 (green, bold)
 * - Content: normal white text
 * - Citations: [1], [2] badges
 * - Conclusion: Answer-h2 (green bold)
 * - 📚 References: Green header with numbered items
 * - 🔍 Sources: Orange header for verification
 */

export function formatQueryResponse(text: string): string {
  if (!text) return '';

  const originalText = text;
  let cleaned = text;

  // STEP 1: Remove malformed LLM ##References with Source X:
  cleaned = cleaned.replace(
    /##\s*References\s*\n?\d*\s*Source\s+\d+:[\s\S]*?(?=\n##|\nSources:|Sources:|$)/gi,
    ''
  );

  // STEP 2: Fix period at start of paragraphs
  cleaned = cleaned.replace(/([a-zA-Z])\n\s*\.\s+/g, '$1. ');
  cleaned = cleaned.replace(/\n\.\s+/g, '\n');

  // STEP 3: Remove disclaimers and noise
  cleaned = cleaned.replace(/Note on Context[\s\S]*?I will answer[^.]*\./gi, '');
  cleaned = cleaned.replace(/Context Note[\s\S]*?general knowledge[^.]*\./gi, '');
  cleaned = cleaned.replace(/The provided context discusses[\s\S]*?unrelated to[\s\S]*?\./gi, '');
  cleaned = cleaned.replace(/I will answer your question based on (?:general |my )?knowledge[^.]*\./gi, '');
  cleaned = cleaned.replace(/Based on (?:general |my )?knowledge,?[^.]*\./gi, '');
  cleaned = cleaned.replace(/\(Remove this[^)]*\)/gi, '');
  cleaned = cleaned.replace(/\[Remove this[^\]]*\]/gi, '');

  const disclaimersToRemove = [
    /I couldn't find any information[^.]*\./gi,
    /Please try a different search term[^.]*\./gi,
    /The indexed data may contain formatting issues[^.]*\./gi,
    /Note: This response is based on[^.]*\./gi,
    /Disclaimer:[^.]*\./gi,
    /I apologize, but[^.]*\./gi,
    /I don't see any information[^.]*\./gi,
    /There is no information[^.]*\./gi,
    /The context provided (?:does not|doesn't) (?:contain|have|discuss)[^.]*\./gi,
  ];
  disclaimersToRemove.forEach(pattern => {
    cleaned = cleaned.replace(pattern, '');
  });

  // STEP 4: Store Sources section
  let sourcesSection = '';
  const sourcesMatch = cleaned.match(/Sources:([\s\S]*)$/i);
  if (sourcesMatch) {
    sourcesSection = sourcesMatch[1].trim();
  }
  cleaned = cleaned.replace(/Sources:[\s\S]*$/i, '');

  // STEP 5: Extract references from original
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

  // STEP 6: Pre-process headings
  cleaned = cleaned.replace(/^(#+)([A-Za-z])/gm, '$1 $2');
  cleaned = cleaned.replace(/^(#+)([A-Za-z]+)\s*(\d+)\s+/gm, '$1 $2 $3 ');
  cleaned = cleaned.replace(/^(#{1,6})([A-Z][a-z]+)([A-Z])/gm, '$1 $2$3');

  // STEP 7: Separate headings from content
  cleaned = cleaned.replace(/([.!?])(#{1,6}\s)/g, '$1\n$2');
  cleaned = cleaned.replace(/([a-z])(#{1,6}\s)/gi, '$1\n$2');

  // STEP 8: Convert headings to EXACT FORMAT
  // H1 = Title (Cyan, max 6 words)
  // H2 = Executive Summary/Subtitles (Green, max 8 words)
  // H3 = Subsections (Green, max 10 words)
  cleaned = cleaned.replace(/^(#{1,6})\s+(.+?)$/gm, (match, hashes, content) => {
    const level = hashes.length;
    let cleanContent = content.trim();
    
    // Skip References headers
    if (/^References?$/i.test(cleanContent)) return '';
    if (cleanContent.length < 2) return '';
    
    // Word limits based on level
    const words = cleanContent.split(/\s+/);
    let maxWords = 10;
    let className = 'answer-h3';
    
    if (level === 1) {
      maxWords = 6;
      className = 'answer-h1'; // Title - Cyan
    } else if (level === 2) {
      maxWords = 8;
      className = 'answer-h2'; // Subtitle - Green
    } else {
      maxWords = 10;
      className = 'answer-h2'; // H3+ also use h2 style (green)
    }
    
    if (words.length > maxWords) {
      cleanContent = words.slice(0, maxWords).join(' ') + '...';
    }
    
    return `<${className} class="${className}">${cleanContent}</${className}>`;
  });

  // STEP 9: Format content
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  
  // Add spacing after headings
  cleaned = cleaned.replace(/(<\/answer-h[123]>)([A-Z])/g, '$1<br><br>$2');
  
  // Remove period at start
  cleaned = cleaned.replace(/<br>\s*\.\s+/gi, '<br>');
  cleaned = cleaned.replace(/<br><br>\s*\.\s+/gi, '<br><br>');
  
  // Format bold and italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  
  // Format citations [1], [2], etc.
  cleaned = cleaned.replace(/\[(\d+)\]/g, '<span class="citation-ref">[$1]</span>');
  
  // Convert newlines
  cleaned = cleaned.replace(/\n/g, '<br>');
  cleaned = cleaned.replace(/(<br>){4,}/g, '<br><br><br>');

  // STEP 10: Add 📚 References section (Green)
  const uniqueRefs = references.filter(r => r && r.length > 3);
  
  if (uniqueRefs.length > 0) {
    cleaned += '<br><br><div class="references-section"><div class="references-header">📚 References</div>';
    
    uniqueRefs.forEach((ref, index) => {
      cleaned += `<div class="reference-item"><span class="ref-number">${index + 1}.</span> ${ref}</div>`;
    });
    
    cleaned += '</div>';
  }

  // STEP 11: Add 🔍 Sources section (Orange)
  if (sourcesSection) {
    cleaned += '<br><br><div class="sources-section"><div class="sources-header">🔍 Sources (for Verification)</div>';
    cleaned += '<div class="sources-list">';
    
    sourcesSection.split(/\n/).forEach(line => {
      if (line.trim()) cleaned += `<div class="source-item">${line.trim()}</div>`;
    });
    
    cleaned += '</div></div>';
  }

  return cleaned;
}

// ======================
// CSS STYLES - EXACT FORMAT
// ======================
/*
// Title - Cyan, bigger, bold (max 6 words)
.query-answer .answer-h1 {
  display: block;
  font-size: 2em;
  font-weight: 800;
  color: #00d4ff;
  margin: 28px 0 20px 0;
  padding-bottom: 12px;
  border-bottom: 3px solid #00d4ff;
}

// Subtitles - Green, bold (max 8 words)
.query-answer .answer-h2 {
  display: block;
  font-size: 1.4em;
  font-weight: 700;
  color: #4CAF50;
  margin: 24px 0 16px 0;
  padding: 8px 0;
  border-bottom: 2px solid #4CAF50;
}

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
}

// References Section - Green theme
.query-answer .references-section {
  margin-top: 32px;
  padding-top: 16px;
  border-top: 2px solid #4CAF50;
}

.query-answer .references-header {
  font-size: 1.6em;
  font-weight: 800;
  color: #4CAF50;
  text-align: center;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid #4CAF50;
}

.query-answer .reference-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  margin: 8px 0;
  background: rgba(76, 175, 80, 0.08);
  border-radius: 8px;
  border-left: 4px solid #4CAF50;
  font-size: 0.95em;
}

.query-answer .reference-item .ref-number {
  font-weight: 700;
  color: #4CAF50;
  min-width: 28px;
  flex-shrink: 0;
}

// Sources Section - Orange theme
.query-answer .sources-section {
  margin-top: 24px;
  padding: 16px;
  background: rgba(255, 152, 0, 0.05);
  border: 2px dashed rgba(255, 152, 0, 0.3);
  border-radius: 8px;
}

.query-answer .sources-header {
  font-size: 1.2em;
  font-weight: 700;
  color: #ff9800;
  margin-bottom: 12px;
  padding-left: 8px;
  border-left: 4px solid #ff9800;
}

.query-answer .sources-list {
  font-family: 'Courier New', monospace;
  font-size: 0.85em;
}

.query-answer .source-item {
  color: #aaa;
  padding: 4px 0;
  border-bottom: 1px dotted rgba(255, 255, 255, 0.1);
  word-break: break-all;
}

.query-answer .source-item:last-child {
  border-bottom: none;
}
*/
