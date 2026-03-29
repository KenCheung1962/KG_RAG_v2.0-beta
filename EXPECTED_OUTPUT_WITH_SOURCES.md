# Expected Output With Sources Section Preserved

## Output Structure:

```
[Main Content with formatted headings, citations, etc.]

📚 References
1. Novel low-temperature and high-flux hydrogen plasma source...
2. Novel low-temperature and high-flux hydrogen plasma source...
3. High Performance Next Generation EUV Lithography Light Source.txt
4. RAG LLMs are Not Safer - A Safety Analysis...

🔍 Sources (Verification)
1. High Performance Next Generation EUV Lithography Light Source.txt
2. RAG LLMs are Not Safer - A Safety Analysis...
```

---

## Visual Representation:

### Main Content Section
<query-h2 class="query-h2">Executive Summary</query-h2>

Extreme Ultraviolet (EUV) lithography is a critical technology...
The provided sources focus on two key aspects... <span class="citation-ref">[1]</span>, <span class="citation-ref">[2]</span>,
and the performance characteristics... <span class="citation-ref">[3]</span>.

<query-h2 class="query-h2">The Role of EUV Lithography...</query-h2>

[More content with proper citations...]

---

### References Section (Primary - Clean & Formatted)
<query-h2 class="query-h2 references-header">📚 References</query-h2>

<div class="reference-item">
  <span class="ref-number">1.</span> 
  Novel low-temperature and high-flux hydrogen plasma source for extreme-ultraviolet lithography applications.txt
</div>
<div class="reference-item">
  <span class="ref-number">2.</span> 
  Novel low-temperature and high-flux hydrogen plasma source for extreme-ultraviolet lithography applications.txt
</div>
<div class="reference-item">
  <span class="ref-number">3.</span> 
  High Performance Next Generation EUV Lithography Light Source.txt
</div>
<div class="reference-item">
  <span class="ref-number">4.</span> 
  RAG LLMs are Not Safer - A Safety Analysis of Retrieval-Augmented Generation for Large Language Models.txt
</div>

---

### Sources Section (Verification - Preserved from Backend)
<query-h3 class="query-h3 sources-header">🔍 Sources (Verification)</query-h3>

<div class="sources-verification">
  <div class="source-item-verify">1. High Performance Next Generation EUV Lithography Light Source.txt</div>
  <div class="source-item-verify">2. RAG LLMs are Not Safer - A Safety Analysis...</div>
</div>

---

## CSS Styling Differences:

| Feature | References Section | Sources Section |
|---------|-------------------|-----------------|
| **Header** | "📚 References" (h2) | "🔍 Sources (Verification)" (h3) |
| **Color Theme** | Green (#4CAF50) | Orange (#ff9800) |
| **Background** | Light green tint | Light orange tint with dashed border |
| **Font** | Regular | Monospace (Courier) |
| **Border** | Solid left border | Dashed box border |
| **Purpose** | User-facing citations | Developer verification |

---

## Key Changes from Original:

| Original Issue | Fixed Output |
|----------------|--------------|
| `##Executive Summary` (no space) | `<query-h2>Executive Summary</query-h2>` |
| `Source 1, Source 2` | <span class="citation-ref">[1]</span>, <span class="citation-ref">[2]</span> |
| `the literature` | <span class="citation-ref">[3]</span> (mapped to correct file) |
| `##References8791` (merged) | Removed - replaced with clean References header |
| Multiple references sections | Single References + preserved Sources at end |
| `Sources:filename.txt` (concatenated) | Properly formatted with line breaks |
