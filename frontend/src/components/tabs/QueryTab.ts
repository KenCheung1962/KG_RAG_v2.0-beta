/**
 * Query Tab Component
 */

import { sendQuery } from '@/api';
import type { QueryMode } from '@/config';
import { getElement, setVisible, setDisabled } from '@/utils/dom';
import { escapeHtml } from '@/utils/helpers';
import {
  setActiveQueryController, setIsQuerying, cancelActiveQuery, isQuerying
} from '@/stores/appStore';

// Store last query and answer for printing
let lastQueryText = '';
let lastAnswerText = '';
let lastSources: string[] = [];

/**
 * Check if text contains Traditional Chinese characters
 * Uses common Traditional/Simplified Chinese character differences
 */
function containsTraditionalChinese(text: string): boolean {
  // Common Traditional Chinese characters that differ from Simplified
  const traditionalChars = /[記體歷興員門車龍馬魚鳥學長東車國會來時個們說開發問過這種處從當與麼灣]/;
  
  // Count Traditional-specific characters
  const traditionalMatches = text.match(/[記體歷興員門車龍馬魚鳥學長東國會來時個們說開發問過這種處從當與麼灣]/g);
  const simplifiedMatches = text.match(/[记体历兴员门车龙马鱼鸟学长东国会来时个们说开发问过这种处从当与]/g);
  
  // If we have Traditional-specific chars, and more than or equal to Simplified-specific chars
  const traditionalCount = traditionalMatches ? traditionalMatches.length : 0;
  const simplifiedCount = simplifiedMatches ? simplifiedMatches.length : 0;
  
  return traditionalCount > 0 && traditionalCount >= simplifiedCount;
}

/**
 * Print the answer
 */
function printAnswer(event?: Event): void {
  // Prevent any default behavior that might clear the form
  event?.preventDefault();
  event?.stopPropagation();
  
  if (!lastAnswerText) {
    alert('No answer to print. Please run a query first.');
    return;
  }

  // Process text for clean academic format
  let processedText = lastAnswerText;
  
  // Convert backend HTML tags to markdown headers
  // Use [\s\S] instead of . to match newlines inside tags
  processedText = processedText.replace(/<query-h1>([\s\S]*?)<\/query-h1>/gi, '# $1');
  processedText = processedText.replace(/<query-h2>([\s\S]*?)<\/query-h2>/gi, '## $1');
  processedText = processedText.replace(/<query-h3>([\s\S]*?)<\/query-h3>/gi, '### $1');
  processedText = processedText.replace(/<query-h4>([\s\S]*?)<\/query-h4>/gi, '#### $1');
  
  // KEEP citations in print version - convert citation spans to bracket format
  processedText = processedText.replace(/<span[^>]*citation-ref[^>]*>\[(\d+)\]<\/span>/gi, '[$1]');
  
  // Remove old "Source X" format if present (but keep bracket citations)
  processedText = processedText.replace(/\(\s*Source\s+\d+(?:\s*,\s*Source\s+\d+)*\s*\)/gi, '');
  processedText = processedText.replace(/Source\s+\d+(?:\s*,\s*Source\s+\d+)*/gi, '');
  
  // Remove HTML paragraph tags but preserve reference structure
  processedText = processedText.replace(/<\/?p>/gi, '');
  
  // Convert reference items to a printable format before removing divs
  // Handle format: <div class="reference-item"><span class="ref-number">1.</span> <span class="ref-source">Name</span></div>
  processedText = processedText.replace(/<div[^>]*class="reference-item"[^>]*>\s*<span[^>]*class="ref-number"[^>]*>(\d+\.?)<\/span>\s*(?:<span[^>]*class="ref-source"[^>]*>)?([^<]+)(?:<\/span>)?\s*<\/div>/gi, '[$1] $2<br>');
  
  // Also handle simple format: [1] Source name (already converted)
  // Remove remaining HTML tags but keep citations
  processedText = processedText.replace(/<\/?(div|span)[^>]*>/gi, '');
  
  // NOTE: We no longer extract/remove the References section separately.
  // This was causing truncation issues. The references are part of the content
  // and will be formatted naturally with the rest of the text.
  // Both screen and print now show the FULL content without truncation.
  
  // Format markdown-style headings and bold text
  let formattedAnswer = processedText
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Convert **text** to bold
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  
  // Process headings line by line for proper numbering
  const lines = formattedAnswer.split('\n');
  const processedLines: string[] = [];
  
  let mainSectionNum = 0;
  let subSectionNum = 0;
  let isFirstHeading = true;
  let isSecondHeading = false;
  
  for (const line of lines) {
    const h1Match = line.match(/^#\s+(.+)$/);
    const h2Match = line.match(/^##\s+(.+)$/);
    const h3Match = line.match(/^###\s+(.+)$/);
    
    if (h1Match || h2Match || h3Match) {
      let content = (h1Match || h2Match || h3Match)![1].trim();
      const level = h1Match ? 1 : h2Match ? 2 : 3;
      
      // STEP A: Remove standalone Chinese numbering like "一、", "二、" at the very start
      content = content.replace(/^[一二三四五六七八九十]+[、.．]\s*/, '');
      
      // STEP B: Remove redundant combined patterns like "1. 一、" -> keep only content after "一、"
      content = content.replace(/^\d+\.\s*[一二三四五六七八九十]+[、.．]\s*/, '');
      
      // STEP C: Remove patterns like "1. 1.1 " or "1. 1.1" (frontend number + backend subsection)
      content = content.replace(/^\d+\.\s*\d+\.\d+\s*/, '');
      
      // STEP D: Remove standalone subsection numbers like "1.1 ", "1.2."
      content = content.replace(/^\d+\.\d+\.?\s*/, '');
      
      // STEP E: Remove standalone section numbers like "1. ", "2."
      content = content.replace(/^\d+\.\s*/, '');
      
      // STEP F: Clean up any remaining standalone numbers at start
      content = content.replace(/^\d+\s+/, '');
      
      // First heading = Document Title (unnumbered)
      if (isFirstHeading) {
        isFirstHeading = false;
        isSecondHeading = true;
        processedLines.push(`<div class="print-document-title">${content}</div>`);
        continue;
      }
      
      // Second heading = Check if it's a summary/intro section
      if (isSecondHeading) {
        isSecondHeading = false;
        const isSummarySection = /executive\s+summary|summary|摘要|引言|前言|概述|導言/i.test(content);
        if (isSummarySection) {
          // Auto-translate "Executive Summary" to "摘要" if Traditional Chinese detected
          let displayContent = content;
          if (/executive\s+summary/i.test(content) && containsTraditionalChinese(processedText)) {
            displayContent = '摘要';
          }
          processedLines.push(`<div class="print-section-intro">${displayContent}</div>`);
          continue;
        }
        // Not a summary, treat as first main section
        mainSectionNum = 1;
        processedLines.push(`<div class="print-section-title">${mainSectionNum}. ${content}</div>`);
        continue;
      }
      
      // Special handling for References section (unnumbered)
      if (/^references?$|參考文獻|参考文献/i.test(content)) {
        processedLines.push(`<div class="print-section-references">${content}</div>`);
        continue;
      }
      
      // Subsequent headings
      if (level <= 2) {
        // H1 or H2 = main section
        mainSectionNum++;
        subSectionNum = 0;
        processedLines.push(`<div class="print-section-title">${mainSectionNum}. ${content}</div>`);
      } else {
        // H3 = subsection
        subSectionNum++;
        processedLines.push(`<div class="print-section-heading">${mainSectionNum}.${subSectionNum} ${content}</div>`);
      }
    } else {
      processedLines.push(line);
    }
  }
  
  formattedAnswer = processedLines.join('\n');
  
  // Convert newlines to <br>
  formattedAnswer = formattedAnswer.replace(/\n/g, '<br>');
  
  // Note: References section is already included in processedText

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Query Result</title>
  <style>
    @page {
      margin: 2.0cm 1.2cm;
    }
    @media print {
      body { 
        font-family: Georgia, 'Times New Roman', serif;
        font-size: 11pt;
        line-height: 1.6;
        margin: 0;
        color: #000;
      }
      h1 { font-size: 16pt; border-bottom: 2px solid #333; padding-bottom: 0.2cm; margin-top: 0.5cm; }
      h2 { font-size: 14pt; margin-top: 0.1cm; color: #333; }
      h3 { font-size: 12pt; margin-top: 0cm; color: #555; }
      .no-print { display: none; }
      .h1-bold { 
        font-size: 18pt; 
        font-weight: bold; 
        margin-top: 0.4cm; 
        margin-bottom: 0.15cm;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 0.1cm;
      }
      .h2-bold { 
        font-size: 15pt; 
        font-weight: bold; 
        margin-top: 0.2cm; 
        margin-bottom: 0.1cm;
        color: #2E7D32;
      }
      .h3-bold { 
        font-size: 13pt; 
        font-weight: bold; 
        margin-top: 0.15cm; 
        margin-bottom: 0.05cm;
        color: #333;
      }
      .references-section {
        background: rgba(76, 175, 80, 0.15);
        border: 1px solid #4CAF50;
        border-radius: 4px;
        padding: 8px 12px;
        margin-top: 0.2cm;
        color: #2E7D32;
        font-weight: bold;
      }
      .sources-section {
        background: rgba(255, 152, 0, 0.15);
        border: 1px dashed #FF9800;
        border-radius: 4px;
        padding: 8px 12px;
        margin-top: 0.15cm;
        color: #E65100;
        font-weight: bold;
        font-family: monospace;
      }
      .conclusion-section {
        background: rgba(156, 39, 176, 0.1);
        border-left: 3px solid #9C27B0;
        padding: 8px 12px;
        margin-top: 0.15cm;
        font-style: italic;
      }
      strong { font-weight: bold; }
      /* New HTML tag styles for standard format */
      query-h1 {
        display: block;
        font-size: 18pt;
        font-weight: bold;
        margin-top: 0.4cm;
        margin-bottom: 0.15cm;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 0.1cm;
      }
      query-h2 {
        display: block;
        font-size: 15pt;
        font-weight: bold;
        margin-top: 0.2cm;
        margin-bottom: 0.1cm;
        color: #2E7D32;
      }
      query-h3 {
        display: block;
        font-size: 13pt;
        font-weight: bold;
        margin-top: 0.15cm;
        margin-bottom: 0.05cm;
        color: #333;
      }
      .citation-ref {
        color: #1976D2;
        font-weight: bold;
      }
      .reference-item {
        margin-bottom: 0.3cm;
      }
      .ref-number {
        font-weight: bold;
        margin-right: 0.3cm;
      }
      /* Clean print format styles */
      .print-document-title {
        font-size: 16pt;
        font-weight: bold;
        margin-top: 0;
        margin-bottom: 0.4cm;
        color: #000;
        border-bottom: 2px solid #000;
        padding-bottom: 0.15cm;
        text-align: center;
      }
      .print-section-intro {
        font-size: 12pt;
        font-weight: bold;
        margin-top: 0.3cm;
        margin-bottom: 0.15cm;
        color: #333;
        font-style: italic;
      }
      .print-section-references {
        font-size: 13pt;
        font-weight: bold;
        margin-top: 0.5cm;
        margin-bottom: 0.2cm;
        color: #2e7d32;
        border-top: 1px solid #2e7d32;
        padding-top: 0.2cm;
      }
      .print-section-title {
        font-size: 13pt;
        font-weight: bold;
        margin-top: 0.4cm;
        margin-bottom: 0.15cm;
        color: #000;
        border-bottom: 1px solid #333;
        padding-bottom: 0.1cm;
      }
      .print-section-heading {
        font-size: 12pt;
        font-weight: bold;
        margin-top: 0.3cm;
        margin-bottom: 0.15cm;
        color: #333;
      }
      .print-section-subheading {
        font-size: 11pt;
        font-weight: bold;
        margin-top: 0.2cm;
        margin-bottom: 0.1cm;
        color: #555;
      }
      .print-references-section {
        margin-top: 0.8cm;
        padding-top: 0.3cm;
        border-top: 1px solid #333;
      }
      .print-references-header {
        font-size: 13pt;
        font-weight: bold;
        margin-bottom: 0.2cm;
        color: #000;
      }
      .print-references-list {
        padding-left: 0.3cm;
      }
      .print-reference-item {
        margin-bottom: 0.15cm;
        font-size: 10pt;
      }
      .print-ref-number {
        font-weight: bold;
        margin-right: 0.2cm;
      }
    }
    @media screen {
      body { 
        font-family: Georgia, 'Times New Roman', serif;
        max-width: 800px;
        margin: 2cm auto;
        padding: 1cm;
        line-height: 1.6;
      }
      .print-button {
        display: block;
        margin: 1cm auto;
        padding: 10px 30px;
        font-size: 14pt;
        background: #4CAF50;
        color: white;
        border: none;
        border-radius: 4px;
        cursor: pointer;
      }
      .print-button:hover { background: #45a049; }
      .h1-bold { 
        font-size: 20pt; 
        font-weight: bold; 
        margin-top: 20px; 
        margin-bottom: 10px;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 5px;
      }
      .h2-bold { 
        font-size: 16pt; 
        font-weight: bold; 
        margin-top: 15px; 
        margin-bottom: 8px;
        color: #2E7D32;
      }
      .h3-bold { 
        font-size: 14pt; 
        font-weight: bold; 
        margin-top: 12px; 
        margin-bottom: 6px;
        color: #333;
      }
      .references-section {
        background: rgba(76, 175, 80, 0.15);
        border: 1px solid #4CAF50;
        border-radius: 4px;
        padding: 10px 14px;
        margin-top: 16px;
        color: #2E7D32;
        font-weight: bold;
      }
      .sources-section {
        background: rgba(255, 152, 0, 0.15);
        border: 1px dashed #FF9800;
        border-radius: 4px;
        padding: 10px 14px;
        margin-top: 12px;
        color: #E65100;
        font-weight: bold;
        font-family: monospace;
      }
      .conclusion-section {
        background: rgba(156, 39, 176, 0.1);
        border-left: 3px solid #9C27B0;
        padding: 10px 14px;
        margin-top: 12px;
        font-style: italic;
      }
      strong { font-weight: bold; }
      /* New HTML tag styles for standard format - screen view */
      query-h1 {
        display: block;
        font-size: 20pt;
        font-weight: bold;
        margin-top: 20px;
        margin-bottom: 10px;
        color: #008B8B;
        border-bottom: 2px solid #008B8B;
        padding-bottom: 5px;
      }
      query-h2 {
        display: block;
        font-size: 16pt;
        font-weight: bold;
        margin-top: 15px;
        margin-bottom: 8px;
        color: #2E7D32;
      }
      query-h3 {
        display: block;
        font-size: 14pt;
        font-weight: bold;
        margin-top: 12px;
        margin-bottom: 6px;
        color: #333;
      }
      .citation-ref {
        color: #1976D2;
        font-weight: bold;
      }
      .reference-item {
        margin-bottom: 8px;
      }
      .ref-number {
        font-weight: bold;
        margin-right: 8px;
      }
    }
  </style>
</head>
<body>
  <div class="answer">${formattedAnswer}</div>
</body>
</html>`;

  // Use Blob URL for more reliable rendering
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const printWindow = window.open(url, '_blank');
  
  if (!printWindow) {
    alert('Please allow popups to print the answer.');
    URL.revokeObjectURL(url);
    return;
  }
}

/**
 * Initialize query tab
 */
export function initQueryTab(): void {
  getElement('runQueryBtn')?.addEventListener('click', handleRunQuery);
  getElement('printQueryBtn')?.addEventListener('click', (e) => printAnswer(e));
  
  // Clear previous answer when user starts typing a new query
  getElement('queryText')?.addEventListener('input', () => {
    const printBtn = getElement('printQueryBtn');
    if (printBtn) printBtn.style.display = 'none';
    // Don't clear the answer text - let user see it until new query is submitted
  });
  
  // Test query buttons
  getElement('testQueryCompanies')?.addEventListener('click', () => setTestQuery('What companies are mentioned?'));
  getElement('testQueryRelations')?.addEventListener('click', () => setTestQuery('What relationships exist?'));
  getElement('testQueryOverview')?.addEventListener('click', () => setTestQuery('Give me an overview'));
}

/**
 * Set test query text
 */
function setTestQuery(query: string): void {
  const textarea = getElement<HTMLTextAreaElement>('queryText');
  if (textarea) textarea.value = query;
  handleRunQuery();
}

/**
 * Get selected query mode
 */
function getQueryMode(): QueryMode {
  const radio = document.querySelector('input[name="queryMode"]:checked') as HTMLInputElement;
  return (radio?.value as QueryMode) || 'smart';
}

/**
 * Get selected query detail level
 */
function getQueryDetail(): { 
  top_k: number; 
  ultra_comprehensive: boolean;
  detailed: boolean;
  label: string;
} {
  const radio = document.querySelector('input[name="queryDetail"]:checked') as HTMLInputElement;
  const level = radio?.value || 'balanced';
  
  switch (level) {
    case 'quick':
      return { 
        top_k: 10, 
        ultra_comprehensive: false,
        detailed: false,
        label: 'Quick'
      };
    case 'ultra':
      return {
        top_k: 40,
        ultra_comprehensive: true,
        detailed: true,
        label: 'Ultra Deep'
      };
    case 'comprehensive':
      return { 
        top_k: 30, 
        ultra_comprehensive: false,
        detailed: true,
        label: 'Comprehensive'
      };
    case 'balanced':
    default:
      return { 
        top_k: 20, 
        ultra_comprehensive: false,
        detailed: false,
        label: 'Balanced'
      };
  }
}

/**
 * Handle run query
 */
async function handleRunQuery(): Promise<void> {
  const queryText = getElement<HTMLTextAreaElement>('queryText')?.value.trim();
  
  if (!queryText) {
    alert('Please enter a question');
    return;
  }
  
  // Store query for printing
  lastQueryText = queryText;
  
  // Cancel any existing query
  if (isQuerying()) {
    cancelActiveQuery();
  }
  
  const mode = getQueryMode();
  const detail = getQueryDetail();
  const answerText = getElement('answerText');
  const sourcesText = getElement('sourcesText');
  const runBtn = getElement('runQueryBtn');
  const printBtn = getElement('printQueryBtn');
  
  setIsQuerying(true);
  setDisabled('runQueryBtn', true);
  if (printBtn) printBtn.style.display = 'none';
  
  // Update button text based on mode
  const isUltra = detail.ultra_comprehensive;
  const isComprehensive = detail.detailed && !isUltra;
  const estimatedTime = isUltra ? '10-15 min' : (isComprehensive ? '8-10 min' : '3-5 min');
  if (runBtn) runBtn.textContent = `⏳ ${detail.label} Mode (${estimatedTime})...`;
  
  setVisible('queryResult', true);
  
  // Build mode-specific message (EXACT format as specified)
  let modeMessage = '';
  if (isUltra) {
    // Ultra Deep Mode: 40 chunks, 3000+ words
    modeMessage = `Retrieving 40 chunks + Generating ultra-extensive (3000+ words) answer...`;
  } else if (isComprehensive) {
    // Comprehensive Mode: 30 chunks, 2000+ words
    modeMessage = `Retrieving 30 chunks + Generating comprehensive (2000+ words) answer...`;
  } else if (detail.top_k === 10) {
    // Quick Mode: 10 chunks, ~1000 words
    modeMessage = `Retrieving 10 chunks + ~ 1000 words Generating standard answer...`;
  } else {
    // Balanced Mode: 20 chunks, ~1500 words
    modeMessage = `Retrieving 20 chunks + ~1500 words Generating standard answer...`;
  }
  
  answerText!.innerHTML = `<span class="spinner"></span> <strong>${detail.label} Mode</strong><br>${modeMessage}<br>Estimated time: ${estimatedTime}<br><small>Please wait, do not close or refresh the page</small>`;
  sourcesText!.textContent = '';
  
  const controller = new AbortController();
  setActiveQueryController(controller);
  
  // Set timeout based on mode - MUST match client.ts timeouts
  let timeoutMs: number;
  if (isUltra) {
    timeoutMs = 900000;  // 15 min for ultra (multi-step: outline + 6+ sections + conclusion)
  } else if (detail.detailed) {
    timeoutMs = 600000;  // 10 min for comprehensive (multi-step: outline + 5 sections + conclusion)
  } else {
    timeoutMs = 300000;  // 5 min for quick/balanced (single-pass)
  }
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    const result = await sendQuery({ 
      message: queryText, 
      mode,
      top_k: detail.top_k,
      ultra_comprehensive: detail.ultra_comprehensive,
      detailed: detail.detailed
    }, controller.signal);
    clearTimeout(timeoutId);
    
    const responseText = result.response || result.answer || JSON.stringify(result, null, 2);
    
    // Debug: log full result to see what fields are returned
    console.log('[Query] Full result:', result);
    console.log('[Query] Result keys:', Object.keys(result));
    
    // Store sources and build answer with references for printing
    // Check multiple possible source field names
    const sources = result.sources || result.source_documents || (result as Record<string, unknown>).source || (result as Record<string, unknown>).chunks;
    console.log('[Query] Raw sources:', sources);
    console.log('[Query] sources type:', typeof sources);
    console.log('[Query] sources isArray:', Array.isArray(sources));
    
    // TEMPORARY: If backend returns number instead of array, log the issue
    if (typeof sources === 'number') {
      console.warn('[Query] Backend returned source COUNT instead of source filenames. References cannot be displayed.');
    }
    if (Array.isArray(sources)) {
      // Handle both string array and object array
      lastSources = sources.map((s: unknown): string => {
        if (typeof s === 'string') return s;
        // If source is an object with filename or doc_id, extract it
        if (s && typeof s === 'object') {
          return ((s as Record<string, unknown>).filename as string) || 
                 ((s as Record<string, unknown>).doc_id as string) || 
                 ((s as Record<string, unknown>).name as string) || 
                 JSON.stringify(s);
        }
        return String(s);
      });
    } else {
      lastSources = [];
    }
    console.log('[Query] Processed sources:', lastSources);
    
    // Extract which sources are actually CITED in the response text
    const citedSourceNumbers = new Set<number>();
    const sourceCitations = responseText.match(/Source\s+(\d+)/gi);
    if (sourceCitations) {
      sourceCitations.forEach(citation => {
        const match = citation.match(/\d+/);
        if (match) {
          citedSourceNumbers.add(parseInt(match[0], 10));
        }
      });
    }
    console.log('[Query] Sources cited in text:', Array.from(citedSourceNumbers));
    
    // Build answer with reference section for print output
    // ONLY include references that are actually CITED in the text
    let answerWithRefs = responseText;
    if (citedSourceNumbers.size > 0 && lastSources.length > 0) {
      // Filter to only cited sources
      const citedSources = Array.from(citedSourceNumbers)
        .sort((a, b) => a - b)
        .map(num => lastSources[num - 1])  // Source 1 = index 0
        .filter(src => src !== undefined);  // Remove undefined
      
      if (citedSources.length > 0) {
        answerWithRefs += '\n\n\n## References\n\n';
        citedSources.forEach((src, idx) => {
          answerWithRefs += `${idx + 1}. ${src}\n`;
        });
      }
    }
    // Note removed - response shown as-is from backend
    lastAnswerText = answerWithRefs;
    
    if (printBtn) printBtn.style.display = 'inline-block';
    
    // Check if LLM timed out
    if (responseText.startsWith('Found') && responseText.includes('relevant chunks')) {
      renderTimeoutResponse(responseText, answerText!);
    } else {
      // Format the response with improved styling - include ONLY cited references
      let displayText = responseText;
      if (citedSourceNumbers.size > 0 && lastSources.length > 0) {
        // Filter to only cited sources
        const citedSources = Array.from(citedSourceNumbers)
          .sort((a, b) => a - b)
          .map(num => lastSources[num - 1])
          .filter(src => src !== undefined);
        
        if (citedSources.length > 0) {
          displayText += '\n\n\n## References\n\n' + citedSources.map((src, idx) => `${idx + 1}. ${src}`).join('\n');
        }
      }
      // Note removed - response shown as-is from backend
      answerText!.innerHTML = formatQueryResponse(displayText);
      
      // Render math formulas using KaTeX
      setTimeout(() => renderMathInElement(answerText!), 100);
    }
    
    // Show sources with dual sections (📚 References + 🔍 Sources for Verification)
    const rawSources = result.sources || result.source_documents;
    if (lastSources.length > 0) {
      // Build structured sources display with 📚 References and 🔍 Sources sections
      let sourcesHtml = '';
      
      // 📚 References section (Green) - only cited sources
      if (citedSourceNumbers.size > 0) {
        const citedSources = Array.from(citedSourceNumbers)
          .sort((a, b) => a - b)
          .map(num => lastSources[num - 1])
          .filter(src => src !== undefined);
        
        if (citedSources.length > 0) {
          sourcesHtml += `<div class="sources-section references-section">`;
          sourcesHtml += `<div class="sources-header references-header">📚 References</div>`;
          citedSources.forEach((src, idx) => {
            sourcesHtml += `<div class="source-item references-item">${idx + 1}. ${escapeHtml(src)}</div>`;
          });
          sourcesHtml += `</div>`;
        }
      }
      
      // 🔍 Sources (for Verification) section (Orange) - all sources
      sourcesHtml += `<div class="sources-section verification-section">`;
      sourcesHtml += `<div class="sources-header verification-header">🔍 Sources (for Verification)</div>`;
      lastSources.forEach((src, idx) => {
        sourcesHtml += `<div class="source-item verification-item">${idx + 1}. ${escapeHtml(src)}</div>`;
      });
      sourcesHtml += `</div>`;
      
      sourcesText!.innerHTML = sourcesHtml;
    } else if (typeof rawSources === 'number') {
      sourcesText!.innerHTML = `<div class="source-item">Found ${rawSources} sources (filenames not available - backend config issue)</div>`;
    } else {
      sourcesText!.textContent = 'No sources available';
    }
    
  } catch (error) {
    clearTimeout(timeoutId);
    handleQueryError(error, answerText!);
  } finally {
    setIsQuerying(false);
    setActiveQueryController(null);
    setDisabled('runQueryBtn', false);
    if (runBtn) runBtn.textContent = '🔍 Ask Question';
  }
}

/**
 * Format query response with clean academic styling
 * 
 * Key Features:
 * 1. Remove all inline citation markers (Source X, [X], etc.)
 * 2. Convert ## headings to simple numbered sections (1, 1.1, 1.2, etc.)
 * 3. Clean "參考文獻" (References) section at end
 * 4. "驗證來源" (Verification Sources) section for source documents
 */
export function formatQueryResponse(text: string): string {
  if (!text) return '';
  
  // Debug: Check if References section is present in input
  const hasRefs = /References?|參考文獻|参考文献/i.test(text);
  const refsIndex = text.search(/References?|參考文獻|参考文献/i);
  console.log('[formatQueryResponse] Input length:', text.length, 'Has References:', hasRefs, 'Refs position:', refsIndex);
  if (refsIndex > 0) {
    console.log('[formatQueryResponse] References preview:', text.substring(refsIndex, refsIndex + 200));
  }
  
  let cleaned = text;
  
  // ======================
  // STEP 0: Convert backend HTML tags to markdown headers
  // ======================
  // Backend uses <query-h1>, <query-h2>, <query-h3>, <query-h4> tags
  // Convert them to markdown #, ##, ###, #### for consistent processing
  // Use [\s\S] instead of . to match newlines inside tags
  cleaned = cleaned.replace(/<query-h1>([\s\S]*?)<\/query-h1>/gi, '# $1');
  cleaned = cleaned.replace(/<query-h2>([\s\S]*?)<\/query-h2>/gi, '## $1');
  cleaned = cleaned.replace(/<query-h3>([\s\S]*?)<\/query-h3>/gi, '### $1');
  cleaned = cleaned.replace(/<query-h4>([\s\S]*?)<\/query-h4>/gi, '#### $1');
  
  // ======================
  // STEP 1: Handle inline citation markers
  // ======================
  
  // Remove (Source X, Source Y) patterns - old format
  cleaned = cleaned.replace(/\(\s*Source\s+\d+(?:\s*,\s*Source\s+\d+)*\s*\)/gi, '');
  // Remove Source X, Source Y without parentheses - old format
  cleaned = cleaned.replace(/Source\s+\d+(?:\s*,\s*Source\s+\d+)*/gi, '');
  
  // KEEP academic citations [X] and <span class="citation-ref">[X]</span>
  // Convert citation spans to clean [X] format for display
  cleaned = cleaned.replace(/<span[^>]*citation-ref[^>]*>\[(\d+)\]<\/span>/gi, '[$1]');
  // Keep standalone [X] citations - these are academic citations that should be preserved
  
  // Remove HTML paragraph tags (<p> and </p>)
  cleaned = cleaned.replace(/<\/?p>/gi, '');
  
  // Convert reference-item divs to markdown format BEFORE stripping other divs
  // Pattern: <div class="reference-item"><span class="ref-number">1.</span> filename</div>
  const beforeRefItems = cleaned;
  cleaned = cleaned.replace(/<div[^>]*class="reference-item"[^>]*>\s*<span[^>]*class="ref-number"[^>]*>(\d+\.)<\/span>\s*([^<]+)<\/div>/gi, '$1 $2');
  cleaned = cleaned.replace(/<div[^>]*class="reference-item"[^>]*>\s*(\d+\.)\s*([^<]+)<\/div>/gi, '$1 $2');
  if (cleaned !== beforeRefItems) {
    console.log('[formatQueryResponse] Converted reference-item divs');
  }
  
  // Remove any other HTML tags that might appear
  cleaned = cleaned.replace(/<\/?(div|span)[^>]*>/gi, '');
  
  // Clean up "the literature" references
  cleaned = cleaned.replace(/the\s+literature/gi, '相關文獻');
  
  // ======================
  // STEP 2: Remove disclaimers and noise
  // ======================
  
  // Remove "Note on Context" / "Context Note" sections
  cleaned = cleaned.replace(/Note on Context[\s\S]*?I will answer[^.]*\./gi, '');
  cleaned = cleaned.replace(/Context Note[\s\S]*?general knowledge[^.]*\./gi, '');
  
  // Remove standalone irrelevant context explanations
  cleaned = cleaned.replace(/The provided context discusses[\s\S]*?unrelated to[\s\S]*?\./gi, '');
  cleaned = cleaned.replace(/The (?:provided |available |indexed )?context (?:does not contain|lacks|is (?:unrelated|irrelevant))[\s\S]*?\./gi, '');
  
  // Remove "I will answer based on general knowledge" statements
  cleaned = cleaned.replace(/I will answer your question based on (?:general |my )?knowledge[^.]*\./gi, '');
  cleaned = cleaned.replace(/Based on (?:general |my )?knowledge,?[^.]*\./gi, '');
  
  // Remove editor notes
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
  
  // ======================
  // STEP 3: Extract and store References section
  // ======================
  
  // NOTE: We NO LONGER remove References or Sources sections.
  // Previous logic was too aggressive and caused massive truncation.
  // Both screen display and print should show the FULL content.
  // References are already appended to the text before this function is called.
  

  
  // ======================
  // STEP 4: Convert headings to numbered sections
  // ======================
  
  const lines = cleaned.split('\n');
  
  // Track section numbering
  let mainSectionNum = 0;
  let subSectionNum = 0;
  let isFirstHeading = true;
  let isSecondHeading = false;  // Second heading starts main numbering
  
  // Process headings line by line to assign numbers
  const processedLines: string[] = [];
  
  for (const line of lines) {
    const h1Match = line.match(/^#\s+(.+)$/);
    const h2Match = line.match(/^##\s+(.+)$/);
    const h3Match = line.match(/^###\s+(.+)$/);
    const h4Match = line.match(/^####\s+(.+)$/);
    
    if (h1Match || h2Match || h3Match || h4Match) {
      let content = (h1Match || h2Match || h3Match || h4Match)![1].trim();
      const level = h1Match ? 1 : h2Match ? 2 : h3Match ? 3 : 4;
      
      // STEP A: Remove standalone Chinese numbering like "一、", "二、" at the very start
      content = content.replace(/^[一二三四五六七八九十]+[、.．]\s*/, '');
      
      // STEP B: Remove redundant combined patterns like "1. 一、" -> keep only content after "一、"
      // Pattern: number.ChineseNumber. or number.ChineseNumber (with or without space)
      content = content.replace(/^\d+\.\s*[一二三四五六七八九十]+[、.．]\s*/, '');
      
      // STEP C: Remove patterns like "1. 1.1 " or "1. 1.1" (frontend number + backend subsection)
      content = content.replace(/^\d+\.\s*\d+\.\d+\s*/, '');
      
      // STEP D: Remove standalone subsection numbers like "1.1 ", "1.2."
      content = content.replace(/^\d+\.\d+\.?\s*/, '');
      
      // STEP E: Remove standalone section numbers like "1. ", "2."
      content = content.replace(/^\d+\.\s*/, '');
      
      // STEP F: Clean up any remaining standalone numbers at start
      content = content.replace(/^\d+\s+/, '');
      
      // First heading = Document Title (unnumbered)
      if (isFirstHeading) {
        isFirstHeading = false;
        isSecondHeading = true;
        processedLines.push(`<strong class="document-title">${content}</strong>`);
        continue;
      }
      
      // Second heading = Introduction/Summary (unnumbered, like "Executive Summary")
      if (isSecondHeading) {
        isSecondHeading = false;
        // Check if this looks like a summary/intro section (Executive Summary, 摘要, 引言, etc.)
        const isSummarySection = /executive\s+summary|summary|摘要|引言|前言|概述|導言|執行摘要/i.test(content);
        if (isSummarySection) {
          // Auto-translate "Executive Summary" to "摘要" if Traditional Chinese detected
          let displayContent = content;
          if (/executive\s+summary/i.test(content) && containsTraditionalChinese(cleaned)) {
            displayContent = '摘要';
          }
          processedLines.push(`<strong class="section-intro">${displayContent}</strong>`);
          continue;
        }
        // Not a summary, treat as first main section
        mainSectionNum = 1;
        subSectionNum = 0;
        processedLines.push(`<strong class="section-title">${mainSectionNum}. ${content}</strong>`);
        continue;
      }
      
      // Special handling for References section (unnumbered)
      if (/^references?$|參考文獻|参考文献/i.test(content)) {
        processedLines.push(`<strong class="section-references">${content}</strong>`);
        continue;
      }
      
      // Determine if this is a main section or subsection based on level change
      // H2 or H3 (depending on structure) = main section
      // Deeper levels = subsections
      if (level <= 2) {
        // H1 or H2 = main section
        mainSectionNum++;
        subSectionNum = 0;
        processedLines.push(`<strong class="section-title">${mainSectionNum}. ${content}</strong>`);
      } else if (level === 3) {
        // H3 = could be main section or subsection depending on context
        if (mainSectionNum === 0) {
          // If no main section yet, this is main section 1
          mainSectionNum = 1;
          processedLines.push(`<strong class="section-title">${mainSectionNum}. ${content}</strong>`);
        } else {
          // This is a subsection
          subSectionNum++;
          processedLines.push(`<strong class="section-heading">${mainSectionNum}.${subSectionNum} ${content}</strong>`);
        }
      } else {
        // H4+ = subsection
        subSectionNum++;
        processedLines.push(`<strong class="section-heading">${mainSectionNum}.${subSectionNum} ${content}</strong>`);
      }
    } else {
      processedLines.push(line);
    }
  }
  
  cleaned = processedLines.join('\n');

  
  // ======================
  // STEP 5: Clean up formatting
  // ======================
  
  // Clean up excessive newlines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  
  // Remove standalone parentheses with instructions
  cleaned = cleaned.replace(/^\s*\([^)]+\)\s*$/gmi, '');
  
  // Fix math equation spacing
  cleaned = cleaned.replace(/([A-Za-z])(\t+|\s{2,})([|⟨⟩])/g, '$1 $3');
  cleaned = cleaned.replace(/(\))\t+|\s{2,}([|⟨⟩])/g, '$1 $2');
  cleaned = cleaned.replace(/([|⟨⟩][^|⟨⟩]*?)(\t+|\s{2,})(?=\))/g, '$1');
  cleaned = cleaned.replace(/\t+/g, ' ');
  cleaned = cleaned.replace(/\s{3,}/g, ' ');
  
  // Format bold and italic
  cleaned = cleaned.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  cleaned = cleaned.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  
  // Format bullet points (but not numbered lists which we use for sections)
  cleaned = cleaned.replace(/^- (.+)$/gm, '• $1');
  cleaned = cleaned.replace(/^\* (.+)$/gm, '• $1');
  
  // ======================
  // STEP 6: Convert to HTML
  // ==================
  
  // Convert newlines to <br>
  cleaned = cleaned.replace(/\n/g, '<br>');
  
  // Clean up empty <br> sequences
  cleaned = cleaned.replace(/(<br>){3,}/g, '<br><br>');
  
  // Add spacing after section headings
  cleaned = cleaned.replace(/(<\/strong>)([A-Za-z\u4e00-\u9fff])/g, '$1<br><br>$2');
  
  // Note: References section is already included in the input text.
  // We don't need to extract and re-add it - that was causing truncation.
  
  // Debug: Check if References is in output
  const hasRefsOutput = /References?|參考文獻|参考文献/i.test(cleaned);
  console.log('[formatQueryResponse] Output length:', cleaned.length, 'Has References:', hasRefsOutput);
  
  return cleaned;
}

/**
 * Render math formulas using KaTeX after content is inserted
 * This should be called after setting innerHTML
 */
function renderMathInElement(element: HTMLElement): void {
  // Check if KaTeX is loaded
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
    // KaTeX not loaded yet, retry after a short delay
    setTimeout(() => renderMathInElement(element), 500);
  }
}

/**
 * Render timeout response with formatted chunks
 */
function renderTimeoutResponse(responseText: string, container: HTMLElement): void {
  const chunkMatch = responseText.match(/Found (\d+) relevant chunks/);
  const chunkCount = chunkMatch ? chunkMatch[1] : 'some';
  
  let html = `<h3>⚠️ LLM Processing Timed Out</h3>`;
  html += `<p>The AI processing timed out after 25 seconds. Showing ${chunkCount} raw text chunks instead:</p><hr>`;
  
  const chunksStart = responseText.indexOf('\n\n');
  if (chunksStart > 0) {
    const chunks = responseText.substring(chunksStart + 2);
    const chunkLines = chunks.split('\n\n');
    
    chunkLines.forEach((chunk, index) => {
      if (chunk.trim()) {
        html += `<h4>Chunk ${index + 1}</h4><pre>${escapeHtml(chunk)}</pre><hr>`;
      }
    });
  } else {
    html += `<pre>${escapeHtml(responseText)}</pre>`;
  }
  
  // Add retry button
  html += `<button id="retryQueryBtn" class="btn">🔄 Retry with Simpler Query</button>`;
  container.innerHTML = html;
  
  getElement('retryQueryBtn')?.addEventListener('click', () => {
    const currentQuery = getElement<HTMLTextAreaElement>('queryText')?.value || '';
    const simplerQuery = currentQuery.replace(/explain|in detail|with examples|comprehensive|detailed/gi, '').trim();
    if (simplerQuery && simplerQuery !== currentQuery) {
      getElement<HTMLTextAreaElement>('queryText')!.value = simplerQuery;
      handleRunQuery();
    } else {
      alert('Try a simpler, more specific query. Example: "What is Bayesian probability?"');
    }
  });
}

/**
 * Handle query errors
 */
function handleQueryError(error: unknown, container: HTMLElement): void {
  console.error('Query error:', error);
  
  if (error instanceof Error) {
    if (error.name === 'AbortError') {
      container.textContent = '⏰ Query was cancelled or timed out after 5 minutes.';
    } else if (error.message.includes('network') || error.message.includes('fetch')) {
      container.innerHTML = `❌ Network error. <button id="retryErrorBtn" class="btn">Retry</button>`;
      getElement('retryErrorBtn')?.addEventListener('click', handleRunQuery);
    } else {
      container.textContent = `❌ Error: ${error.message}`;
    }
  } else {
    container.textContent = '❌ Unknown error occurred';
  }
}

/**
 * Get tab HTML
 */
export function getQueryTabHTML(): string {
  return `
    <div id="query" class="tab-content card active" role="tabpanel" aria-labelledby="tab-query">
      <h2>🔍 Query Knowledge Graph</h2>
      
      
      <h3 id="queryModeLabel">Query Mode</h3>
      <div class="radio-group" role="radiogroup" aria-labelledby="queryModeLabel">
        <label class="radio-option" title="Smart unified search: combines semantic, keyword, entity, and relationship embeddings (Recommended)">
          <input type="radio" name="queryMode" value="smart" checked> Smart
        </label>
        <label class="radio-option" title="Semantic hybrid search: vector similarity + keyword matching + relationship enhancement">
          <input type="radio" name="queryMode" value="semantic"> Semantic
        </label>
        <label class="radio-option" title="Entity-focused search with relationship expansion">
          <input type="radio" name="queryMode" value="entity-lookup"> Entity-lookup
        </label>
        <label class="radio-option" title="Knowledge graph relationship traversal with embedding enhancement">
          <input type="radio" name="queryMode" value="graph-traversal"> Graph-traversal
        </label>
      </div>
      
      <h3 id="queryDetailLabel">Answer Detail Level</h3>
      <div class="radio-group" role="radiogroup" aria-labelledby="queryDetailLabel">
        <label class="radio-option" title="Quick answer using 10 chunks">
          <input type="radio" name="queryDetail" value="quick"> ⚡ Quick
        </label>
        <label class="radio-option" title="Balanced answer using 20 chunks">
          <input type="radio" name="queryDetail" value="balanced" checked> 📊 Balanced
        </label>
        <label class="radio-option" title="Comprehensive answer (2000+ words)">
          <input type="radio" name="queryDetail" value="comprehensive"> 📚 Comprehensive
        </label>
        <label class="radio-option" title="Ultra comprehensive (3000-4000 words) - Extended wait">
          <input type="radio" name="queryDetail" value="ultra"> 🎓 Ultra Deep
        </label>
      </div>
      
      <label for="queryText" class="sr-only">Enter your question</label>
      <textarea id="queryText" placeholder="Ask a question about your knowledge graph...&#10;Example: What do you know about Alibaba?&#10;&#10;Tip: For complex queries, the AI may time out after 25 seconds.&#10;Try simpler, more specific questions for better results." rows="6" aria-describedby="queryText-hint"></textarea>
      <p id="queryText-hint" class="hint">Type your question about the knowledge graph</p>
      
      <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <button id="runQueryBtn" class="btn" aria-label="Submit query">🔍 Ask Question</button>
        <button type="button" id="printQueryBtn" class="btn" style="padding: 6px 12px; font-size: 13px; display: none;" aria-label="Print answer">🖨️ Print</button>
      </div>
      
      <div id="queryResult" style="display: none;" aria-live="polite">

        <div id="answerText" class="result-box query-answer"></div>
        
        <h3>Sources:</h3>
        <div id="sourcesText" class="sources-box"></div>
      </div>
      
      <!-- KaTeX for math rendering -->
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
      <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
      <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
      
      <style>
        /* Query Response Formatting */
        .query-answer {
          line-height: 1.8;
          white-space: pre-wrap;
          word-wrap: break-word;
        }
        
        /* Keep math equations on single line */
        .query-answer .math-inline {
          white-space: nowrap;
          display: inline-block;
        }
        
        /* H1 - Title (Cyan, biggest, boldest) */
        .query-answer .query-h1 {
          display: block;
          font-size: 1.8em;
          font-weight: 800;
          color: #00BCD4;
          margin-top: 18px;
          margin-bottom: 16px;
          padding-bottom: 10px;
          border-bottom: 3px solid #00BCD4;
        }
        
        /* H2 - Executive Summary (Green, bold) */
        .query-answer .query-h2 {
          display: block;
          font-size: 1.5em;
          font-weight: 700;
          color: #4CAF50;
          margin-top: 14px;
          margin-bottom: 10px;
          padding-left: 12px;
          border-left: 4px solid #4CAF50;
        }
        
        /* H3 - Section headings with blue border */
        .query-answer .query-h3 {
          display: block;
          font-size: 1.3em;
          font-weight: 600;
          color: #64b5f6;
          margin-top: 12px;
          margin-bottom: 8px;
          border-left: 3px solid #64b5f6;
          padding-left: 10px;
        }
        
        /* H4 - Subsection headings */
        .query-answer .query-h4 {
          display: block;
          font-size: 1.2em;
          font-weight: 600;
          color: #e0e0e0;
          margin-top: 10px;
          margin-bottom: 6px;
        }
        
        /* References section (Green) */
        .query-answer .references-section,
        .query-answer .query-references {
          background: rgba(76, 175, 80, 0.1);
          border: 1px solid rgba(76, 175, 80, 0.3);
          border-radius: 8px;
          padding: 12px 16px;
          margin-top: 20px;
          color: #4CAF50;
          font-weight: 600;
        }
        
        /* Sources for Verification section (Orange) */
        .query-answer .sources-section,
        .query-answer .sources-verification {
          background: rgba(255, 152, 0, 0.1);
          border: 1px dashed rgba(255, 152, 0, 0.5);
          border-radius: 8px;
          padding: 12px 16px;
          margin-top: 16px;
          color: #FF9800;
          font-weight: 600;
          font-family: monospace;
        }
        
        /* Conclusion styling */
        .query-answer .conclusion,
        .query-answer .query-conclusion {
          background: rgba(156, 39, 176, 0.1);
          border-left: 4px solid #9C27B0;
          padding: 12px 16px;
          margin-top: 16px;
          font-style: italic;
        }
        
        .query-answer br + br {
          content: "";
          display: block;
          margin-top: 8px;
        }
        
        /* Academic Citations [X] */
        .query-answer .citation-ref,
        .query-answer [class*="citation"] {
          color: #64b5f6;
          font-weight: 600;
          font-size: 0.85em;
          vertical-align: super;
          margin: 0 1px;
        }
        
        /* Inline citation numbers [1], [2,3] */
        .query-answer {
          /* Match bracketed numbers and style them as citations */
        }
        
        /* Bold text **text** */
        .query-answer strong {
          font-weight: 600;
          color: var(--text-primary, #e0e0e0);
        }
        
        /* Table Styling */
        .query-table-container {
          overflow-x: auto;
          margin: 16px 0;
          border-radius: 8px;
          border: 1px solid var(--border-color, #333);
        }
        
        .query-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.9em;
        }
        
        .query-table th,
        .query-table td {
          padding: 10px 12px;
          text-align: left;
          border-bottom: 1px solid var(--border-color, #333);
        }
        
        .query-table th {
          background: rgba(76, 175, 80, 0.15);
          font-weight: 600;
          color: var(--primary-color, #4CAF50);
        }
        
        .query-table tr:hover {
          background: rgba(255, 255, 255, 0.03);
        }
        
        .query-table tr:last-child td {
          border-bottom: none;
        }
        
        .query-table-container + br {
          display: none;
        }
        
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
        
        /* Clean Academic Format Styles */
        .query-answer .document-title {
          display: block;
          font-size: 1.6em;
          font-weight: 800;
          color: #00d4ff;
          margin-top: 0;
          margin-bottom: 20px;
          padding-bottom: 10px;
          border-bottom: 3px solid #00d4ff;
          text-align: center;
        }
        
        .query-answer .section-intro {
          display: block;
          font-size: 1.2em;
          font-weight: 600;
          color: #c0c0c0;
          margin-top: 20px;
          margin-bottom: 12px;
          font-style: italic;
        }
        
        .query-answer .section-references {
          display: block;
          font-size: 1.4em;
          font-weight: 700;
          color: #4CAF50;
          margin-top: 30px;
          margin-bottom: 15px;
          padding-top: 15px;
          border-top: 2px solid #4CAF50;
        }
        
        .query-answer .section-title {
          display: block;
          font-size: 1.3em;
          font-weight: 700;
          color: #e0e0e0;
          margin-top: 24px;
          margin-bottom: 12px;
          padding-bottom: 6px;
          border-bottom: 2px solid #4CAF50;
        }
        
        .query-answer .section-heading {
          display: block;
          font-size: 1.1em;
          font-weight: 600;
          color: #b0b0b0;
          margin-top: 16px;
          margin-bottom: 8px;
        }
        
        /* Clean References Section */
        .query-answer .clean-references-section {
          margin-top: 32px;
          padding-top: 16px;
          border-top: 2px solid #4CAF50;
        }
        
        .query-answer .clean-references-header {
          font-size: 1.3em;
          font-weight: 700;
          color: #4CAF50;
          margin-bottom: 12px;
        }
        
        .query-answer .clean-references-list {
          background: rgba(76, 175, 80, 0.05);
          border-radius: 8px;
          padding: 12px 16px;
        }
        
        .query-answer .clean-reference-item {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          padding: 6px 0;
          font-size: 0.95em;
          color: #c0c0c0;
          border-bottom: 1px dotted rgba(255, 255, 255, 0.1);
        }
        
        .query-answer .clean-reference-item:last-child {
          border-bottom: none;
        }
        
        .query-answer .clean-ref-number {
          font-weight: 600;
          color: #4CAF50;
          min-width: 24px;
          flex-shrink: 0;
        }
        
        /* Verification Sources Section */
        .query-answer .verification-sources-section {
          margin-top: 24px;
          padding-top: 12px;
          border-top: 1px dashed #FF9800;
        }
        
        .query-answer .verification-sources-header {
          font-size: 1.1em;
          font-weight: 600;
          color: #FF9800;
          margin-bottom: 10px;
        }
        
        .query-answer .verification-source-item {
          font-family: 'Courier New', monospace;
          font-size: 0.85em;
          color: #aaa;
          padding: 4px 0;
          word-break: break-all;
        }
      </style>
      
      <h3>Test Queries</h3>
      <button id="testQueryCompanies" class="btn" aria-label="Run test query for companies">Companies</button>
      <button id="testQueryRelations" class="btn" aria-label="Run test query for relationships">Relationships</button>
      <button id="testQueryOverview" class="btn" aria-label="Run test query for overview">Overview</button>
    </div>
  `;
}
