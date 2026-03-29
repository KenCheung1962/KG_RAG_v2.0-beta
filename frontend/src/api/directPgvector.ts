/**
 * Direct PGVector Stats Query
 * Queries the pgvector database directly since the API returns file-based stats
 */

import type { KGStats, DocStats } from './types';

// PGVector connection settings
const PGVECTOR_HOST = 'localhost';
const PGVECTOR_PORT = 5432;
const PGVECTOR_DB = 'kg_rag';
const PGVECTOR_USER = 'kg_rag';

/**
 * CURRENT STATS from pgvector database (kg_rag)
 * Updated: 2026-03-12
 * Source: docker exec kg_rag_postgres psql -U postgres -d kg_rag
 */
export const CURRENT_PGVECTOR_STATS = {
  entities: 8720,
  relationships: 21028,
  chunks: 23267,
  documents: 335  // COUNT(DISTINCT source) from chunks table
};

/**
 * Get current stats from pgvector
 * In production, this should query the actual database
 */
export async function getCurrentPGVectorStats(): Promise<{ kg: KGStats; docs: DocStats }> {
  // For now, return the manually updated stats
  // TODO: Implement actual SQL query via API endpoint
  
  return {
    kg: {
      entities: CURRENT_PGVECTOR_STATS.entities,
      relationships: CURRENT_PGVECTOR_STATS.relationships,
      chunks: CURRENT_PGVECTOR_STATS.chunks
    },
    docs: {
      total_documents: CURRENT_PGVECTOR_STATS.documents
    }
  };
}

/**
 * Update stats after manual verification
 */
export function updatePGVectorStats(stats: Partial<typeof CURRENT_PGVECTOR_STATS>): void {
  Object.assign(CURRENT_PGVECTOR_STATS, stats);
  console.log('PGVector stats updated:', CURRENT_PGVECTOR_STATS);
}

/**
 * Query stats from pgvector via fetch API
 * This would need a backend endpoint that queries pgvector
 */
export async function queryPGVectorStatsFromAPI(apiUrl: string): Promise<{ kg: KGStats; docs: DocStats } | null> {
  try {
    // Try to get stats from a custom endpoint
    const resp = await fetch(`${apiUrl}/pgvector-stats`, {
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (resp.ok) {
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
    }
    
    return null;
  } catch (error) {
    console.error('Failed to query pgvector stats:', error);
    return null;
  }
}
