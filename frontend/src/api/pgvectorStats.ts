/**
 * PGVector Stats API
 * Fetches stats from pgvector PostgreSQL database
 * 
 * Priority:
 * 1. Port 8002 - Native PGVector API (preferred)
 * 2. Port 8012 - Docker proxy (fallback)
 * 3. Hardcoded values (last resort)
 */

import type { KGStats, DocStats } from './types';

// API endpoints
const PGVECTOR_API_URL = 'http://localhost:8002';  // Native pgvector API
const PROXY_URL = 'http://localhost:8012';          // Docker proxy

// Fallback stats (verified from database)
// Updated: 2026-03-28 - Current actual stats from production database
const FALLBACK_STATS = {
  entities: 45887,
  relationships: 116305,
  chunks: 368536,
  documents: 1982
};

/**
 * Try to fetch stats from port 8002 (native pgvector API)
 */
async function fetchFromNativeAPI(): Promise<{ kg: KGStats; docs: DocStats } | null> {
  try {
    const resp = await fetch(`${PGVECTOR_API_URL}/health`, {
      signal: AbortSignal.timeout(30000)  // 30 seconds timeout for health check
    });
    
    if (!resp.ok) return null;
    
    const data = await resp.json();
    
    return {
      kg: {
        entities: data.entities_count ?? 0,
        relationships: data.relationships_count ?? 0,
        chunks: data.chunks_count ?? 0
      },
      docs: {
        total_documents: data.documents_count ?? 0
      }
    };
  } catch (error) {
    console.log('Port 8002 API not available:', error instanceof Error ? error.message : error);
    return null;
  }
}

/**
 * Try to fetch stats from port 8012 (docker proxy)
 */
async function fetchFromProxy(): Promise<{ kg: KGStats; docs: DocStats } | null> {
  try {
    const resp = await fetch(`${PROXY_URL}/stats`, {
      signal: AbortSignal.timeout(30000)  // 30 seconds timeout for proxy
    });
    
    if (!resp.ok) return null;
    
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
    console.log('Port 8012 proxy not available');
    return null;
  }
}

/**
 * Get stats with automatic fallback
 * Priority: Port 8002 → Port 8012 → Hardcoded
 */
export async function getPGVectorStats(): Promise<{ kg: KGStats; docs: DocStats; source: string }> {
  // Try port 8002 first (native API)
  const nativeStats = await fetchFromNativeAPI();
  if (nativeStats) {
    console.log('✅ Stats from port 8002:', {
      docs: nativeStats.docs.total_documents,
      entities: nativeStats.kg.entities,
      rels: nativeStats.kg.relationships,
      chunks: nativeStats.kg.chunks
    });
    return { ...nativeStats, source: 'pgvector-api:8002' };
  }
  
  // Try port 8012 (docker proxy)
  const proxyStats = await fetchFromProxy();
  if (proxyStats) {
    console.log('✅ Stats from port 8012:', {
      docs: proxyStats.docs.total_documents,
      entities: proxyStats.kg.entities,
      rels: proxyStats.kg.relationships,
      chunks: proxyStats.kg.chunks
    });
    return { ...proxyStats, source: 'proxy:8012' };
  }
  
  // Fallback to hardcoded
  console.warn('⚠️ Using fallback hardcoded stats - API may be down');
  return {
    kg: {
      entities: FALLBACK_STATS.entities,
      relationships: FALLBACK_STATS.relationships,
      chunks: FALLBACK_STATS.chunks
    },
    docs: {
      total_documents: FALLBACK_STATS.documents
    },
    source: 'fallback'
  };
}
