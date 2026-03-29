/**
 * IMPROVED formatMarkdownToHtml function for query.js
 * Replace the existing formatMarkdownToHtml function with this code
 */

/**
 * Format markdown-style text to HTML
 * - Converts markdown headings to styled HTML (removes # characters)
 * - Formats citations with proper styling
 * - Creates organized References section
 * @param {string} text - Raw markdown text
 * @returns {string} - HTML formatted text
 */
function formatMarkdownToHtml(text) {
    if (!text) return '';

    // Normalize line endings
    let formatted = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    
    // Remove disclaimers and notes
    const disclaimersToRemove = [
        /Note on Context[\s\S]*?I will answer[^.]*\./gi,
        /Context Note[\s\S]*?general knowledge[^.]*\./gi,
        /The provided context discusses[\s\S]*?unrelated to[\s\S]*?\./gi,
        /I will answer your question based on (?:general |my )?knowledge[^.]*\./gi,
        /Based on (?:general |my )?knowledge,?[^.]*\./gi,
        /\(Remove this[^)]*\)/gi,
        /\[Remove this[^\]]*\]/gi,
    ];
    disclaimersToRemove.forEach(pattern => {
        formatted = formatted.replace(pattern, '');
    });
    
    // Clean up excessive whitespace
    formatted = formatted.replace(/\n{4,}/g, '\n\n\n');

    // ======================
    // HEADING FORMATTING - IMPROVED
    // ======================
    
    // Step 1: Insert newline before heading markers that don't have one
    formatted = formatted.replace(/(?<![\n])(.)(#{1,6} )/g, '$1\n$2');
    
    // Step 2: Convert markdown headings to HTML (REMOVES the # characters)
    // Pattern: ^#{1,6} (.+)$ -> converts to <h1-h6 class="md-h1-md-h6">
    formatted = formatted.replace(/^(#{1,6})\s+(.+)$/gm, (match, hashes, content) => {
        const level = Math.min(hashes.length, 6);
        const tagName = `h${level}`;
        return `<${tagName} class="md-${tagName}">${content.trim()}</${tagName}>`;
    });
    
    // ======================
    // CITATION FORMATTING
    // ======================
    
    // Format "Source X" citations with proper styling
    formatted = formatted.replace(/Source\s+(\d+)/gi, (match, num) => {
        return `<span class="citation-ref">[${num}]</span>`;
    });
    
    // Format reference numbers like [1], [2] etc.
    formatted = formatted.replace(/\[(\d+)\]/g, (match, num) => {
        return `<span class="citation-ref">[${num}]</span>`;
    });
    
    // ======================
    // REFERENCES SECTION
    // ======================
    
    // Format "References" section header
    formatted = formatted.replace(/^(References?|Bibliography|Citations?)$/gmi, 
        '<h2 class="md-h2 references-header">📚 References</h2>');
    
    // Format numbered references (e.g., "1. filename.pdf" or "1) filename.pdf")
    formatted = formatted.replace(/^(\d+)[\.\)]\s+(.+)$/gm, (match, num, content) => {
        // Only format if it looks like a reference line
        if (content.match(/\.(pdf|doc|docx|txt|md|json|csv|xlsx?|pptx?|html?|xml|zip)/i) || 
            content.length < 200) {
            return `<div class="reference-item"><span class="ref-number">${num}.</span> ${content}</div>`;
        }
        return match;
    });
    
    // Format bold text
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Format italic text
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // Format strikethrough
    formatted = formatted.replace(/~~([^~]+)~~/g, '<del>$1</del>');
    
    // Format code inline
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Format bullet points with proper styling
    formatted = formatted.replace(/^- (.+)$/gm, '<span class="md-bullet">•</span> <span class="md-list-item">$1</span>');
    formatted = formatted.replace(/^\* (.+)$/gm, '<span class="md-bullet">•</span> <span class="md-list-item">$1</span>');

    // Format numbered lists
    formatted = formatted.replace(/^(\d+)\. (.+)$/gm, (match, num, content) => {
        // Skip if already wrapped in reference-item
        if (match.includes('reference-item')) return match;
        return `<span class="md-number">${num}.</span> <span class="md-list-item">${content}</span>`;
    });
    
    // Format blockquotes
    formatted = formatted.replace(/^>\s?(.+)$/gm, '<blockquote>$1</blockquote>');
    
    // Format horizontal rules
    formatted = formatted.replace(/^-{3,}$/gm, '<hr class="md-hr">');
    formatted = formatted.replace(/^\*{3,}$/gm, '<hr class="md-hr">');

    // Convert remaining newlines to <br> for HTML display
    formatted = formatted.replace(/\n/g, '<br>');

    // Clean up excessive <br> sequences
    formatted = formatted.replace(/(<br>){3,}/g, '<br><br>');
    
    // Wrap blockquotes for styling
    formatted = formatted.replace(/(<blockquote>.+?<\/blockquote>)/g, '<div class="md-blockquote">$1</div>');

    return formatted;
}

// ======================
// CSS STYLES TO ADD
// ======================
/*
Add these CSS styles to your HTML file or stylesheet:

.md-h1 {
    font-size: 1.8em;
    font-weight: 700;
    color: #00d4ff;
    margin: 24px 0 16px 0;
    padding-bottom: 8px;
    border-bottom: 2px solid #00d4ff;
    display: block;
}

.md-h2 {
    font-size: 1.5em;
    font-weight: 700;
    color: #ffffff;
    margin: 20px 0 12px 0;
    padding: 6px 0;
    border-bottom: 1px solid #555;
    display: block;
}

.md-h3 {
    font-size: 1.25em;
    font-weight: 600;
    color: #e0e0e0;
    margin: 16px 0 10px 0;
    padding-left: 12px;
    border-left: 3px solid #00d4ff;
    display: block;
}

.md-h4 {
    font-size: 1.1em;
    font-weight: 600;
    color: #cccccc;
    margin: 12px 0 8px 0;
    display: block;
}

.md-h5 {
    font-size: 1em;
    font-weight: 600;
    color: #bbbbbb;
    margin: 10px 0 6px 0;
    display: block;
}

.md-h6 {
    font-size: 0.9em;
    font-weight: 600;
    color: #aaaaaa;
    margin: 8px 0 6px 0;
    display: block;
}

// Citation styling
.citation-ref {
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

.citation-ref:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
}

// References section styling
.references-header {
    margin-top: 32px !important;
    padding-top: 16px;
    border-top: 2px solid #4CAF50 !important;
    border-bottom: none !important;
}

.reference-item {
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

.reference-item .ref-number {
    font-weight: 700;
    color: #4CAF50;
    min-width: 24px;
    flex-shrink: 0;
}

// List styling
.md-bullet {
    color: #4CAF50;
    font-weight: bold;
    margin-right: 8px;
}

.md-list-item {
    display: inline;
}

.md-number {
    color: #4CAF50;
    font-weight: bold;
    margin-right: 8px;
}

// Blockquote styling
.md-blockquote {
    margin: 16px 0;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.05);
    border-left: 4px solid #4CAF50;
    border-radius: 0 8px 8px 0;
}

.md-blockquote blockquote {
    margin: 0;
    font-style: italic;
    color: #cccccc;
}

// Horizontal rule styling
.md-hr {
    border: none;
    height: 2px;
    background: linear-gradient(90deg, transparent, #4CAF50, transparent);
    margin: 24px 0;
}

// Code styling
code {
    background: rgba(0, 0, 0, 0.3);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
    color: #ffdd00;
}

// Strikethrough styling
del {
    text-decoration: line-through;
    opacity: 0.6;
}
*/
