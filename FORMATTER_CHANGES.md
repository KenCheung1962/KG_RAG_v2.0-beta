# Query Output Formatter Changes

## Summary
- Fixed section numbering to match target format from `1Samel-7*.pdf`
- Added automatic translation of "Executive Summary" → "摘要" for Traditional Chinese content

## Format Structure

### Target Format (from 1Samel-7*.pdf)
```
撒母耳記上之屬靈教訓深度分析    <- Title (unnumbered, centered)

摘要                            <- Executive Summary (unnumbered, italic)
[content]

1. 順服與呼召的屬靈原則          <- Main section 1

1.1 撒母耳的蒙召與順服典范      <- Subsection 1.1

1.2 屬靈領袖的品格與使命        <- Subsection 1.2

2. 悖逆與管教的屬靈定律          <- Main section 2
```

## Auto-Translation Feature

When Traditional Chinese is detected in the content, "Executive Summary" is automatically translated to "摘要".

### Traditional Chinese Detection
Uses common Traditional/Simplified character pairs:
- 記/记, 體/体, 歷/历, 興/兴, 員/员, 門/门, 車/车, etc.

### Translation Rules
| Original | When Traditional Chinese Detected |
|----------|-----------------------------------|
| Executive Summary | 摘要 |
| Summary | 摘要 |

## Key Changes

### Section Numbering
1. First heading = Document Title (unnumbered)
2. Second heading = Check if summary/intro
   - If yes → Unnumbered intro section (auto-translated if Traditional Chinese)
   - If no → Main section 1
3. Subsequent headings = Main sections 1, 2, 3... and subsections 1.1, 1.2...

### Files Modified
- `QueryTab.ts` - Display formatter and print function
- `QueryFileTab.ts` - Print function

### New Helper Function
```typescript
function containsTraditionalChinese(text: string): boolean
```

### CSS Classes
```css
.section-intro         /* Unnumbered intro (Executive Summary/摘要) */
.print-section-intro   /* Print version of intro section */
```

## Build Status
✅ Frontend builds successfully
