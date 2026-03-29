/**
 * IMPROVED formatQueryResponse function for QueryTab.ts
 * Replace the existing formatQueryResponse function (lines 433-603) with this code
 */

/**
 * Format query response with improved styling
 * - Converts markdown headings to styled HTML headings (removes # characters)
 * - Formats citations properly
 * - Creates proper References section
 * - Handles tables, bold, italic text
 */
export function formatQueryResponse(text: string): string {
  if (!text) return '';
  
  let cleaned = text;
  
  // Remove "Note on Context" / "Context Note" sections entirely (multi-line)
  cleaned = cleaned.replace(/Note on Context[\s\S]*?I will answer[^.]*\./gi, '');
  cleaned = cleaned.replace(/Context Note[\s\S]*?general knowledge[^.]*\./gi, '');
  
  // Remove standalone irrelevant context explanations
  cleaned = cleaned.replace(/The provided context discusses[\s\S]*?unrelated to[\s\S]*?\./gi, '');
  cleaned = cleaned.replace(/The (?:provided |available |indexed )?context (?:does not contain|lacks|is (?:unrelated|irrelevant))[\s\S]*?\./gi, '');
  
  // Remove "I will answer based on general knowledge" statements
  cleaned = cleaned.replace(/I will answer your question based on (?:general |my )?knowledge[^.]*\./gi, '');
  cleaned = cleaned.replace(/Based on (?:general |my )?knowledge,?[^.]*\./gi, '');
  
  // Remove editor notes like "(Remove this gap)"
  cleaned = cleaned.replace(/\(Remove this[^)]*\)/gi, '');
  cleaned = cleaned.replace(/\[Remove this[^\]]*\]/gi, '');
  
  // Remove common disclaimers
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
  
  // Clean up excessive newlines (more than 2 consecutive)
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  
  // Remove standalone parentheses with instructions
  cleaned = cleaned.replace(/^\s*\([^)]+\)\s*$/gmi, '');
  
  // Fix math equation spacing issues
  cleaned = cleaned.replace(/([A-Za-z])(\t+|\s{2,})([|⟨⟩])/g, '$1 $3');
  cleaned = cleaned.replace(/(\))\t+|\s{2,}([|⟨⟩])/g, '$1 $2');
  cleaned = cleaned.replace(/([|⟨⟩][^|⟨⟩]*?)(\t+|\s{2,})(?=\))/g, '$1');
  cleaned = cleaned.replace(/\t+/g, ' ');
  cleaned = cleaned.replace(/\s{3,}/g, ' ');
  
  // ======================
  // HEADING FORMATTING - IMPROVED
  // ======================
  
  // Step 1: Insert newline before heading markers that don't have one
  cleaned = cleaned.replace(/(?<![\n])(.)(#{1,6} )/g, '$1\n$2');
  
  // Step 2: Convert markdown headings to HTML (REMOVES the # characters)
  // Pattern: ^#{1,6} (.+)$ -> converts to <h1-h6> without the #
  cleaned = cleaned.replace(/^(#{1,6})\s+(.+)$/gm, (match, hashes, content) => {
    const level = hashes.length;
    const className = `query-h${level}`;
    return `<${className} class="${className}">${content.trim()}</${className}>`;
  });
  
  // ======================
  // CITATION FORMATTING
  // ======================
  
  // Extract and format "Source X" citations with proper styling
  cleaned = cleaned.replace(/Source\s+(\d+)/gi, (match, num) => {
    return `<span class="citation-ref">[${num}]</span>`;
  });
  
  // Format reference numbers like [1], [2] etc. with styling
  cleaned = cleaned.replace(/\[(\d+)\]/g, (match, num) => {
    return `<span class="citation-ref">[${num}]</span>`;
  });
  
  // ======================
  // REFERENCES SECTION FORMATTING
  // ======================
  
  // Format "References" section header if present
  cleaned = cleaned.replace(/^(References?|Bibliography|Citations?)$/gmi, 
    '<h2 class="query-h2 references-header">📚 References</h2>');
  
  // Format numbered references in References section (e.g., "1. filename.pdf" or "1) filename.pdf")
  cleaned = cleaned.replace(/^(\d+)[\.\)]\s+(.+)$/gm, (match, num, content) => {
    // Only format if it looks like a reference line (contains file extension or is short)
    if (content.match(/\.(pdf|doc|docx|txt|md|json|csv|xlsx?|pptx?|html?|xml|zip)/i) || 
        content.length < 200) {
      return `<div class="reference-item"><span class="ref-number">${num}.</span> ${content}</div>`;
    }
    return match;
  });
  
  // ======================
  // TABLE FORMATTING
  // ======================
  
  const tableLines = cleaned.split('\n');
  let inTable = false;
  let tableHtml = '';
  const formattedLines: string[] = [];
  
  for (let i = 0; i < tableLines.length; i++) {
    const line = tableLines[i];
    const isTableLine = line.includes('|') && (line.match(/\|/g) || []).length >= 2;
    const isSeparatorLine = /^\s*\|?[-:\s\|]+\|?\s*$/.test(line);
    
    if (isTableLine && !isSeparatorLine) {
      if (!inTable) {
        inTable = true;
        tableHtml = '<div class="query-table-container"><table class="query-table">';
      }
      
      // Parse table row
      const cells = line.split('|').map(c => c.trim()).filter(c => c);
      if (cells.length > 0) {
        const isHeader = i === 0 || (i > 0 && isSeparatorLine && i === 1);
        const cellTag = isHeader ? 'th' : 'td';
        const rowClass = isHeader ? 'query-table-header' : '';
        tableHtml += `<tr class="${rowClass}">${cells.map(c => `<${cellTag}>${escapeHtml(c)}</${cellTag}>`).join('')}</tr>`;
      }
    } else if (isSeparatorLine) {
      // Skip separator lines in markdown tables
      continue;
    } else {
      if (inTable) {
        inTable = false;
        tableHtml += '</table></div>';
        formattedLines.push(tableHtml);
        tableHtml = '';
      }
      formattedLines.push(line);
    }
  }
  
  // Close any open table
  if (inTable) {
    tableHtml += '</table></div>';
    formattedLines.push(tableHtml);
  }
  
  cleaned = formattedLines.join('\n');
  
  // ======================
  // INLINE FORMATTING
  // ======================
  
  // Format bold text
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  
  // Format italic text
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  
  // Format bullet points
  cleaned = cleaned.replace(/^- (.+)$/gm, '• $1');
  cleaned = cleaned.replace(/^\* (.+)$/gm, '• $1');
  
  // Format numbered lists (only if not already formatted as reference)
  cleaned = cleaned.replace(/^(\d+)\.\s+(.+)$/gm, (match, num, content) => {
    // Skip if already wrapped in reference-item
    if (match.includes('reference-item')) return match;
    return `${num}. ${content}`;
  });
  
  // Convert newlines to <br> for HTML display
  cleaned = cleaned.replace(/\n/g, '<br>');
  
  // Clean up empty <br> sequences
  cleaned = cleaned.replace(/(<br>){3,}/g, '<br><br>');
  
  return cleaned;
}

// ======================
// UPDATED CSS TO ADD
// ======================
/* Add these styles to your existing CSS in getQueryTabHTML() */

/*
// Citation references styling
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
}

.query-answer .reference-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 12px;
  margin: 4px 0;
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

// Improved heading styling (no # characters)
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
  margin-top: 24px;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid #00d4ff;
}

.query-answer query-h2 {
  font-size: 1.25em;
  color: #ffffff;
  margin-top: 20px;
  margin-bottom: 12px;
  padding: 6px 0;
  border-bottom: 1px solid #555;
}

.query-answer query-h3 {
  font-size: 1.1em;
  color: #e0e0e0;
  margin-top: 16px;
  margin-bottom: 10px;
  padding-left: 10px;
  border-left: 3px solid #00d4ff;
}

.query-answer query-h4 {
  font-size: 1em;
  color: #b0b0b0;
  margin-top: 12px;
  margin-bottom: 8px;
}
*/
