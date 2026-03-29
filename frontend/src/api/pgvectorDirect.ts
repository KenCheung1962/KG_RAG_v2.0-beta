/**
 * Direct PGVector Stats Query
 * Fetches real-time stats from pgvector PostgreSQL database
 */

import type { KGStats, DocStats } from './types';

// PGVector proxy endpoint (proxied through Vite dev server)
const PGVECTOR_PROXY_URL = '/pgvector';

/**
 * Fetch live stats from pgvector via proxy
 */
export async function fetchLivePGVectorStats(): Promise<{ kg: KGStats; docs: DocStats } | null> {
  try {
    const resp = await fetch(`${PGVECTOR_PROXY_URL}/stats`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!resp.ok) {
      console.error('PGVector proxy error:', resp.status);
      return null;
    }
    
    const data = await resp.json();
    
    return {
      kg: {
        entities: data.entities ?? 0,
        relationships: data.relationships ?? 0,
        chunks: data.chunks ?? 0
      },
      docs: {
        total_documents: data.documents ?? 0
      }
    };
  } catch (error) {
    console.error('Failed to fetch live pgvector stats:', error);
    return null;
  }
}

/**
 * Check if pgvector proxy is available
 */
export async function isPGVectorProxyAvailable(): Promise<boolean> {
  try {
    const resp = await fetch(`${PGVECTOR_PROXY_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(2000)
    });
    return resp.ok;
  } catch {
    return false;
  }
}

/**
 * Get stats with fallback to hardcoded values
 */
export async function getPGVectorStatsWithFallback(): Promise<{ kg: KGStats; docs: DocStats }> {
  // Try live stats first
  const liveStats = await fetchLivePGVectorStats();
  if (liveStats) {
    console.log('Using live pgvector stats:', liveStats);
    return liveStats;
  }
  
  // Fallback to hardcoded stats
  console.log('Using fallback pgvector stats');
  return {
    kg: {
      entities: 8720,
      relationships: 21028,
      chunks: 23267
    },
    docs: {
      total_documents: 335
    }
  };
}
