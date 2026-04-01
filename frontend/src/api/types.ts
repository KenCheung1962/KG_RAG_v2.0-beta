/**
 * API type definitions
 */

export interface KGStats {
  entities?: number;
  total_entities?: number;
  relationships?: number;
  total_relations?: number;
  chunks?: number;
}

export interface DocStats {
  total_documents: number;
}

export interface Document {
  doc_id: string;
  filename: string;
  status?: string;
}

export interface DocumentStatus {
  indexed?: boolean;
  ready?: boolean;
  chunks?: number;
}

export interface UploadResult {
  doc_id: string;
  success: boolean;
}

export interface QueryRequest {
  message: string;
  mode?: string;
  /** Number of chunks to retrieve (higher = more context) */
  top_k?: number;
  /** System prompt to guide LLM response style */
  system_prompt?: string;
  /** Max tokens for response */
  max_tokens?: number;
  /** Temperature for response creativity (0-1) */
  temperature?: number;
  /** Request detailed comprehensive answer */
  detailed?: boolean;
  /** Enable ultra-comprehensive mode (3000-4000 words) */
  ultra_comprehensive?: boolean;
  /** Rerank method: semantic, vector, keyword, none */
  rerank?: boolean;
  rerank_method?: string;
  /** LLM provider configuration */
  llm_config?: LLMProviderConfig;
}

export interface LLMProviderConfig {
  /** Primary LLM provider: deepseek, minimax */
  provider: 'deepseek' | 'minimax';
  /** Fallback provider (optional) */
  fallback_provider?: 'deepseek' | 'minimax' | null;
}

export interface QueryWithFilesRequest {
  message: string;
  filenames: string[];
  /** Number of chunks to retrieve */
  top_k?: number;
  /** Request detailed comprehensive answer */
  detailed?: boolean;
  /** Enable ultra-comprehensive mode */
  ultra_comprehensive?: boolean;
  /** LLM provider configuration */
  llm_config?: LLMProviderConfig;
}

export interface QueryResponse {
  response?: string;
  answer?: string;
  sources?: string[] | number;
  source_documents?: string[] | number;
  detail?: string;
}

export interface HealthStatus {
  status: string;
  version?: string;
}

export interface FolderUploadRequest {
  folder_path: string;
  recursive: boolean;
}

export interface FolderUploadResult {
  total_files: number;
}
