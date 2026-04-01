/**
 * API client for LightRAG backend
 */

import { API_URL, API_KEY } from '@/config';
import { getLLMConfig } from '@/components/tabs/ConfigTab';
import type {
  KGStats, DocStats, Document, DocumentStatus, UploadResult,
  QueryRequest, QueryResponse, QueryWithFilesRequest, HealthStatus,
  FolderUploadRequest, FolderUploadResult, LLMProviderConfig
} from './types';

/**
 * Get LLM configuration for entity extraction (from Config Tab)
 */
function getEntityExtractionConfig(): LLMProviderConfig {
  const config = getLLMConfig();
  return {
    provider: config.entityExtraction.primary,
    fallback_provider: config.entityExtraction.fallback
  };
}

/**
 * Default headers with API key
 */
const defaultHeaders = {
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY
};

/**
 * Check if backend is healthy
 */
export async function isBackendHealthy(): Promise<boolean> {
  try {
    const resp = await fetch(`${API_URL}/health`, { 
      method: 'GET',
      headers: { 'X-API-Key': API_KEY },
      signal: AbortSignal.timeout(5000)
    });
    return resp.ok;
  } catch {
    return false;
  }
}

/**
 * Delay utility
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Fetch with timeout, abort support, and retry logic
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = 600000,  // 10 min default for comprehensive generation
  retries = 3
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    
    // Check if it's a timeout/abort error
    if (error instanceof Error && error.name === 'AbortError') {
      const timeoutError = new Error(`Request timeout after ${timeoutMs/1000}s`);
      timeoutError.name = 'TimeoutError';
      throw timeoutError;
    }
    
    // Retry on network errors
    if (retries > 0 && error instanceof TypeError) {
      console.log(`Network error, retrying... (${retries} attempts left)`);
      await delay(1000 * (4 - retries)); // Exponential backoff: 1s, 2s, 3s
      return fetchWithTimeout(url, options, timeoutMs, retries - 1);
    }
    
    throw error;
  }
}

/**
 * Build API URL with cache-busting
 */
function buildUrl(path: string): string {
  const separator = path.includes('?') ? '&' : '?';
  return `${API_URL}${path}${separator}_=${Date.now()}`;
}

// API Functions

export async function fetchKGStats(): Promise<KGStats> {
  // Use health endpoint which has entities_count and relationships_count
  const resp = await fetchWithTimeout(`${API_URL}/health`, {
    headers: { 'X-API-Key': API_KEY }
  });
  if (!resp.ok) throw new Error(`Failed to fetch KG stats: ${resp.status}`);
  const data = await resp.json();
  return {
    entities: data.entities_count ?? data.entities ?? 0,
    relationships: data.relationships_count ?? data.relationships ?? 0,
    chunks: data.chunks_count ?? data.chunks ?? 0
  };
}

export async function fetchDocStats(): Promise<DocStats> {
  // Use health endpoint for document count
  const resp = await fetchWithTimeout(`${API_URL}/health`, {
    headers: { 'X-API-Key': API_KEY }
  });
  if (!resp.ok) throw new Error(`Failed to fetch doc stats: ${resp.status}`);
  const data = await resp.json();
  return {
    total_documents: data.documents_count ?? data.total_documents ?? 0
  };
}

export async function fetchDocuments(limit = 1000): Promise<Document[]> {
  const resp = await fetchWithTimeout(`${API_URL}/api/v1/documents?limit=${limit}`, {
    headers: { 'X-API-Key': API_KEY }
  });
  if (!resp.ok) throw new Error(`Failed to fetch documents: ${resp.status}`);
  return resp.json();
}

/**
 * Read file content using FileReader (handles both text and binary files)
 */
function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = () => {
      const result = reader.result as string;
      // Data URL format: data:[type];base64,[content]
      // Extract base64 part after the comma
      const base64Content = result.split(',')[1];
      resolve(base64Content);
    };
    
    reader.onerror = () => {
      reject(new Error(`Failed to read file: ${file.name}`));
    };
    
    reader.readAsDataURL(file);
  });
}

export async function uploadDocument(file: File): Promise<UploadResult> {
  // Read file as base64 using FileReader (works for all file types)
  const base64Content = await readFileAsBase64(file);
  
  // Detect content type
  const contentType = file.type || 'application/octet-stream';
  const isText = contentType.startsWith('text/') || 
                 file.name.match(/\.(txt|md|csv|json|html|xml|js|ts|py|css)$/i);
  
  // Get LLM configuration from Config Tab for entity extraction
  const llmConfig = getEntityExtractionConfig();
  
  const resp = await fetchWithTimeout(`${API_URL}/api/v1/documents/upload/json`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY 
    },
    body: JSON.stringify({
      content: base64Content,
      id: file.name,
      content_type: isText ? 'text/plain' : contentType,
      llm_config: llmConfig  // Pass LLM config from Config Tab
    })
  }, 120000); // 2 minute timeout for uploads (increased from 1 min)
  
  if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`);
  return resp.json();
}

export async function getDocumentStatus(docId: string): Promise<DocumentStatus | null> {
  try {
    const resp = await fetchWithTimeout(`${API_URL}/api/v1/documents/${docId}/status`, {
      headers: { 'X-API-Key': API_KEY }
    }, 10000);
    if (!resp.ok) return null;
    return resp.json();
  } catch {
    return null;
  }
}

/**
 * Default system prompt for comprehensive answers
 */
const COMPREHENSIVE_SYSTEM_PROMPT = `You are a knowledgeable research assistant with access to a document database.

Your task is to provide comprehensive, detailed answers based on the retrieved context. Follow these guidelines:

1. **Be thorough**: Provide detailed explanations with specific examples, data points, and relationships found in the context.

2. **Structure your answer**: Use clear headings (# for main sections, ## for subsections) and organize information logically.

3. **Synthesize information**: Don't just list facts—connect ideas, explain relationships, and provide insights that demonstrate deep understanding.

4. **Include specifics**: Cite specific entities, metrics, dates, or technical details when available in the context.

5. **Explain relevance**: Briefly explain why the information matters or how concepts relate to each other.

6. **No unnecessary disclaimers**: If the context provides relevant information, answer confidently without apologizing for "limited context."

7. **Expand on concepts**: When discussing technical topics, explain underlying principles and mechanisms, not just surface-level facts.`;

/**
 * Map frontend mode names to backend mode names
 * Frontend: 'smart' | 'semantic' | 'entity-lookup' | 'graph-traversal'
 * Backend:  'smart' | 'semantic-hybrid' | 'entity-lookup' | 'graph-traversal'
 * 
 * Note: 'semantic' frontend maps to 'semantic-hybrid' backend for enhanced search
 */
function mapQueryMode(mode?: string): string {
  const modeMap: Record<string, string> = {
    'smart': 'smart',
    'semantic': 'semantic-hybrid',  // Semantic button uses hybrid (vector + keyword + relationship)
    'entity-lookup': 'entity-lookup',
    'graph-traversal': 'graph-traversal'
  };
  return modeMap[mode || ''] || 'smart';  // Default to smart mode
}

export async function sendQuery(
  request: QueryRequest,
  signal?: AbortSignal
): Promise<QueryResponse> {
  // Determine query mode
  const isUltra = request.ultra_comprehensive;
  const isComprehensive = isUltra || request.detailed || 
    request.message.toLowerCase().includes('explain') || 
    request.message.toLowerCase().includes('detail') ||
    request.message.toLowerCase().includes('comprehensive');
  
  // Get LLM configuration from ConfigTab
  const llmConfig = getLLMConfig();
  const providerConfig: LLMProviderConfig = {
    provider: llmConfig.responseGeneration.primary,
    fallback_provider: llmConfig.responseGeneration.fallback
  };
  
  // Enhance request for more comprehensive answers
  const enhancedRequest = {
    ...request,
    // Map mode names for backend compatibility
    mode: mapQueryMode(request.mode),
    // Increase chunks retrieved for more context
    top_k: isUltra ? 40 : (request.top_k ?? 20),
    // Enable reranking by default
    rerank: request.rerank ?? true,
    rerank_method: request.rerank_method ?? 'semantic',
    // Use comprehensive system prompt if not provided
    system_prompt: request.system_prompt ?? COMPREHENSIVE_SYSTEM_PROMPT,
    // Request detailed response
    detailed: isComprehensive,
    ultra_comprehensive: isUltra,
    // Temperature based on mode
    temperature: request.temperature ?? 0.3,
    // Set max_tokens based on mode to prevent truncation
    // Higher limits for comprehensive modes to ensure complete responses
    max_tokens: isUltra ? 8192 : (isComprehensive ? 8192 : 4096),
    // Use the user's message exactly as provided
    message: request.message,
    // Include LLM provider configuration
    llm_config: providerConfig
  };
  
  // Extended timeout based on mode
  let timeoutMs: number;
  if (isUltra) {
    timeoutMs = 900000;  // 15 min for ultra (6+ sections × 3 subsections + conclusion)
  } else if (isComprehensive) {
    timeoutMs = 600000;  // 10 min for comprehensive (5 sections × 3 subsections + conclusion)
  } else if (request.top_k && request.top_k >= 20) {
    timeoutMs = 300000;  // 5 min for balanced
  } else {
    timeoutMs = 180000;  // 3 min for quick
  }
  
  const resp = await fetchWithTimeout(buildUrl('/api/v1/chat'), {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY 
    },
    body: JSON.stringify(enhancedRequest),
    signal
  }, timeoutMs);
  
  if (!resp.ok) throw new Error(`Query failed: ${resp.status}`);
  return resp.json();
}

export async function sendQueryWithFiles(
  request: QueryWithFilesRequest,
  signal?: AbortSignal
): Promise<QueryResponse> {
  // Determine mode from request
  const isUltra = request.ultra_comprehensive;
  const isComprehensive = request.detailed;
  
  // Get LLM configuration from ConfigTab
  const llmConfig = getLLMConfig();
  const providerConfig: LLMProviderConfig = {
    provider: llmConfig.responseGenerationWithFile.primary,
    fallback_provider: llmConfig.responseGenerationWithFile.fallback
  };
  
  // Enhance request based on mode
  const enhancedRequest = {
    ...request,
    top_k: request.top_k ?? 20,
    system_prompt: isUltra || isComprehensive ? COMPREHENSIVE_SYSTEM_PROMPT : undefined,
    detailed: isComprehensive,
    ultra_comprehensive: isUltra,
    temperature: isComprehensive ? 0.3 : 0.3,
    // Set max_tokens to prevent truncation
    max_tokens: isUltra ? 8192 : (isComprehensive ? 8192 : 4096),
    // Use the user's message exactly as provided
    message: request.message,
    // Include LLM provider configuration
    llm_config: providerConfig
  };
  
  // Set timeout based on mode
  const timeoutMs = isUltra ? 900000 : (isComprehensive ? 600000 : 180000);
  
  const resp = await fetchWithTimeout(buildUrl('/api/v1/chat/with-doc'), {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY 
    },
    body: JSON.stringify(enhancedRequest),
    signal
  }, timeoutMs);
  
  if (!resp.ok) throw new Error(`Query with files failed: ${resp.status}`);
  return resp.json();
}

export async function uploadFolder(
  request: FolderUploadRequest
): Promise<FolderUploadResult> {
  // Get LLM configuration from Config Tab for entity extraction
  const llmConfig = getEntityExtractionConfig();
  
  const resp = await fetchWithTimeout(`${API_URL}/api/v1/documents/upload/folder/json`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY 
    },
    body: JSON.stringify({
      ...request,
      llm_config: llmConfig  // Pass LLM config from Config Tab
    })
  }, 300000);
  
  if (!resp.ok) throw new Error(`Folder upload failed: ${resp.status}`);
  return resp.json();
}

export async function testConnection(): Promise<HealthStatus> {
  const resp = await fetchWithTimeout(`${API_URL}/health`, {
    headers: { 'X-API-Key': API_KEY }
  }, 10000);
  if (!resp.ok) throw new Error(`Health check failed: ${resp.status}`);
  return resp.json();
}

export async function clearDatabase(): Promise<void> {
  const resp = await fetchWithTimeout(`${API_URL}/api/v1/clear`, {
    method: 'DELETE',
    headers: { 'X-API-Key': API_KEY }
  }, 60000);
  
  if (!resp.ok) throw new Error(`Clear database failed: ${resp.status}`);
}
