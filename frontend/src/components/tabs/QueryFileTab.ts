/**
 * Query + File Tab Component
 */

import { uploadDocument, sendQuery, getDocumentStatus } from '@/api';
import { renderFileList } from '@/components/FileList';
import { showProgress, hideProgress, setProgressStatus } from '@/components/ProgressBar';
import { getElement, setVisible } from '@/utils/dom';
import { checkDuplicates } from './IngestTab';
import { escapeHtml, exponentialBackoff } from '@/utils/helpers';
import { formatQueryResponse } from './QueryTab';
import {
  getSelectedQueryFiles, addSelectedQueryFile, removeSelectedQueryFile,
  clearSelectedQueryFiles, setIsQuerying
} from '@/stores/appStore';
import type { QueryMode } from '@/config';

// Store the last answer for PDF export
let lastAnswerText = '';
let lastQueryText = '';

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
let lastSources: string[] = [];


/**
 * Get selected query detail level for file query
 */
function getQueryFileDetail(): { 
  top_k: number; 
  ultra_comprehensive: boolean;
  detailed: boolean;
  label: string;
} {
  const radio = document.querySelector('input[name="queryFileDetail"]:checked') as HTMLInputElement;
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
  // NOTE: Preserve <i> and <em> tags BEFORE escaping HTML entities
  let formattedAnswer = processedText
    // Preserve <i>...</i> tags by converting to placeholder
    .replace(/<i>([\s\S]*?)<\/i>/gi, '__ITALIC_START__$1__ITALIC_END__')
    // Preserve <em>...</em> tags by converting to placeholder
    .replace(/<em>([\s\S]*?)<\/em>/gi, '__EM_START__$1__EM_END__')
    // Escape HTML entities
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Convert **text** to bold
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // Restore <i> tags
    .replace(/__ITALIC_START__/g, '<i>')
    .replace(/__ITALIC_END__/g, '</i>')
    // Restore <em> tags
    .replace(/__EM_START__/g, '<em>')
    .replace(/__EM_END__/g, '</em>');
  
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
      em, i { font-style: italic; }
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
      em, i { font-style: italic; }
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
export function initQueryFileTab(): void {
  getElement('queryFileInput')?.addEventListener('change', handleFileSelect);
  getElement('runQueryFileBtn')?.addEventListener('click', handleRunQueryWithFile);
  getElement('exportQueryFilePdfBtn')?.addEventListener('click', (e) => printAnswer(e));
  
  // Clear previous answer when user starts typing a new query
  getElement('queryFileText')?.addEventListener('input', () => {
    const printBtn = getElement('exportQueryFilePdfBtn');
    if (printBtn) printBtn.style.display = 'none';
  });
}

/**
 * Handle file selection
 */
function handleFileSelect(): void {
  const input = getElement<HTMLInputElement>('queryFileInput');
  if (!input?.files?.length) return;
  
  Array.from(input.files).forEach(file => addSelectedQueryFile(file));
  renderQueryFiles();
  input.value = '';
}

/**
 * Render query file list
 */
function renderQueryFiles(): void {
  renderFileList(getSelectedQueryFiles(), {
    containerId: 'querySelectedFilesList',
    onRemove: (index) => {
      removeSelectedQueryFile(index);
      renderQueryFiles();
    },
    emptyText: 'Selected files:'
  });
}

/**
 * Query database only (no files)
 */
/**
 * Query database only (no files)
 */
async function queryDatabaseOnly(
  queryText: string, 
  detail = getQueryFileDetail(),
  answerDiv?: HTMLElement | null,
  exportBtn?: HTMLButtonElement | null
): Promise<void> {
  const { sendQuery } = await import('@/api');
  const controller = new AbortController();
  
  // Set timeout based on mode - MUST match client.ts timeouts
  const isUltra = detail.ultra_comprehensive;
  const timeoutMs = isUltra ? 900000 : (detail.detailed ? 600000 : 180000);
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    const result = await sendQuery({ 
      message: queryText,
      top_k: detail.top_k,
      detailed: detail.detailed,
      ultra_comprehensive: detail.ultra_comprehensive
    }, controller.signal);
    clearTimeout(timeoutId);
    
    const responseText = result.response || result.answer || '';
    
    // Store sources and build answer with references for printing
    // Check multiple possible source field names (same as QueryTab)
    const sources = result.sources || result.source_documents || (result as Record<string, unknown>).source || (result as Record<string, unknown>).chunks;
    console.log('[QueryFile] Raw sources:', sources);
    
    if (Array.isArray(sources)) {
      lastSources = sources.map((s: unknown): string => {
        if (typeof s === 'string') return s;
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
    console.log('[QueryFile] Processed sources:', lastSources);
    
    // Extract which sources are actually CITED in the response text (same as QueryTab)
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
    console.log('[QueryFile] Sources cited in text:', Array.from(citedSourceNumbers));
    
    // Build answer with reference section for print output
    // ONLY include references that are actually CITED in the text (same as QueryTab)
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
    lastAnswerText = answerWithRefs;
    
    // Format the response with improved styling - include ONLY cited references (same as QueryTab)
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
    
    // Use innerHTML with formatQueryResponse for proper formatting
    if (answerDiv) {
      answerDiv.innerHTML = formatQueryResponse(displayText);
    }
    
    // Show print button
    if (exportBtn) {
      exportBtn.style.display = 'inline-block';
    }
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      if (answerDiv) answerDiv.textContent = '⏰ Query timed out. The LLM is taking too long.';
    } else {
      if (answerDiv) answerDiv.textContent = `❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  }
}

/**
 * Query with existing (already uploaded) files + database
 */
async function queryWithExistingFiles(
  queryText: string,
  filenames: string[],
  detail = getQueryFileDetail(),
  answerDiv?: HTMLElement | null,
  exportBtn?: HTMLButtonElement | null
): Promise<void> {
  const controller = new AbortController();
  
  // Set timeout based on mode - MUST match client.ts timeouts
  const isUltra = detail.ultra_comprehensive;
  const timeoutMs = isUltra ? 900000 : (detail.detailed ? 600000 : 180000);
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    if (answerDiv) {
      answerDiv.innerHTML = `<span class="spinner"></span> <strong>${detail.label} Mode</strong><br>Querying with ${filenames.length} existing file(s)...`;
    }
    
    // Use sendQuery (same as Query mode) - files are already indexed in database
    const result = await sendQuery({ 
      message: queryText,
      top_k: detail.top_k,
      detailed: detail.detailed,
      ultra_comprehensive: detail.ultra_comprehensive
    }, controller.signal);
    
    clearTimeout(timeoutId);
    
    if (result.response || result.answer) {
      const responseText = result.response || result.answer || '';
      
      // Store sources and build answer with references for printing
      // Check multiple possible source field names (same as QueryTab)
      const sources = result.sources || result.source_documents || (result as Record<string, unknown>).source || (result as Record<string, unknown>).chunks;
      console.log('[QueryFile] Raw sources:', sources);
      
      if (Array.isArray(sources)) {
        lastSources = sources.map((s: unknown): string => {
          if (typeof s === 'string') return s;
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
      console.log('[QueryFile] Processed sources:', lastSources);
      
      // Extract which sources are actually CITED in the response text (same as QueryTab)
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
      console.log('[QueryFile] Sources cited in text:', Array.from(citedSourceNumbers));
      
      // Build answer with reference section for print output
      // ONLY include references that are actually CITED in the text (same as QueryTab)
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
      lastAnswerText = answerWithRefs;
      
      // Format the response with improved styling - include ONLY cited references (same as QueryTab)
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
      
      // Display with proper formatting
      if (answerDiv) {
        answerDiv.innerHTML = formatQueryResponse(displayText);
      }
      if (exportBtn) {
        exportBtn.style.display = 'inline-block';
      }
    } else if (result.detail) {
      if (answerDiv) answerDiv.textContent = `❌ Error: ${result.detail}`;
    } else {
      if (answerDiv) answerDiv.textContent = JSON.stringify(result, null, 2);
    }
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      if (answerDiv) answerDiv.textContent = '⏰ Query timed out after 5 minutes.';
    } else {
      if (answerDiv) answerDiv.textContent = `❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  }
}

/**
 * Handle run query with file
 */
async function handleRunQueryWithFile(): Promise<void> {
  const queryText = getElement<HTMLTextAreaElement>('queryFileText')?.value.trim();
  let files = getSelectedQueryFiles();
  
  if (!files.length || !queryText) {
    alert('Please upload file(s) and enter a question');
    return;
  }
  
  // Store query for export
  lastQueryText = queryText;
  
  // Get query detail level
  const detail = getQueryFileDetail();
  
  setIsQuerying(true);
  const answerDiv = getElement('queryFileAnswer');
  const exportBtn = getElement('exportQueryFilePdfBtn') as HTMLButtonElement | null;
  const runBtn = getElement('runQueryFileBtn');
  if (runBtn) runBtn.classList.add('blinking');  // Add blinking effect during search
  
  console.log('[QueryFile] Starting query, exportBtn:', exportBtn);
  
  setVisible('queryFileResult', true);
  if (exportBtn) {
    exportBtn.style.display = 'none';
    console.log('[QueryFile] Button hidden');
  }
  
  const isUltra = detail.ultra_comprehensive;
  const isComprehensive = detail.detailed && !isUltra;
  const estimatedTime = isUltra ? '3-5 min' : (isComprehensive ? '2-4 min' : '30-60 sec');
  
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
  
  answerDiv!.innerHTML = `<span class="spinner"></span> <strong>${detail.label} Mode</strong><br>${modeMessage}<br>Estimated time: ${estimatedTime}<br><small>Please wait, do not close or refresh the page</small>`;
  
  try {
    // Check for duplicates
    const { duplicates, newFiles, duplicateDocIds } = await checkDuplicates(files);
    
    if (duplicates.length > 0) {
      if (files.length === 1) {
        const action = confirm(`File "${escapeHtml(duplicates[0])}" already exists. Click OK to overwrite, Cancel to use existing file.`);
        if (!action) {
          // User chose to skip upload - query with the existing file
          answerDiv!.innerHTML = `<span class="spinner"></span> <strong>${detail.label} Mode</strong><br>📄 Using existing file...`;
          clearSelectedQueryFiles();
          await queryWithExistingFiles(queryText, duplicates, detail, answerDiv, exportBtn);
          setIsQuerying(false);
          return;
        }
      } else {
        const dupList = escapeHtml(duplicates.join(', '));
        const newList = escapeHtml(newFiles.map(f => f.name).join(', '));
        
        const action = newFiles.length > 0
          ? confirm(`Found ${duplicates.length} existing: ${dupList}\n\nNew: ${newList}\n\nClick OK to upload all, Cancel to skip duplicates and use existing files.`)
          : confirm(`All ${duplicates.length} exist: ${dupList}\n\nClick OK to overwrite all, Cancel to use existing files.`);
        
        if (!action) {
          if (newFiles.length === 0) {
            // All files exist, user wants to use existing files
            answerDiv!.innerHTML = `<span class="spinner"></span> <strong>${detail.label} Mode</strong><br>📄 Using ${duplicates.length} existing file(s)...`;
            clearSelectedQueryFiles();
            await queryWithExistingFiles(queryText, duplicates, detail, answerDiv, exportBtn);
            setIsQuerying(false);
            return;
          }
          // Some new, some existing - user wants to skip duplicates, only upload new ones
          files = newFiles;
          // We'll still query with all files (new + existing duplicates) after upload
        }
      }
    }
    
    if (files.length === 0 && duplicates.length === 0) {
      // No files at all - query database only
      await queryDatabaseOnly(queryText, detail, answerDiv, exportBtn);
      setIsQuerying(false);
      return;
    }
    
    // Upload files
    const uploadedDocs: { filename: string; doc_id: string }[] = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      answerDiv!.textContent = `📤 Uploading ${i + 1}/${files.length}: ${escapeHtml(file.name)}...`;
      
      try {
        const result = await uploadDocument(file);
        if (result.doc_id) {
          uploadedDocs.push({ filename: file.name, doc_id: result.doc_id });
        }
      } catch (error) {
        console.error(`Upload failed for ${file.name}:`, error);
      }
    }
    
    if (uploadedDocs.length === 0) {
      answerDiv!.textContent = '❌ Upload failed. No files were uploaded.';
      setIsQuerying(false);
      return;
    }
    
    // Wait for indexing
    await waitForIndexing(uploadedDocs, answerDiv!);
    
    // Query with files (including both newly uploaded and existing duplicates if user skipped them)
    const uploadedFilenames = uploadedDocs.map(d => d.filename);
    // If user skipped duplicates, include them in the query
    const skippedDuplicates = (duplicateDocIds && files.length < getSelectedQueryFiles().length) 
      ? duplicates.filter(d => !uploadedFilenames.includes(d))
      : [];
    const filenames = [...uploadedFilenames, ...skippedDuplicates];
    answerDiv!.innerHTML = `<span class="spinner"></span> <strong>${detail.label} Mode</strong><br>Querying knowledge graph (including ${filenames.length} uploaded file(s))...`;
    
    const controller = new AbortController();
    
    // Set timeout based on mode - MUST match client.ts timeouts
    const timeoutMs = isUltra ? 900000 : (detail.detailed ? 600000 : 180000);
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    
    // Use sendQuery (same endpoint as Query mode) - files are now indexed in database
    const result = await sendQuery({ 
      message: queryText,
      top_k: detail.top_k,
      detailed: detail.detailed,
      ultra_comprehensive: detail.ultra_comprehensive
    }, controller.signal);
    clearTimeout(timeoutId);
    
    if (result.response || result.answer) {
      const responseText = result.response || result.answer || '';
      
      // Store sources and build answer with references for printing
      // Check multiple possible source field names (same as QueryTab)
      const sources = result.sources || result.source_documents || (result as Record<string, unknown>).source || (result as Record<string, unknown>).chunks;
      console.log('[QueryFile] Raw sources:', sources);
      console.log('[QueryFile] sources type:', typeof sources);
      console.log('[QueryFile] sources isArray:', Array.isArray(sources));
      
      // TEMPORARY: If backend returns number instead of array, log the issue
      if (typeof sources === 'number') {
        console.warn('[QueryFile] Backend returned source COUNT instead of source filenames. References cannot be displayed.');
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
      console.log('[QueryFile] Processed sources:', lastSources);
      
      // Extract which sources are actually CITED in the response text (same as QueryTab)
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
      console.log('[QueryFile] Sources cited in text:', Array.from(citedSourceNumbers));
      
      // Build answer with reference section for print output
      // ONLY include references that are actually CITED in the text (same as QueryTab)
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
      lastAnswerText = answerWithRefs;
      
      // Format the response with improved styling - include ONLY cited references (same as QueryTab)
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
      answerDiv!.innerHTML = formatQueryResponse(displayText);
      
      // Display sources in structured format (like QueryTab)
      const sourcesText = getElement('queryFileSources');
      if (sourcesText && lastSources.length > 0) {
        // Build structured sources display with 📚 References and 🔍 Sources sections
        let sourcesHtml = '';
        
        // 📚 References section (Green) - only cited sources
        const citedSourceNumbers = new Set<number>();
        const citationMatches = responseText.match(/\[(\d+)\]|Source\s+(\d+)/gi);
        if (citationMatches) {
          citationMatches.forEach((match: string) => {
            const nums = match.match(/\d+/);
            if (nums) citedSourceNumbers.add(parseInt(nums[0], 10));
          });
        }
        
        // Filter to only cited sources
        const citedSources = Array.from(citedSourceNumbers)
          .sort((a, b) => a - b)
          .map(num => lastSources[num - 1])
          .filter(src => src !== undefined);
        
        // Add 📚 References section (only if citations detected)
        if (citedSources.length > 0) {
          sourcesHtml += `<div class="sources-section references-section">`;
          sourcesHtml += `<div class="sources-header references-header">📚 References</div>`;
          citedSources.forEach((src, idx) => {
            sourcesHtml += `<div class="source-item references-item">${idx + 1}. ${escapeHtml(src)}</div>`;
          });
          sourcesHtml += `</div>`;
        }
        
        // Add 🔍 Sources (for Verification) section (Orange) - all sources
        sourcesHtml += `<div class="sources-section verification-section">`;
        sourcesHtml += `<div class="sources-header verification-header">🔍 Sources (for Verification)</div>`;
        lastSources.forEach((src, idx) => {
          sourcesHtml += `<div class="source-item verification-item">${idx + 1}. ${escapeHtml(src)}</div>`;
        });
        sourcesHtml += `</div>`;
        
        sourcesText.innerHTML = sourcesHtml;
      } else if (sourcesText) {
        sourcesText.innerHTML = `<div class="source-item">No sources available</div>`;
      }
      
      if (exportBtn) {
        exportBtn.style.display = 'inline-block';
        console.log('[QueryFile] Button shown');
      }
    } else if (result.detail) {
      answerDiv!.textContent = `❌ Error: ${result.detail}`;
    } else {
      answerDiv!.textContent = JSON.stringify(result, null, 2);
    }
    
  } catch (error) {
    console.error('Query with file failed:', error);
    if (error instanceof Error && error.name === 'AbortError') {
      answerDiv!.textContent = '⏰ Query timed out after 5 minutes.';
    } else {
      answerDiv!.textContent = `❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`;
    }
  } finally {
    setIsQuerying(false);
    const runBtn = getElement('runQueryFileBtn');
    if (runBtn) runBtn.classList.remove('blinking');  // Remove blinking effect when search completes
  }
}

/**
 * Wait for documents to be indexed
 */
async function waitForIndexing(
  docs: { doc_id: string }[],
  statusEl: HTMLElement
): Promise<void> {
  let allIndexed = false;
  let pollCount = 0;
  
  while (!allIndexed && pollCount < 30) {
    const delay = exponentialBackoff(pollCount, 1000, 5000);
    await new Promise(r => setTimeout(r, delay));
    pollCount++;
    
    let indexedCount = 0;
    
    for (const doc of docs) {
      const status = await getDocumentStatus(doc.doc_id);
      if (status?.indexed || status?.ready || (status?.chunks && status.chunks > 0)) {
        indexedCount++;
      }
    }
    
    statusEl.textContent = `⏳ Indexing... (${pollCount}s) - ${indexedCount}/${docs.length} ready`;
    
    if (indexedCount === docs.length) {
      allIndexed = true;
      break;
    }
  }
  
  if (!allIndexed) {
    statusEl.textContent = '⚠️ Indexing in progress, but proceeding with query...';
  } else {
    statusEl.textContent = '✅ Files indexed! Now querying...';
  }
}

/**
 * Get tab HTML
 */
export function getQueryFileTabHTML(): string {
  return `
    <div id="queryfile" class="tab-content card" role="tabpanel" aria-labelledby="tab-queryfile">
      <h2>🔗 Query with File(s)</h2>
      
      
      <h3>Upload Document(s)</h3>
      <label for="queryFileInput" class="sr-only">Select files to upload</label>
      <input type="file" id="queryFileInput" accept=".txt,.md,.pdf,.doc,.docx" multiple aria-describedby="queryFileInput-hint">
      <p id="queryFileInput-hint" class="hint">You can select multiple files (Ctrl+Click or Cmd+Click)</p>
      
      <div id="querySelectedFilesList" class="file-list" style="display: none;"></div>
      
      <h3>Question</h3>
      <label for="queryFileText" class="sr-only">Enter your question about the uploaded file</label>
      <textarea id="queryFileText" placeholder="Ask a question about the uploaded file and knowledge graph..." rows="3" aria-describedby="queryFileText-hint"></textarea>
      <p id="queryFileText-hint" class="hint">Type your question about the uploaded document</p>
      
      <h3 id="queryFileDetailLabel">Answer Detail Level</h3>
      <div class="radio-group" role="radiogroup" aria-labelledby="queryFileDetailLabel">
        <label class="radio-option" title="Quick answer using 10 chunks">
          <input type="radio" name="queryFileDetail" value="quick"> ⚡ Quick
        </label>
        <label class="radio-option" title="Balanced answer using 20 chunks">
          <input type="radio" name="queryFileDetail" value="balanced" checked> 📊 Balanced
        </label>
        <label class="radio-option" title="Comprehensive answer">
          <input type="radio" name="queryFileDetail" value="comprehensive"> 📚 Comprehensive
        </label>
        <label class="radio-option" title="Ultra comprehensive - Extended wait">
          <input type="radio" name="queryFileDetail" value="ultra"> 🎓 Ultra Deep
        </label>
      </div>
      
      <button id="runQueryFileBtn" class="btn" aria-label="Submit query with uploaded files">🔍 Query with File</button>
      
      <div id="queryFileResult" style="display: none;" aria-live="polite">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">

          <button type="button" id="exportQueryFilePdfBtn" class="btn" style="padding: 6px 12px; font-size: 13px; background: var(--bg-tertiary, #333); border: 1px solid var(--border-color, #444); display: none;">
            🖨️ Print
          </button>
        </div>
        <div id="queryFileAnswer" class="result-box"></div>
        <div id="queryFileSources" class="sources-box" style="margin-top: 20px;"></div>
      </div>
    </div>
  `;
}
