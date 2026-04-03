# PDF Font Embedding Guide

> **Version**: v2.0-beta  
> **Date**: 2026-04-01  
> **Purpose**: Ensuring math fonts are properly embedded in PDF exports

---

## Overview

When printing to PDF, font embedding is critical for mathematical symbols to display correctly across different devices and PDF viewers. This document explains the solutions implemented and best practices for PDF generation.

---

## The Problem

### Font Dependencies in PDF

| Scenario | Issue |
|----------|-------|
| **Browser Print → PDF** | Web fonts may not be embedded |
| **Missing Fonts** | Math symbols appear as ☐ boxes |
| **Wrong Fonts** | Fallback fonts display incorrect glyphs |
| **Cross-Platform** | PDF looks different on different systems |

### Why It Happens

1. **Web fonts are lazy-loaded**: Fonts loaded from CDN may not be ready when PDF is generated
2. **PDF generators vary**: Chrome, Firefox, Safari handle font embedding differently
3. **Subset issues**: PDF generators may only embed used glyphs
4. **License restrictions**: Some fonts can't be embedded

---

## Solutions Implemented

### Solution 1: Dedicated PDF Export Button (Recommended)

**Implementation**: New "📄 PDF" button with font preloading

**How it works**:
```typescript
async function exportToPDF() {
  // 1. Show loading indicator
  // 2. Preload fonts with <link rel="preload">
  // 3. Define @font-face with CDN URLs
  // 4. Wait for document.fonts.ready
  // 5. Load each math font individually
  // 6. Render KaTeX
  // 7. Auto-trigger print dialog
}
```

**Key Features**:
- ✅ Font preloading hints
- ✅ `@font-face` definitions with direct URLs
- ✅ `font-display: block` (wait for fonts)
- ✅ Loading indicator for user feedback
- ✅ Auto-open print dialog when ready

**Usage**:
1. Click the green **"📄 PDF"** button
2. Wait for "Loading fonts..." indicator
3. Browser print dialog opens automatically
4. Select "Save as PDF"

---

### Solution 2: Font Preloading in Print Template

**Implementation**: Preload hints in print HTML

```html
<!-- In print window HTML -->
<link rel="preconnect" href="https://cdn.jsdelivr.net">
<link rel="preload" href="https://cdn.jsdelivr.net/npm/noto-sans-math@2.1/fonts/NotoSansMath-Regular.woff2" 
      as="font" type="font/woff2" crossorigin>
<link rel="preload" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/fonts/KaTeX_Main-Regular.woff2" 
      as="font" type="font/woff2" crossorigin>
```

**Benefits**:
- Fonts start loading before they're needed
- Browser prioritizes font requests
- Faster rendering when print dialog opens

---

### Solution 3: Embedded Font-Face Definitions

**Implementation**: Define fonts in CSS with full URLs

```css
@font-face {
  font-family: 'Noto Sans Math';
  font-style: normal;
  font-weight: 400;
  font-display: block; /* Important: Block until loaded */
  src: url('https://cdn.jsdelivr.net/npm/noto-sans-math@2.1/fonts/NotoSansMath-Regular.woff2') format('woff2');
  unicode-range: U+2200-22FF, U+27C0-27EF, U+2980-29FF, U+2A00-2AFF, U+2100-214F;
}
```

**Key Properties**:
- `font-display: block` - Wait for font before rendering
- `unicode-range` - Only load math-related glyphs
- Full CDN URLs - PDF generators can fetch fonts

---

### Solution 4: Font Loading API

**Implementation**: JavaScript font loading verification

```javascript
// Wait for all fonts to load
await document.fonts.ready;

// Load specific fonts
const fonts = ['KaTeX_Main', 'KaTeX_Math', 'Noto Sans Math'];
for (const font of fonts) {
  await document.fonts.load(`1em "${font}"`);
}

// Then show content and print
content.style.visibility = 'visible';
window.print();
```

**Benefits**:
- Explicit control over font loading
- Can show loading state to user
- Ensures fonts are ready before print

---

## Browser Compatibility

### PDF Font Embedding by Browser

| Browser | Print to PDF | Font Embedding | Notes |
|---------|-------------|----------------|-------|
| **Chrome** | ✅ Excellent | ✅ Full | Recommended |
| **Edge** | ✅ Excellent | ✅ Full | Uses Chromium |
| **Firefox** | ✅ Good | ✅ Good | May need longer wait |
| **Safari** | ⚠️ Variable | ⚠️ Partial | macOS only |
| **Opera** | ✅ Good | ✅ Good | Uses Chromium |

### Best Practices by Browser

#### Chrome / Edge (Recommended)
1. Use "📄 PDF" button
2. Wait for fonts to load (auto-handled)
3. Select "Save as PDF"
4. Fonts embed automatically

#### Firefox
1. Use "📄 PDF" button
2. May need to wait a few extra seconds
3. Check "Print to File" → PDF

#### Safari (macOS)
1. Use "📄 PDF" button
2. Use "Export as PDF" (not Preview)
3. May have limited font support

---

## File Locations

### Code Changes

| File | Lines | Change |
|------|-------|--------|
| `QueryTab.ts` | 189-201 | Font preloading in print HTML |
| `QueryTab.ts` | 203-230 | `@font-face` definitions |
| `QueryTab.ts` | 367-387 | Print CSS for math |
| `QueryTab.ts` | 489-514 | Font loading script |
| `QueryTab.ts` | 605-800 | **NEW: `exportToPDF()` function** |
| `QueryTab.ts` | 1621 | **NEW: PDF button** |

---

## Troubleshooting

### Issue: Math symbols still appear as boxes

**Diagnosis**: Fonts not embedding

**Solutions**:
1. ✅ Use the "📄 PDF" button (most reliable)
2. ✅ Try Chrome/Edge browser
3. ✅ Wait 5+ seconds before saving PDF
4. ✅ Check internet connection (fonts loaded from CDN)

### Issue: PDF file size is very large

**Cause**: Font files are embedded

**Solutions**:
1. Use `unicode-range` (already implemented) - only embeds math glyphs
2. Print only needed pages
3. Use PDF compression tool after generation

### Issue: KaTeX math not appearing in PDF

**Cause**: JavaScript didn't execute

**Solutions**:
1. ✅ Use "📄 PDF" button (waits for KaTeX)
2. Ensure browser allows JavaScript in print view
3. Try standard print and wait for math to render

### Issue: Different appearance on different computers

**Cause**: PDF viewers handle fonts differently

**Solutions**:
1. Use Adobe Acrobat Reader (best font support)
2. Avoid Preview (macOS) for math-heavy documents
3. Test on target device before finalizing

---

## Alternative Solutions

### Option A: Server-Side PDF Generation

**Approach**: Use Puppeteer or similar on backend

```javascript
// Backend (Node.js with Puppeteer)
const puppeteer = require('puppeteer');
const browser = await puppeteer.launch();
const page = await browser.newPage();
await page.setContent(htmlWithMath);
await page.waitForFunction(() => document.fonts.ready);
await page.pdf({ path: 'output.pdf', format: 'A4' });
```

**Pros**: Guaranteed font embedding, consistent output
**Cons**: Requires backend infrastructure, slower

### Option B: html2pdf.js Library

**Approach**: Client-side PDF generation with html2canvas + jsPDF

```javascript
import html2pdf from 'html2pdf.js';

html2pdf()
  .set({
    html2canvas: { scale: 2 },
    jsPDF: { unit: 'pt', format: 'a4' }
  })
  .from(element)
  .save();
```

**Pros**: Direct PDF generation, no print dialog
**Cons**: Large library, may not support all CSS

### Option C: MathJax SVG Rendering

**Approach**: Pre-render math to SVG

```javascript
// Convert all math to SVG before printing
MathJax.typesetPromise()
  .then(() => {
    // Math is now SVG, no font dependencies
    window.print();
  });
```

**Pros**: No font dependencies, vector graphics
**Cons**: Slower, larger file size

---

## Summary

| Method | Font Embedding | Ease of Use | Recommendation |
|--------|---------------|-------------|----------------|
| Standard Print | ⚠️ Variable | ✅ Easy | For quick prints |
| **"📄 PDF" Button** | ✅ **Excellent** | ✅ **Easy** | **Recommended** |
| Server-Side | ✅ Excellent | ❌ Complex | For production |
| html2pdf.js | ✅ Good | ⚠️ Moderate | Alternative option |
| MathJax SVG | ✅ Excellent | ⚠️ Moderate | For guaranteed compatibility |

**Bottom Line**: Use the "📄 PDF" button for best results with embedded fonts.

---

*End of Guide*
