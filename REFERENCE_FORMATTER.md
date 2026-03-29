# KG RAG Output Formatting Improvements

## Summary of Changes

### 1. Heading Formatting (Fixed)
**Before (Issue):**
```html
<strong class="query-h1"># Introduction to Topic</strong>
```
Shows: **# Introduction to Topic** (with # character)

**After (Fixed):**
```html
<query-h1 class="query-h1">Introduction to Topic</query-h1>
```
Shows: **Introduction to Topic** (bold title, no # character)

### 2. Citation Formatting (Improved)
**Before:**
```
According to Source 1 and Source 2, the data shows...
```

**After:**
```
According to [1] and [2], the data shows...
Sources displayed as: [1] [2] [3] (styled badges)
```

### 3. References Section (New)
**Structure:**
```
📚 References

1. document1.pdf
2. document2.pdf
3. research-paper.md
```

Styled with:
- Green left border
- Subtle background
- Numbered with styled badges

---

## Implementation Guide

### Step 1: Update Frontend (QueryTab.ts)

Replace the `formatQueryResponse` function with the improved version from:
`/Users/ken/clawd_workspace/projects/KG_RAG/v1.2-beta/frontend/src/components/tabs/QueryTab_improved.ts`

### Step 2: Update Backend (query.js)

Replace the `formatMarkdownToHtml` function with the improved version from:
`/Users/ken/clawd_workspace/projects/KG_RAG/v1.2-beta/backend/js/query_improved.js`

### Step 3: Add CSS Styles

Add the CSS styles (provided in the improved files) to your stylesheet or HTML.

---

## Key Improvements

### Heading Regex Fixed
```javascript
// OLD - keeps # characters
formatted = formatted.replace(/^(#{1,6})\s+(.+)$/gm, (match, hashes, heading) => {
    return `<h${hashes.length} class="md-h${hashes.length}">${hashes}${heading.trim()}</h${hashes.length}>`;
});

// NEW - removes # characters
formatted = formatted.replace(/^(#{1,6})\s+(.+)$/gm, (match, hashes, content) => {
    const level = hashes.length;
    return `<h${level} class="md-h${level}">${content.trim()}</h${level}>`;
});
```

### Citation Formatting Added
```javascript
// Format "Source X" citations
formatted = formatted.replace(/Source\s+(\d+)/gi, (match, num) => {
    return `<span class="citation-ref">[${num}]</span>`;
});

// Format reference numbers
formatted = formatted.replace(/\[(\d+)\]/g, (match, num) => {
    return `<span class="citation-ref">[${num}]</span>`;
});
```

### References Section Styling
```javascript
// Format References header
formatted = formatted.replace(/^(References?|Bibliography|Citations?)$/gmi, 
    '<h2 class="query-h2 references-header">📚 References</h2>');

// Format numbered references
formatted = formatted.replace(/^(\d+)[\.\)]\s+(.+)$/gm, (match, num, content) => {
    if (content.match(/\.(pdf|doc|txt|md|json)/i) || content.length < 200) {
        return `<div class="reference-item"><span class="ref-number">${num}.</span> ${content}</div>`;
    }
    return match;
});
```

---

## CSS Classes Added

| Class | Purpose |
|-------|---------|
| `.md-h1` - `.md-h6` | Heading styles (backend) |
| `.query-h1` - `.query-h4` | Heading styles (frontend) |
| `.citation-ref` | Styled citation badges [1], [2], etc. |
| `.references-header` | References section header |
| `.reference-item` | Individual reference entry |
| `.ref-number` | Reference number styling |

---

## Testing Checklist

- [ ] Headings render without `#` characters
- [ ] Bold headings use proper styling
- [ ] Citations appear as styled badges [1], [2]
- [ ] References section has proper header
- [ ] Reference items have green border and numbering
- [ ] Tables format correctly
- [ ] Bold and italic text work
- [ ] Bullet points render properly
