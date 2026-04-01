/**
 * Application configuration
 */

// API Configuration
// @ts-ignore - Vite defines import.meta.env
export const API_URL = import.meta.env?.VITE_API_URL || 'http://localhost:8002';
export const API_KEY = import.meta.env?.VITE_API_KEY || 'static-internal-key';
export const DEFAULT_TIMEOUT = 300000; // 5 minutes for queries
export const STATS_REFRESH_INTERVAL = 10000; // 10 seconds
export const MAX_INDEXING_POLLS = 30;

// Feature flags
export const FEATURES = {
  enableAutoRefresh: true,
  enableNetworkRetry: true,
  enableDuplicateDetection: true,
} as const;

// Query modes (display names: Smart, Semantic, Entity-lookup, Graph-traversal)
// Backend mapping: semantic -> semantic-hybrid for enhanced keyword + relationship search
export type QueryMode = 'smart' | 'semantic' | 'entity-lookup' | 'graph-traversal';
export const QUERY_MODES: QueryMode[] = ['smart', 'semantic', 'entity-lookup', 'graph-traversal'];

// File types
export const SUPPORTED_FILE_TYPES = [
  '.txt', '.md', '.pdf', '.doc', '.docx', 
  '.csv', '.json', '.html', '.xml'
] as const;
