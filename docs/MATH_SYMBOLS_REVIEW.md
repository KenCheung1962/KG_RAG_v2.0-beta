# Mathematical Symbols Handling Review

> **Version**: v2.0-beta  
> **Date**: 2026-04-01  
> **Scope**: Display and Print handling for mathematical symbols across all query modes

---

## Executive Summary

The system uses a **Unicode-first approach** for mathematical symbols, with **KaTeX as a fallback** for any LaTeX that might appear.

### Status After Fixes (2026-04-01)

| Aspect | Status | Notes |
|--------|--------|-------|
| Backend Generation | ✅ Working | Explicitly uses Unicode math |
| Display (Unicode) | ✅ Fixed | Noto Sans Math font + auto-detection |
| Display (LaTeX) | ✅ Fixed | KaTeX now properly invoked |
| Print | ✅ Fixed | KaTeX + math fonts + page break protection |

### Summary of Fixes Applied
1. ✅ Added `renderMathInElement()` call after content display
2. ✅ Added Noto Sans Math font for Unicode symbols
3. ✅ Added auto-detection and wrapping of math content
4. ✅ Added KaTeX to print template with proper initialization
5. ✅ Added print-specific CSS for math formatting
6. ✅ Added page break protection for equations

---

## 1. Backend Implementation

### 1.1 System Prompt Instructions

**File**: `backend/pgvector_api.py` (lines 1834, 1860)

```python
# From generate_ultra_response() prompt
"""
STRICT REQUIREMENTS:
5. Math: Use Unicode |ψ⟩, α, β, ∑ - NEVER LaTeX
...
6. NEVER use LaTeX - use Unicode math
"""
```

**Unicode Symbols Supported**:
| Symbol | Unicode | Description |
|--------|---------|-------------|
| \|ψ⟩ | U+007C U+03C8 U+27E9 | Quantum state ket notation |
| α | U+03B1 | Greek alpha |
| β | U+03B2 | Greek beta |
| ∑ | U+2211 | Summation |
| ⟨ | U+27E8 | Bra notation left |
| ⟩ | U+27E9 | Bra/ket notation right |
| ∫ | U+222B | Integral |
| ∂ | U+2202 | Partial derivative |
| ∞ | U+221E | Infinity |
| ± | U+00B1 | Plus-minus |
| ° | U+00B0 | Degree |
| ‰ | U+2030 | Per mille |

### 1.2 LLM Behavior

The LLM is explicitly instructed to:
1. **Use Unicode characters** for math symbols
2. **NEVER use LaTeX** (no `$...$`, `\(...\)`, `\[...\]`)
3. **Write equations in plain text** with Unicode symbols

**Example Output**:
```
The quantum state |ψ⟩ can be expressed as:
|ψ⟩ = α|0⟩ + β|1⟩

Where α and β are complex coefficients satisfying:
|α|² + |β|² = 1
```

---

## 2. Frontend Display Handling

### 2.1 KaTeX Integration

**File**: `frontend/src/components/tabs/QueryTab.ts`

**Included Libraries** (lines 1194-1196):
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
```

**KaTeX Configuration** (lines 1044-1073):
```typescript
function renderMathInElement(element: HTMLElement): void {
  if ((window as any).katex && (window as any).renderMathInElement) {
    try {
      (window as any).renderMathInElement(element, {
        delimiters: [
          {left: '$$', right: '$$', display: true},
          {left: '$', right: '$', display: false},
          {left: '\\[', right: '\\]', display: true},
          {left: '\\(', right: '\\)', display: false},
          {left: '\\begin{equation}', right: '\\end{equation}', display: true},
          {left: '\\begin{align}', right: '\\end{align}', display: true},
          {left: '\\begin{matrix}', right: '\\end{matrix}', display: true},
        ],
        throwOnError: false,
        errorColor: '#cc0000',
        macros: {
          '\\RR': '\\mathbb{R}',
          '\\NN': '\\mathbb{N}',
          '\\ZZ': '\\mathbb{Z}',
        }
      });
    } catch (e) {
      console.error('KaTeX rendering error:', e);
    }
  } else {
    // Retry after delay if not loaded
    setTimeout(() => renderMathInElement(element), 500);
  }
}
```

### 2.2 ❌ CRITICAL ISSUE: Function Never Called

**Problem**: `renderMathInElement()` is defined but **never invoked** after content is set.

**Locations where it SHOULD be called** (but isn't):
1. Line 685: After setting partial content during streaming
2. Line 708: After updating content during streaming  
3. Line 723: After setting final content

**Current Code** (line 723):
```typescript
// Format and display final content
answerText!.innerHTML = formatQueryResponse(accumulatedContent);
// MISSING: renderMathInElement(answerText!);
```

### 2.3 Unicode Math Spacing Fix

**File**: `frontend/src/components/tabs/QueryTab.ts` (lines 1002-1005)

```typescript
// Fix math equation spacing
cleaned = cleaned.replace(/([A-Za-z])(\t+|\s{2,})([|⟨⟩])/g, '$1 $3');
cleaned = cleaned.replace(/(\))\t+|\s{2,}([|⟨⟩])/g, '$1 $2');
cleaned = cleaned.replace(/([|⟨⟩][^|⟨⟩]*?)(\t+|\s{2,})(?=\))/g, '$1');
```

**Purpose**: Fixes spacing around bra-ket notation (|ψ⟩) and angle brackets (⟨, ⟩)

### 2.4 CSS Styling for Math

**File**: `frontend/src/components/tabs/QueryTab.ts` (lines 1359-1388)

```css
/* Math Formula Styling */
.query-answer .katex {
  font-size: 1.1em;
  color: var(--text-primary, #e0e0e0);
}

.query-answer .katex-display {
  margin: 1.5em 0;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 1em;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  border-left: 3px solid var(--primary-color, #4CAF50);
}

.query-answer .katex-display .katex {
  font-size: 1.2em;
}

/* Inline math */
.query-answer .katex-inline {
  padding: 0 0.2em;
}

/* Math error coloring */
.query-answer .katex-error {
  color: #ff6b6b;
  border-bottom: 1px dashed #ff6b6b;
}
```

### 2.5 Display Status Summary

| Feature | Status | Notes |
|---------|--------|-------|
| KaTeX library loaded | ✅ Yes | From CDN v0.16.9 |
| KaTeX rendering function | ✅ Defined | Configured with multiple delimiters |
| KaTeX actually invoked | ✅ Fixed | Called after content display |
| Unicode math display | ✅ Fixed | Noto Sans Math + auto-detection |
| Math spacing fix | ✅ Yes | For bra-ket notation |
| CSS styling | ✅ Yes | For rendered math |
| Unicode font support | ✅ Added | 'Noto Sans Math' in font stack |

---

## 3. Print Handling

### 3.1 Print Function Analysis

**File**: `frontend/src/components/tabs/QueryTab.ts` - `printAnswer()` (lines 40-160)

**Math-Related Processing**:

```typescript
function printAnswer(event?: Event): void {
  // ... header processing ...
  
  // Convert <i> tags to markdown italics (line 71)
  processedText = processedText.replace(/<i>([^<]*)<\/i>/gi, '*$1*');
  
  // ... more processing ...
  
  // Convert markdown to HTML for print (lines 88-95)
  let formattedAnswer = processedText
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Bold
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // Italics
    .replace(/\*([^*]+)\*/g, '<i>$1</i>');
}
```

### 3.2 Print Status Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| Unicode math preservation | ✅ Yes | Passed through as-is |
| LaTeX rendering | ✅ Yes | KaTeX loaded and rendered |
| Math-specific formatting | ✅ Yes | Print CSS + Noto Sans Math |
| Font considerations | ✅ Fixed | Noto Sans Math embedded |
| Page break handling | ✅ Yes | `page-break-inside: avoid` |

**Print Features**:
1. ✅ KaTeX library loaded from CDN
2. ✅ Noto Sans Math font for Unicode symbols
3. ✅ Math styled with proper spacing and borders
4. ✅ Equations protected from breaking across pages

### 3.3 PDF Export with Font Embedding

**New Feature**: Dedicated PDF export button with font preloading

**Implementation** (`exportToPDF()` function):

```typescript
// Key features of PDF export:
1. Font preloading with `<link rel="preload">`
2. `@font-face` definitions with embedded URLs
3. `font-display: block` to ensure fonts load before render
4. `document.fonts.ready` wait for all fonts
5. Individual font loading checks for KaTeX fonts
6. Auto-trigger print dialog after fonts loaded
7. Loading indicator while fonts prepare
```

**Font Embedding Strategy**:

| Font | Format | Embedding Method |
|------|--------|------------------|
| Noto Sans Math | WOFF2 | `@font-face` with CDN URL |
| KaTeX_Main | WOFF2 | `@font-face` with CDN URL |
| KaTeX_Math | WOFF2 | `@font-face` with CDN URL |
| KaTeX_Size1 | WOFF2 | `@font-face` with CDN URL |

**PDF Optimization Features**:
- **Font preloading**: `<link rel="preload">` hints for faster loading
- **Unicode range**: Limited to math symbols (U+2200-22FF, etc.)
- **Page size**: A4 format optimized
- **Margins**: 2.0cm top/bottom, 1.5cm sides
- **Print media**: `@media print` CSS rules
- **Page break control**: `page-break-after: avoid` for headings, `page-break-inside: avoid` for math

**Usage**:
1. Click "📄 PDF" button (green, next to Print)
2. Wait for fonts to load (loading indicator shown)
3. Browser print dialog opens automatically
4. Select "Save as PDF" as the destination
5. Fonts are embedded in the generated PDF

---

## 4. Query Mode Differences

All query modes use the **same math handling**:

| Query Mode | Math Generation | Display | Print |
|------------|-----------------|---------|-------|
| **Quick** | Unicode | KaTeX + Unicode fonts | KaTeX + math fonts |
| **Balanced** | Unicode | KaTeX + Unicode fonts | KaTeX + math fonts |
| **Comprehensive** | Unicode | KaTeX + Unicode fonts | KaTeX + math fonts |
| **Ultra-Deep** | Unicode | KaTeX + Unicode fonts | KaTeX + math fonts |

**Note**: All modes use the same `formatQueryResponse()` and `printAnswer()` functions with identical math support.

---

## 5. Issues & Fixes

### 5.1 Fixed Issues ✅

#### Issue 1: KaTeX Never Called (Display) ✅ FIXED
- **Severity**: 🔴 High
- **Status**: ✅ **FIXED**
- **Fix Applied**: Added `renderMathInElement(answerText!)` call after content display
- **Location**: `frontend/src/components/tabs/QueryTab.ts` line 799

```typescript
// After line 796:
answerText!.innerHTML = formatQueryResponse(accumulatedContent);
renderMathInElement(answerText!);  // Renders LaTeX math
```

#### Issue 2: No Font Fallback for Unicode Math ✅ FIXED
- **Severity**: 🟡 Medium
- **Status**: ✅ **FIXED**
- **Fix Applied**: 
  - Added Noto Sans Math font to main display CSS (line 1279)
  - Added `unicode-math` CSS class for math content (line 1284)
  - Auto-detection and wrapping of math-heavy content (lines 1094-1108)

#### Issue 3: No Print-Specific Math Handling ✅ FIXED
- **Severity**: 🟡 Medium  
- **Status**: ✅ **FIXED**
- **Fix Applied**:
  - Added KaTeX library to print HTML template (lines 189-192)
  - Added Noto Sans Math font for print (line 195)
  - Added print-specific CSS for math styling (lines 367-387)
  - Added `renderMathInElement` call on print page load (lines 489-514)
  - Added `page-break-inside: avoid` to prevent math breaking across pages

### 5.2 Recently Fixed Issues

#### Issue 4: LaTeX in Comprehensive Mode (NEW) ✅ FIXED
- **Severity**: 🟡 Medium
- **Status**: ✅ **FIXED**
- **Problem**: Comprehensive mode was generating LaTeX math (`\( G = (V, E) \)`) instead of Unicode
- **Root Cause**: Streaming prompts didn't include "NEVER use LaTeX" instruction
- **Fix Applied**:
  1. Added Unicode math instruction to all streaming prompts (lines 5120, 5181, 5225)
  2. Added system prompt instruction for all LLM calls
  3. Created `convert_latex_to_unicode()` function (lines 5057-5165)
  4. Applied conversion to all generated content before yielding

**LaTeX to Unicode Conversion Examples**:
| LaTeX | Unicode |
|-------|---------|
| `\( G = (V, E) \)` | `G = (V, E)` |
| `\alpha, \beta, \gamma` | `α, β, γ` |
| `\sum, \int, \partial` | `∑, ∫, ∂` |
| `\langle, \rangle` | `⟨, ⟩` |
| `\rightarrow, \Rightarrow` | `→, ⇒` |

### 5.3 Remaining Issues

#### Issue 5: No Math Accessibility
- **Severity**: 🟡 Low
- **Status**: ⏳ Pending
- **Problem**: No aria-labels or alt text for math content
- **Impact**: Screen readers may not handle math correctly
- **Fix**: Add MathML or aria-labels for accessibility (future improvement)

---

## 6. PDF Troubleshooting Guide

### Issue: Math symbols appear as boxes or incorrect characters in PDF

**Cause**: Fonts not properly embedded in the PDF

**Solutions**:

#### Option 1: Use the PDF Export Button (Recommended)
Click the green **"📄 PDF"** button which:
- Preloads all math fonts before printing
- Uses `font-display: block` to ensure fonts load
- Waits for `document.fonts.ready` before opening print dialog
- Embeds font URLs directly in the HTML

#### Option 2: Wait Longer Before Saving as PDF
When using standard Print:
1. Open print dialog (Ctrl+P / Cmd+P)
2. Wait 3-5 seconds for fonts to load
3. Then select "Save as PDF"

#### Option 3: Use a Different PDF Generator
| Method | Font Embedding | Recommendation |
|--------|---------------|----------------|
| Chrome "Save as PDF" | ✅ Good | Recommended |
| Firefox "Save as PDF" | ✅ Good | Recommended |
| Safari "Export as PDF" | ⚠️ Variable | Wait for fonts |
| Microsoft Print to PDF | ❌ Poor | Not recommended |
| Adobe PDF Printer | ✅ Good | If available |

#### Option 4: Print to Physical Printer First
If PDF generators don't work:
1. Print to a physical printer (fonts handled by OS)
2. Scan the printed page back to PDF

### Issue: KaTeX math not rendering in PDF

**Cause**: JavaScript not executed during PDF generation

**Solution**:
- Use the **"📄 PDF"** button which waits for KaTeX to render before showing content
- Or manually wait for math to render in browser before printing

### Issue: Large file size in PDF

**Cause**: Embedded font files are large

**Solutions**:
1. Use subset fonts (already done - Unicode range limited to math symbols)
2. Print only the pages you need
3. Use PDF compression tools after generation

---

## 7. Recommendations

### 7.1 Implementation Reference

The following shows the key implementation patterns used:

```typescript
// In frontend/src/components/tabs/QueryTab.ts

// After streaming content update (around line 723)
case 'complete':
  if (event.content) {
    accumulatedContent = event.content;
    lastAnswerText = accumulatedContent;
    
    // Format and display final content
    answerText!.innerHTML = formatQueryResponse(accumulatedContent);
    
    // ADD: Render any LaTeX math (fallback for Unicode approach)
    renderMathInElement(answerText!);
    
    // ... rest of code ...
  }
  break;
```

### 7.2 Completed Improvements ✅

The following improvements have been implemented:

1. ✅ **Math Font Support**: Noto Sans Math added to both display and print
2. ✅ **Unicode Math CSS Class**: `.unicode-math` class with proper font stack
3. ✅ **Auto-detect Math Content**: Automatic wrapping of math-heavy lines
4. ✅ **PDF Export Function**: Dedicated `exportToPDF()` with font preloading
5. ✅ **Font Embedding**: `@font-face` with CDN URLs for PDF generation

### 7.3 Long-Term Improvements (Future)

1. **Consider MathJax as Alternative**: Better Unicode math support than KaTeX
2. **Add MathML Output**: For better accessibility and semantics
3. **Server-Side Math Rendering**: Pre-render math to SVG for consistency
4. **Web Font Subsetting**: Self-host only required glyph ranges

---

## 8. Testing Checklist

### Display Tests
- [ ] Unicode symbols render: |ψ⟩, α, β, ∑, ∫, ∂, ∞
- [ ] Bra-ket notation displays: ⟨ψ|φ⟩, |0⟩, |1⟩
- [ ] Greek letters display: α β γ δ ε θ λ μ σ φ ω
- [ ] Mathematical operators: ± × ÷ √ ≈ ≠ ≤ ≥
- [ ] Complex equations display correctly
- [ ] LaTeX fallback renders if present

### Print Tests  
- [ ] Math symbols print correctly
- [ ] Equations don't break across lines awkwardly
- [ ] Font embedding works for PDF export
- [ ] Black and white printing is readable

### Query Mode Tests
- [ ] Quick mode: Math displays correctly
- [ ] Balanced mode: Math displays correctly
- [ ] Comprehensive mode: Math displays correctly
- [ ] Ultra-Deep mode: Math displays correctly

---

## 8. Code Locations Summary

### Backend

| Component | File | Line(s) | Purpose |
|-----------|------|---------|---------|
| Unicode Math Prompt | `backend/pgvector_api.py` | 1834, 1860 | Instruct LLM to use Unicode math |
| **LaTeX Conversion Function** | `backend/pgvector_api.py` | **5057-5165** | **NEW: `convert_latex_to_unicode()`** |
| **Streaming Prompts (Fixed)** | `backend/pgvector_api.py` | **5120, 5181, 5225** | **NEW: Unicode math instructions** |
| Content Conversion | `backend/pgvector_api.py` | 5267, 5332, 5378 | Apply LaTeX→Unicode to all content |

### Frontend Display

| Component | File | Line(s) | Purpose |
|-----------|------|---------|---------|
| KaTeX Include | `frontend/src/components/tabs/QueryTab.ts` | 1194-1196 | Load KaTeX library from CDN |
| KaTeX Config | `frontend/src/components/tabs/QueryTab.ts` | 1044-1073 | Rendering function definition |
| **KaTeX Invocation** | `frontend/src/components/tabs/QueryTab.ts` | **799** | **FIXED: Now called after display** |
| Math Font (Display) | `frontend/src/components/tabs/QueryTab.ts` | 1279 | Noto Sans Math in font stack |
| Unicode Math Class | `frontend/src/components/tabs/QueryTab.ts` | 1284 | CSS class for math styling |
| Math Auto-Detection | `frontend/src/components/tabs/QueryTab.ts` | 1094-1108 | Wrap math content in unicode-math span |
| Math Spacing Fix | `frontend/src/components/tabs/QueryTab.ts` | 1078-1081 | Bra-ket notation spacing |
| Math CSS | `frontend/src/components/tabs/QueryTab.ts` | 1436-1465 | KaTeX styling |

### Frontend Print

| Component | File | Line(s) | Purpose |
|-----------|------|---------|---------|
| **PDF Export Function** | `frontend/src/components/tabs/QueryTab.ts` | **605-800** | **NEW: Font preloading + PDF generation** |
| PDF Button | `frontend/src/components/tabs/QueryTab.ts` | 1621 | Green "📄 PDF" button |
| Print KaTeX Include | `frontend/src/components/tabs/QueryTab.ts` | 189-192 | KaTeX for print window |
| Print Math Font | `frontend/src/components/tabs/QueryTab.ts` | 195 | Noto Sans Math for print |
| Print Math CSS | `frontend/src/components/tabs/QueryTab.ts` | 367-387 | Print-specific math styling |
| Print Math Render | `frontend/src/components/tabs/QueryTab.ts` | 489-514 | KaTeX init on print page load |
| Print Function | `frontend/src/components/tabs/QueryTab.ts` | 40-160 | Main print handler |

---

## 9. Conclusion

### Current State (After Fixes)
- ✅ Backend correctly generates Unicode math
- ✅ Frontend display with Noto Sans Math font support
- ✅ KaTeX rendering properly invoked for LaTeX fallback
- ✅ Print handling with full math support (KaTeX + fonts + CSS)

### Fixes Applied
1. **✅ COMPLETED**: Fixed KaTeX rendering call in display
2. **✅ COMPLETED**: Added Noto Sans Math font for Unicode symbols
3. **✅ COMPLETED**: Added auto-detection of math content
4. **✅ COMPLETED**: Added KaTeX to print template
5. **✅ COMPLETED**: Added print-specific CSS for math formatting
6. **✅ COMPLETED**: Added page break protection for equations
7. **✅ COMPLETED**: Added LaTeX to Unicode conversion function
8. **✅ COMPLETED**: Added Unicode math instructions to all prompts

### Remaining Work
- **⏳ PENDING**: Math accessibility (aria-labels/MathML) - Low priority

---

*End of Review - All critical and medium issues resolved*
