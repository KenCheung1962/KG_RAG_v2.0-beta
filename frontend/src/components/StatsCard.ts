/**
 * Stats dashboard component
 */

import { getElement, setText } from '@/utils/dom';
import { fetchKGStats, fetchDocStats } from '@/api';
import { setKGStats, setDocStats } from '@/stores/appStore';
import { initLoadingStyles, showStatsSkeleton } from './LoadingOverlay';
import { getPGVectorStats } from '@/api/pgvectorStats';
import type { KGStats, DocStats } from '@/api';

/**
 * Initialize stats card
 */
export function initStatsCard(): void {
  // Initialize loading styles
  initLoadingStyles();
  
  // Show skeleton while loading
  showStatsSkeleton();
  
  const refreshBtn = getElement('refreshStatsBtn');
  refreshBtn?.addEventListener('click', updateStats);
  
  // Initial load
  updateStats();
}

/**
 * Update stats from pgvector database
 * Priority: Port 8002 → Port 8012 → Fallback
 */
export async function updateStats(): Promise<void> {
  try {
    console.log('[Stats] Fetching pgvector stats...');
    
    // Get stats with automatic fallback
    const { kg, docs, source } = await getPGVectorStats();
    
    console.log(`[Stats] From ${source}:`, { 
      docs: docs?.total_documents ?? 0, 
      entities: kg?.entities ?? 0,
      relations: kg?.relationships ?? 0,
      chunks: kg?.chunks ?? 0
    });
    
    setKGStats(kg);
    setDocStats(docs);
    
    renderStats(kg, docs);
  } catch (error) {
    console.error('[Stats] Failed to fetch:', error);
    // Show error state
    setText('statDocs', '❌');
    setText('statEntities', '❌');
    setText('statRelations', '❌');
    setText('statChunks', '❌');
  }
}

/**
 * Render stats to DOM
 */
function renderStats(kgStats: KGStats, docStats: DocStats): void {
  const docs = docStats?.total_documents ?? 0;
  const entities = kgStats?.entities ?? kgStats?.total_entities ?? 0;
  const relations = kgStats?.relationships ?? kgStats?.total_relations ?? 0;
  const chunks = kgStats?.chunks ?? 0;
  
  console.log('Rendering stats:', { docs, entities, relations, chunks });
  
  setText('statDocs', String(docs));
  setText('statEntities', String(entities));
  setText('statRelations', String(relations));
  setText('statChunks', String(chunks));
}

/**
 * Get stats HTML template
 */
export function getStatsHTML(): string {
  return `
    <div class="card" style="padding: 10px;">
      <h3 style="margin: 0 0 8px 0; font-size: 13px;">📊 Knowledge Graph Stats</h3>
      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-number" id="statDocs">0</div>
          <div class="stat-label">Docs</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statEntities">0</div>
          <div class="stat-label">Entities</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statRelations">0</div>
          <div class="stat-label">Rels</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statChunks">0</div>
          <div class="stat-label">Chunks</div>
        </div>
      </div>
      <button id="refreshStatsBtn" class="btn" style="margin-top: 8px; padding: 4px 10px; font-size: 11px;">🔄 Refresh</button>
    </div>
  `;
}
