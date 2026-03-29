/**
 * IMPROVED formatMarkdownToHtml for query.js
 * - Keeps Sources section for verification
 * - Proper heading formatting
 * - Consistent citations
 */

/**
 * Format markdown-style text to HTML
 * PRESERVES Sources section at the end for double-checking
 * @param {string} text - Raw markdown text
 * @returns {string} - HTML formatted text
 */
function formatMarkdownToHtml(text) {
    if (!text) return '';

    // Normalize line endings
    let formatted = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    
    // Store Sources section before cleaning
    let sourcesSection = '';
    const sourcesMatch = formatted.match(/Sources:([\s\S]*)$/i);
    if (sourcesMatch) {
        sourcesSection = sourcesMatch[1].trim();
    }
    
    // Store reference mappings
    const sourceMap = new Map();
    const sourceListingPattern = /Source\s*(\d+):\s*([^\n]+)/gi;
    let match;
    while ((match = sourceListingPattern.exec(formatted)) !== null) {
        sourceMap.set(match[1], match[2].trim());
    }
    
    // Check for literature file
    const litMatch = formatted.match(/the\s+literature:\s*([^\n]+)/i);
    let literatureFile = litMatch ? litMatch[1].trim() : '';
    
    // Remove disclaimers
    const disclaimersToRemove = [
        /Note on Context[\s\S]*?I will answer[^.]*\./gi,
        /Context Note[\s\S]*?general knowledge[^.]*\./gi,
        /The provided context discusses[\s\S]*?unrelated to[\s\S]*?\./gi,
        /I will answer your question based on (?:general |my )?knowledge[^.]*\./gi,
        /Based on (?:general |my )?knowledge,?[^.]*\./gi,
    ];
    disclaimersToRemove.forEach(pattern => {
        formatted = formatted.replace(pattern, '');
    });
    
    // Clean up whitespace
    formatted = formatted.replace(/\n{4,}/g, '\n\n\n');

    // ======================
    // PRE-PROCESSING FIXES
    // ======================
    
    // Fix headings without space after #
    formatted = formatted.replace(/^(#{1,6})([A-Za-z])/gm, '$1 $2');
    
    // Fix headings merged with numbers
    formatted = formatted.replace(/^(#{1,6})([A-Za-z]+)(\d+)/gm, '$1 $2$3');

    // ======================
    // CITATION STANDARDIZATION
    // ======================
    
    // Convert "Source X" to [X]
    formatted = formatted.replace(/\(?Source\s+(\d+)\)?/gi, '[$1]');
    
    // Handle "the literature"
    const hasLiterature = /the literature/gi.test(formatted);
    if (hasLiterature) {
        formatted = formatted.replace(/the literature/gi, '[LIT]');
    }

    // ======================
    // HEADING FORMATTING
    // ======================
    
    // Insert newline before heading markers
    formatted = formatted.replace(/(?<![\n])([.!?:])(#{1,6}\s)/g, '$1\n$2');
    
    // Convert markdown headings to HTML (REMOVES the # characters)
    formatted = formatted.replace(/^(#{1,6})\s+(.+?)$/gm, (match, hashes, content) => {
        const level = hashes.length;
        return `<h${level} class="md-h${level}">${content.trim()}</h${level}>`;
    });
    
    // ======================
    // CLEANUP
    // ======================
    
    // Remove inline source listings (keep in Sources section)
    formatted = formatted.replace(/\s*Source\s*\d+:\s*[^\n]+/gi, '');
    formatted = formatted.replace(/\s*the\s+literature:\s*[^\n]+/gi, '');
    
    // Remove duplicate References headers
    formatted = formatted.replace(/<h[1-6][^>]*>\s*References?\d*\s*<\/h[1-6]>/gi, '');

    // ======================
    // FORMATTING
    // ======================
    
    // Format citation numbers
    formatted = formatted.replace(/\[(\d+)\]/g, '<span class="citation-ref">[$1]</span>');
    
    // Handle [LIT] citation
    let litNum = 0;
    const references = [];
    sourceMap.forEach((filename, num) => {
        references[parseInt(num) - 1] = filename;
        if (filename === literatureFile) {
            litNum = parseInt(num);
        }
    });
    
    if (litNum === 0 && literatureFile) {
        litNum = references.length + 1;
        references.push(literatureFile);
    }
    
    if (litNum > 0) {
        formatted = formatted.replace(/\[LIT\]/g, `<span class="citation-ref">[${litNum}]</span>`);
    } else {
        formatted = formatted.replace(/\[LIT\]/g, '');
    }
    
    // Format bold, italic, etc.
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    formatted = formatted.replace(/~~([^~]+)~~/g, '<del>$1</del>');
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
    formatted = formatted.replace(/^- (.+)$/gm, '<span class="md-bullet">•</span> $1');
    formatted = formatted.replace(/^\* (.+)$/gm, '<span class="md-bullet">•</span> $1');
    
    // Convert newlines to <br>
    formatted = formatted.replace(/\n/g, '<br>');
    formatted = formatted.replace(/(<br>){4,}/g, '<br><br><br>');
    
    // ======================
    // ADD REFERENCES SECTION
    // ======================
    
    if (references.length > 0) {
        formatted += '<br><br><h2 class="md-h2 references-header">📚 References</h2><br><br>';
        
        references.forEach((ref, index) => {
            if (ref) {
                formatted += `<div class="reference-item"><span class="ref-number">${index + 1}.</span> ${ref}</div>`;
            }
        });
    }
    
    // ======================
    // ADD SOURCES SECTION (for verification)
    // ======================
    
    if (sourcesSection) {
        formatted += '<br><br><h3 class="md-h3 sources-header">🔍 Sources (Verification)</h3><br>';
        formatted += '<div class="sources-verification">';
        
        const sourceLines = sourcesSection.split(/\n|(?=\d+\.\s)/).filter(line => line.trim());
        
        if (sourceLines.length > 0) {
            sourceLines.forEach(line => {
                const trimmed = line.trim();
                if (trimmed) {
                    formatted += `<div class="source-item-verify">${trimmed}</div>`;
                }
            });
        } else {
            formatted += `<div class="source-item-verify">${sourcesSection}</div>`;
        }
        
        formatted += '</div>';
    }

    return formatted;
}

// ======================
// CSS STYLES (Add to your HTML)
// ======================
/*
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
}

.md-h1 { font-size: 1.8em; font-weight: 700; color: #00d4ff; margin: 24px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid #00d4ff; }
.md-h2 { font-size: 1.5em; font-weight: 700; color: #ffffff; margin: 20px 0 12px 0; padding: 6px 0; border-bottom: 1px solid #555; }
.md-h3 { font-size: 1.25em; font-weight: 600; color: #e0e0e0; margin: 16px 0 10px 0; padding-left: 12px; border-left: 3px solid #00d4ff; }
.md-h4 { font-size: 1.1em; font-weight: 600; color: #cccccc; margin: 12px 0 8px 0; }

.references-header { margin-top: 32px !important; padding-top: 16px; border-top: 2px solid #4CAF50 !important; border-bottom: none !important; }

.reference-item {
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

.ref-number { font-weight: 700; color: #4CAF50; min-width: 24px; flex-shrink: 0; }

// Sources verification section
.sources-header { 
    margin-top: 24px !important; 
    color: #ff9800 !important; 
    border-left: 3px solid #ff9800 !important; 
}

.sources-verification {
    background: rgba(255, 152, 0, 0.05);
    border: 1px dashed rgba(255, 152, 0, 0.3);
    border-radius: 8px;
    padding: 12px;
    margin-top: 8px;
}

.source-item-verify {
    font-family: 'Courier New', monospace;
    font-size: 0.85em;
    color: #aaa;
    padding: 4px 0;
    border-bottom: 1px dotted rgba(255, 255, 255, 0.1);
    word-break: break-all;
}

.source-item-verify:last-child { border-bottom: none; }

.md-bullet { color: #4CAF50; font-weight: bold; margin-right: 8px; }

code { background: rgba(0, 0, 0, 0.3); padding: 2px 6px; border-radius: 4px; font-family: 'Courier New', monospace; font-size: 0.9em; color: #ffdd00; }
*/
