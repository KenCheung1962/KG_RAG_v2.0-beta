/**
 * Loading Overlay Component
 * Provides full-page and inline loading states with skeleton loaders
 */

import { getElement, setHTML } from '@/utils/dom';

/**
 * CSS for skeleton loading animations
 */
const SKELETON_STYLES = `
  .skeleton {
    background: linear-gradient(90deg, 
      rgba(255,255,255,0.05) 25%, 
      rgba(255,255,255,0.1) 50%, 
      rgba(255,255,255,0.05) 75%
    );
    background-size: 200% 100%;
    animation: skeleton-shimmer 1.5s ease-in-out infinite;
    border-radius: var(--border-radius-sm);
  }
  
  @keyframes skeleton-shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }
  
  .skeleton-text {
    height: 16px;
    width: 60%;
    margin: 8px 0;
  }
  
  .skeleton-text-sm {
    height: 12px;
    width: 40%;
    margin: 6px 0;
  }
  
  .skeleton-number {
    height: 32px;
    width: 50px;
    margin: 0 auto 8px;
  }
  
  .skeleton-box {
    height: 80px;
    width: 100%;
  }
  
  .skeleton-btn {
    height: 40px;
    width: 120px;
    margin-top: 15px;
  }
  
  .loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(26, 26, 46, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    backdrop-filter: blur(4px);
  }
  
  .loading-spinner {
    width: 50px;
    height: 50px;
    border: 4px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .loading-message {
    color: var(--text-primary);
    margin-top: 15px;
    font-size: 16px;
  }
`;

/**
 * Inject skeleton styles into the document
 */
export function initLoadingStyles(): void {
  if (document.getElementById('loading-styles')) return;
  
  const style = document.createElement('style');
  style.id = 'loading-styles';
  style.textContent = SKELETON_STYLES;
  document.head.appendChild(style);
}

/**
 * Show full-page loading overlay
 */
export function showLoadingOverlay(message = 'Loading...'): void {
  initLoadingStyles();
  
  let overlay = getElement('loading-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'loading-overlay';
    document.body.appendChild(overlay);
  }
  
  overlay.innerHTML = `
    <div style="text-align: center;">
      <div class="loading-spinner"></div>
      <div class="loading-message">${message}</div>
    </div>
  `;
  overlay.style.display = 'flex';
}

/**
 * Hide full-page loading overlay
 */
export function hideLoadingOverlay(): void {
  const overlay = getElement('loading-overlay');
  if (overlay) {
    overlay.style.display = 'none';
  }
}

/**
 * Show skeleton loader for stats card
 */
export function showStatsSkeleton(): void {
  initLoadingStyles();
  
  const container = getElement('stats-container');
  if (!container) return;
  
  container.innerHTML = `
    <div class="card">
      <h2>📊 Knowledge Graph Stats</h2>
      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-number" id="statDocs"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Documents</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statEntities"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Entities</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statRelations"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Relationships</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statChunks"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Chunks</div>
        </div>
      </div>
      <button id="refreshStatsBtn" class="btn">🔄 Refresh Stats</button>
    </div>
  `;
}

/**
 * Render stats card skeleton as standalone HTML
 */
export function getStatsSkeletonHTML(): string {
  return `
    <div class="card">
      <h2>📊 Knowledge Graph Stats</h2>
      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-number" id="statDocs"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Documents</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statEntities"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Entities</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statRelations"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Relationships</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statChunks"><span class="skeleton skeleton-number"></span></div>
          <div class="stat-label">Chunks</div>
        </div>
      </div>
      <button id="refreshStatsBtn" class="btn">🔄 Refresh Stats</button>
    </div>
  `;
}

/**
 * Show skeleton for a generic box/panel
 */
export function showBoxSkeleton(selector: string): void {
  initLoadingStyles();
  
  const container = getElement(selector);
  if (!container) return;
  
  container.innerHTML = `<div class="skeleton skeleton-box"></div>`;
}

/**
 * Show skeleton for query results
 */
export function showQueryResultsSkeleton(): void {
  initLoadingStyles();
  
  const resultBox = getElement('queryResult');
  if (resultBox) {
    resultBox.innerHTML = `
      <div class="skeleton skeleton-text"></div>
      <div class="skeleton skeleton-text"></div>
      <div class="skeleton skeleton-text-sm"></div>
      <div class="skeleton skeleton-text-sm"></div>
    `;
  }
}

/**
 * Show skeleton for file list
 */
export function showFileListSkeleton(): void {
  initLoadingStyles();
  
  const container = getElement('fileList');
  if (container) {
    container.innerHTML = Array(3).fill(`
      <div class="skeleton skeleton-box" style="height: 50px; margin-bottom: 10px;"></div>
    `).join('');
  }
}
