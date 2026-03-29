/**
 * LightRAG WebUI - Main Entry Point
 */

import { STATS_REFRESH_INTERVAL } from '@/config';
import { initStatsCard, updateStats } from '@/components/StatsCard';
import { initProgressBar, isProgressActive } from '@/components/ProgressBar';
import {
  initIngestTab, initQueryTab, initQueryFileTab, initConfigTab,
  getIngestTabHTML, getQueryTabHTML, getQueryFileTabHTML, getConfigTabHTML
} from '@/components/tabs';
import { showTab, getElement } from '@/utils/dom';
import { setStatsInterval, cleanup } from '@/stores/appStore';
import { initErrorHandler } from '@/utils/errorHandler';
import { cleanupDatabasePanel } from '@/components/DatabasePanel';
import './styles.css';

/**
 * Update upload activity indicator based on state
 */
function updateUploadActivityIndicator(): void {
  const indicator = getElement('uploadActivityIndicator');
  if (!indicator) return;
  
  // Check if upload is in progress using the ProgressBar state
  const isUploading = isProgressActive();
  
  indicator.style.display = isUploading ? 'flex' : 'none';
}

// Poll for upload activity updates
let uploadActivityInterval: number | null = null;

function startUploadActivityMonitor(): void {
  if (uploadActivityInterval) return;
  uploadActivityInterval = window.setInterval(updateUploadActivityIndicator, 1000);
}

/**
 * Initialize the application
 */
function init(): void {
  console.log('🧠 LightRAG WebUI initializing...');
  
  // Initialize error handlers first
  initErrorHandler();
  
  // Render app structure
  renderApp();
  
  // Initialize components
  initStatsCard();
  initProgressBar('ingestProgress');
  
  // Initialize tabs
  initIngestTab();
  initQueryTab();
  initQueryFileTab();
  initConfigTab();
  
  // Initialize tab navigation
  initTabNavigation();
  
  // Initialize keyboard navigation
  initKeyboardNav();
  
  // Start auto-refresh
  setStatsInterval(setInterval(updateStats, STATS_REFRESH_INTERVAL));
  
  // Start upload activity monitor
  startUploadActivityMonitor();
  
  // Handle page unload
  window.addEventListener('beforeunload', () => {
    cleanup();
    cleanupDatabasePanel();
    if (uploadActivityInterval) {
      clearInterval(uploadActivityInterval);
    }
  });
  
  console.log('✅ LightRAG WebUI ready');
}

/**
 * Render the main app structure
 */
function renderApp(): void {
  const app = getElement('app');
  if (!app) return;
  
  app.innerHTML = `
    <div class="header">
      <div class="header-main">
        <h1>🧠 LightRAG Knowledge Graph</h1>
        <div id="uploadActivityIndicator" class="upload-activity" style="display: none;">
          <span class="upload-spinner">⏳</span>
          <span class="upload-text">Uploading...</span>
          <span class="upload-hint">(Query available but may be slower)</span>
        </div>
      </div>
      <p class="header-hint">
        💡 If queries fail, try refreshing the page (F5) or check browser console (F12).
      </p>
    </div>
    
    <div id="stats-container"></div>
    
    <nav class="tabs" role="tablist" aria-label="Main navigation">
      <button class="tab active" data-tab="query" role="tab" aria-selected="true" aria-controls="query" id="tab-query">🔍 Query</button>
      <button class="tab" data-tab="queryfile" role="tab" aria-selected="false" aria-controls="queryfile" id="tab-queryfile">🔗 Query+File</button>
      <button class="tab" data-tab="ingest" role="tab" aria-selected="false" aria-controls="ingest" id="tab-ingest">📥 Ingest</button>
      <button class="tab" data-tab="config" role="tab" aria-selected="false" aria-controls="config" id="tab-config">⚙️ Config</button>
    </nav>
    
    <main id="tab-content">
      ${getQueryTabHTML()}
      ${getQueryFileTabHTML()}
      ${getIngestTabHTML()}
      ${getConfigTabHTML()}
    </main>
  `;
  
  // Render stats card
  getElement('stats-container')!.innerHTML = `
    <div class="card">
      <h2>📊 Knowledge Graph Stats</h2>
      <div class="stats-grid">
        <div class="stat-box">
          <div class="stat-number" id="statDocs">0</div>
          <div class="stat-label">Documents</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statEntities">0</div>
          <div class="stat-label">Entities</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statRelations">0</div>
          <div class="stat-label">Relationships</div>
        </div>
        <div class="stat-box">
          <div class="stat-number" id="statChunks">0</div>
          <div class="stat-label">Chunks</div>
        </div>
      </div>
      <button id="refreshStatsBtn" class="btn" aria-label="Refresh statistics">🔄 Refresh Stats</button>
    </div>
  `;
}

/**
 * Initialize tab navigation
 */
function initTabNavigation(): void {
  const tabs = document.querySelectorAll('.tab');
  
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const tabId = tab.getAttribute('data-tab');
      if (tabId) {
        // Update tab buttons
        tabs.forEach(t => {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');
        
        // Show content
        showTab(tabId);
      }
    });
  });
}

/**
 * Initialize keyboard navigation
 */
function initKeyboardNav(): void {
  // Track keyboard mode
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      document.body.classList.add('keyboard-mode');
    }
    
    // Escape to close modals/alerts and blur focused elements
    if (e.key === 'Escape') {
      if (document.activeElement instanceof HTMLElement) {
        document.activeElement.blur();
      }
    }
    
    // Enter/Space to activate buttons when focused
    if ((e.key === 'Enter' || e.key === ' ') && document.activeElement?.matches('button, [role="button"]')) {
      // Don't interfere with native button behavior
      const target = document.activeElement as HTMLButtonElement;
      if (!target.disabled) {
        // Let default behavior work, but ensure visual feedback
        target.classList.add('keyboard-activated');
        setTimeout(() => target.classList.remove('keyboard-activated'), 150);
      }
    }
  });
  
  // Remove keyboard mode class on mouse use
  document.addEventListener('mousedown', () => {
    document.body.classList.remove('keyboard-mode');
  });
  
  // Add keyboard navigation to toast close buttons
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    if (target.classList.contains('toast-close')) {
      target.closest('.toast')?.remove();
    }
  }, { capture: true });
  
  console.log('✅ Keyboard navigation initialized');
}

// Start app when DOM is ready
document.addEventListener('DOMContentLoaded', init);
