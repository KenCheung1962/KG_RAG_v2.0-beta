/**
 * Database Management Panel Component
 * Integrates backup/cleanup/restore functionality into the WebUI
 */

import {
  getDatabaseStats,
  listBackups,
  createBackup,
  cleanupDatabase,
  restoreBackup,
  deleteBackup,
  checkDBManagementAPI,
  getUploadFailures,
  type DatabaseStats,
  type BackupInfo,
  type UploadFailure,
  type UploadSuccess
} from '@/api/dbManagement';
import { getElement, setVisible, setDisabled } from '@/utils/dom';
import { escapeHtml } from '@/utils/helpers';

let _stats: DatabaseStats | null = null;
let _backups: BackupInfo[] = [];
let _apiAvailable = false;
let _refreshInterval: number | null = null;
let _uploadFailures: UploadFailure[] = [];
let _uploadSuccesses: UploadSuccess[] = [];

/**
 * Initialize the database panel
 */
export function initDatabasePanel(): void {
  // Set up event delegation for backup list (must be done before rendering)
  setupBackupListDelegation();
  
  // Check if API is available
  checkAPIAndInit();
  
  // Set up event listeners
  setupEventListeners();
  
  // Start periodic refresh
  startRefreshInterval();
}

/**
 * Check API availability and initialize
 */
async function checkAPIAndInit(): Promise<void> {
  _apiAvailable = await checkDBManagementAPI();
  updatePanelVisibility();
  
  if (_apiAvailable) {
    await refreshStats();
    await refreshBackups();
    await refreshUploadHistory();
  }
}

/**
 * Update panel visibility based on API availability
 */
function updatePanelVisibility(): void {
  const panel = getElement('databasePanel');
  const warning = getElement('dbApiWarning');
  
  if (panel) {
    panel.style.opacity = _apiAvailable ? '1' : '0.5';
  }
  
  if (warning) {
    setVisible('dbApiWarning', !_apiAvailable);
    if (!_apiAvailable) {
      warning.innerHTML = `
        <div class="warning-box">
          <strong>⚠️ Database Management API Not Running</strong><br>
          Start it with: <code>node scripts/db-management-api.cjs</code><br>
          Or: <code>npm run db:api</code>
        </div>
      `;
    }
  }
}

/**
 * Set up event listeners
 */
function setupEventListeners(): void {
  // Backup button
  getElement('btnCreateBackup')?.addEventListener('click', handleCreateBackup);
  
  // Cleanup button
  getElement('btnCleanupDB')?.addEventListener('click', handleCleanupDB);
  
  // Refresh button
  getElement('btnRefreshDBStats')?.addEventListener('click', () => {
    refreshStats();
    refreshBackups();
  });
  
  // Upload history refresh button
  getElement('btnRefreshUploadHistory')?.addEventListener('click', refreshUploadHistory);
}

/**
 * Start periodic refresh interval
 */
function startRefreshInterval(): void {
  if (_refreshInterval) {
    clearInterval(_refreshInterval);
  }
  
  _refreshInterval = window.setInterval(() => {
    if (_apiAvailable) {
      refreshStats();
    }
  }, 30000); // Refresh every 30 seconds
}

/**
 * Refresh database stats
 */
async function refreshStats(): Promise<void> {
  if (!_apiAvailable) return;
  
  try {
    _stats = await getDatabaseStats();
    renderStats();
  } catch (error) {
    console.error('Failed to refresh stats:', error);
    _apiAvailable = false;
    updatePanelVisibility();
  }
}

/**
 * Refresh backup list
 */
async function refreshBackups(): Promise<void> {
  if (!_apiAvailable) return;
  
  try {
    _backups = await listBackups();
    renderBackups();
  } catch (error) {
    console.error('Failed to refresh backups:', error);
  }
}

/**
 * Render stats to the UI
 */
function renderStats(): void {
  if (!_stats) return;
  
  const statsHtml = `
    <div class="db-stats-grid">
      <div class="db-stat-item">
        <span class="db-stat-value">${_stats.counts.documents?.toLocaleString() || 0}</span>
        <span class="db-stat-label">Documents</span>
      </div>
      <div class="db-stat-item">
        <span class="db-stat-value">${_stats.counts.chunks?.toLocaleString() || 0}</span>
        <span class="db-stat-label">Chunks</span>
      </div>
      <div class="db-stat-item">
        <span class="db-stat-value">${_stats.counts.entities?.toLocaleString() || 0}</span>
        <span class="db-stat-label">Entities</span>
      </div>
      <div class="db-stat-item">
        <span class="db-stat-value">${_stats.counts.relationships?.toLocaleString() || 0}</span>
        <span class="db-stat-label">Relationships</span>
      </div>
    </div>
    <div class="db-size-info">
      <strong>Total Database Size:</strong> ${_stats.totalSizeFormatted}
      <span class="db-last-updated">Updated: ${new Date(_stats.timestamp).toLocaleTimeString()}</span>
    </div>
  `;
  
  const container = getElement('dbStatsContainer');
  if (container) {
    container.innerHTML = statsHtml;
  }
}

/**
 * Setup event delegation for backup list
 * This is called once during initialization
 */
function setupBackupListDelegation(): void {
  const container = getElement('dbBackupsContainer');
  if (!container) return;
  
  // Remove any existing listeners to prevent duplicates
  container.removeEventListener('click', handleBackupListClick);
  
  // Add single event listener for the entire container
  container.addEventListener('click', handleBackupListClick);
}

/**
 * Handle clicks on backup list using event delegation
 */
function handleBackupListClick(e: Event): void {
  const target = e.target as HTMLElement;
  
  // Find the clicked button
  const restoreBtn = target.closest('.btn-restore');
  const deleteBtn = target.closest('.btn-delete');
  
  if (!restoreBtn && !deleteBtn) return;
  
  // Find the parent backup item to get the backup name
  const backupItem = target.closest('.backup-item');
  if (!backupItem) return;
  
  const backupName = backupItem.getAttribute('data-backup-name');
  if (!backupName) return;
  
  // Handle restore
  if (restoreBtn) {
    handleRestoreBackup(backupName);
    return;
  }
  
  // Handle delete
  if (deleteBtn) {
    // Prevent double-clicks
    if ((deleteBtn as HTMLButtonElement).disabled) return;
    handleDeleteBackup(backupName, deleteBtn as HTMLButtonElement);
  }
}

/**
 * Render backup list
 */
function renderBackups(): void {
  const container = getElement('dbBackupsContainer');
  if (!container) return;
  
  if (_backups.length === 0) {
    container.innerHTML = '<p class="empty-text">No backups yet. Create your first backup below.</p>';
    return;
  }
  
  const listHtml = _backups.slice(0, 5).map((backup) => {
    const date = new Date(backup.created).toLocaleString();
    const docs = backup.metadata?.stats?.documents || '?';
    const isOutdated = docs === '?' || backup.size === '160 B'; // Mark old/failed backups
    // Use a data attribute with the raw name for reliable retrieval
    return `
      <div class="backup-item ${isOutdated ? 'backup-outdated' : ''}" data-backup-name="${escapeHtml(backup.name)}">
        <div class="backup-info">
          <div class="backup-name">${escapeHtml(backup.name)} ${isOutdated ? '<span class="outdated-badge">outdated</span>' : ''}</div>
          <div class="backup-meta">
            ${date} • ${backup.size} • ${docs} docs
          </div>
        </div>
        <div class="backup-actions">
          <button class="btn-small btn-restore" title="Restore (metadata only)">
            ↩️ Restore
          </button>
          <button class="btn-small btn-delete" title="Delete this backup">
            🗑️ Delete
          </button>
        </div>
      </div>
    `;
  }).join('');
  
  container.innerHTML = `
    <div class="backup-list">
      ${listHtml}
    </div>
    ${_backups.length > 5 ? `<p class="backup-more">+ ${_backups.length - 5} more backups</p>` : ''}
  `;
}

/**
 * Handle create backup
 */
async function handleCreateBackup(): Promise<void> {
  const btn = getElement('btnCreateBackup');
  if (!btn) return;
  
  const originalText = btn.innerHTML;
  btn.innerHTML = '⏳ Creating...';
  setDisabled('btnCreateBackup', true);
  
  try {
    const result = await createBackup();
    showNotification(`✅ Backup created: ${result.result.backupPath}`, 'success');
    await refreshBackups();
  } catch (error) {
    showNotification(`❌ Backup failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
  } finally {
    btn.innerHTML = originalText;
    setDisabled('btnCreateBackup', false);
  }
}

/**
 * Handle cleanup database
 */
async function handleCleanupDB(): Promise<void> {
  const confirmed = confirm(
    '⚠️ WARNING: This will DELETE all data in the database!\n\n' +
    'Make sure you have created a backup first.\n\n' +
    'This action cannot be undone.\n\n' +
    'Are you sure you want to continue?'
  );
  
  if (!confirmed) return;
  
  const btn = getElement('btnCleanupDB');
  if (!btn) return;
  
  const originalText = btn.innerHTML;
  btn.innerHTML = '⏳ Cleaning...';
  setDisabled('btnCleanupDB', true);
  
  try {
    await cleanupDatabase();
    showNotification('✅ Database cleaned successfully', 'success');
    await refreshStats();
    await refreshBackups();
    
    // Clear upload tracker in browser
    localStorage.removeItem('lightrag_upload_tracker');
    localStorage.removeItem('lightrag_uploaded_files');
    showNotification('📝 Upload tracker history cleared', 'info');
  } catch (error) {
    showNotification(`❌ Cleanup failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
  } finally {
    btn.innerHTML = originalText;
    setDisabled('btnCleanupDB', false);
  }
}

/**
 * Handle restore backup
 */
async function handleRestoreBackup(backupName: string): Promise<void> {
  const confirmed = confirm(
    `⚠️ Restore from "${backupName}"?\n\n` +
    'This will OVERWRITE current database metadata.\n\n' +
    'Note: You will need to re-upload the original files to restore full content.\n\n' +
    'Continue?'
  );
  
  if (!confirmed) return;
  
  try {
    const result = await restoreBackup(backupName);
    showNotification(`✅ ${result.message}`, 'success');
    await refreshStats();
  } catch (error) {
    showNotification(`❌ Restore failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
  }
}

/**
 * Handle delete backup
 */
async function handleDeleteBackup(backupName: string, clickedBtn?: HTMLButtonElement): Promise<void> {
  console.log('Delete requested for backup:', backupName);
  
  const confirmed = confirm(
    `🗑️ Delete backup "${backupName}"?\n\n` +
    'This backup will be permanently removed.\n\n' +
    'This action cannot be undone!'
  );
  
  if (!confirmed) return;
  
  // Disable the clicked button immediately
  if (clickedBtn) {
    clickedBtn.disabled = true;
    clickedBtn.textContent = '⏳...';
  }
  
  // Disable all other delete buttons during deletion to prevent double-clicks
  const allDeleteBtns = document.querySelectorAll('.btn-delete');
  allDeleteBtns.forEach(btn => {
    if (btn !== clickedBtn) {
      (btn as HTMLButtonElement).disabled = true;
    }
  });
  
  try {
    console.log('Calling deleteBackup API for:', backupName);
    const result = await deleteBackup(backupName);
    console.log('Delete result:', result);
    showNotification(`✅ ${result.message}`, 'success');
    
    // Remove the deleted backup from the local array immediately for instant UI update
    _backups = _backups.filter(b => b.name !== backupName);
    renderBackups(); // Re-render with updated list
    
    // Then refresh from server to ensure sync
    await refreshBackups();
  } catch (error) {
    console.error('Delete error:', error);
    showNotification(`❌ Delete failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    // Re-enable all buttons on error
    allDeleteBtns.forEach(btn => {
      (btn as HTMLButtonElement).disabled = false;
      if (btn === clickedBtn) {
        btn.textContent = '🗑️ Delete';
      }
    });
  }
}

/**
 * Fetch and render upload history
 */
async function refreshUploadHistory(): Promise<void> {
  try {
    const data = await getUploadFailures();
    _uploadFailures = data.failures;
    _uploadSuccesses = data.successes;
    renderUploadHistory();
  } catch (error) {
    console.error('Failed to fetch upload history:', error);
    const container = getElement('uploadHistoryContainer');
    if (container) {
      container.innerHTML = '<p class="error-text">Failed to load upload history</p>';
    }
  }
}

/**
 * Render upload history
 */
function renderUploadHistory(): void {
  const container = getElement('uploadHistoryContainer');
  if (!container) return;
  
  const failureCount = _uploadFailures.length;
  const successCount = _uploadSuccesses.length;
  
  let html = '';
  
  // Show failures first (if any)
  if (failureCount > 0) {
    html += `<div class="upload-failures-section">`;
    html += `<h4 class="upload-section-title error">❌ Recent Failures (${failureCount})</h4>`;
    html += `<div class="upload-list">`;
    _uploadFailures.slice(-10).reverse().forEach(failure => {
      const shortError = failure.error.length > 60 ? failure.error.substring(0, 60) + '...' : failure.error;
      html += `
        <div class="upload-item failure">
          <div class="upload-filename" title="${escapeHtml(failure.filename)}">${escapeHtml(failure.filename)}</div>
          <div class="upload-meta">
            <span class="upload-error">${escapeHtml(shortError)}</span>
            <span class="upload-time">${new Date(failure.timestamp).toLocaleString()}</span>
          </div>
        </div>
      `;
    });
    html += `</div></div>`;
  }
  
  // Show recent successes
  if (successCount > 0) {
    html += `<div class="upload-successes-section">`;
    html += `<h4 class="upload-section-title success">✅ Recent Successes (${successCount} total)</h4>`;
    html += `<div class="upload-list">`;
    _uploadSuccesses.slice(-5).reverse().forEach(success => {
      html += `
        <div class="upload-item success">
          <div class="upload-filename" title="${escapeHtml(success.filename)}">${escapeHtml(success.filename)}</div>
          <div class="upload-meta">
            <span class="upload-chunks">${success.chunks} chunks</span>
            <span class="upload-time">${new Date(success.timestamp).toLocaleString()}</span>
          </div>
        </div>
      `;
    });
    html += `</div></div>`;
  }
  
  if (failureCount === 0 && successCount === 0) {
    html = '<p class="empty-text">No upload history available yet. Upload some files to see the history.</p>';
  }
  
  container.innerHTML = html;
}

/**
 * Show notification
 */
export function showNotification(message: string, type: 'success' | 'error' | 'info' = 'info'): void {
  const container = getElement('dbNotification');
  if (!container) return;
  
  const className = type === 'success' ? 'notification-success' : 
                    type === 'error' ? 'notification-error' : 'notification-info';
  
  container.innerHTML = `<div class="notification ${className}">${escapeHtml(message)}</div>`;
  
  setTimeout(() => {
    container.innerHTML = '';
  }, 5000);
}

/**
 * Get HTML for database panel
 */
export function getDatabasePanelHTML(): string {
  return `
    <div id="databasePanel" class="database-panel card">
      <h2>🗄️ Database Management</h2>
      
      <div id="dbApiWarning"></div>
      
      <div class="db-section">
        <h3>📊 Current Statistics</h3>
        <div id="dbStatsContainer">
          <p class="loading-text">Loading stats...</p>
        </div>
      </div>
      
      <div class="db-section">
        <h3>💾 Backups</h3>
        <div id="dbBackupsContainer">
          <p class="loading-text">Loading backups...</p>
        </div>
        <div class="db-actions">
          <button id="btnCreateBackup" class="btn-primary">
            💾 Create Backup
          </button>
          <button id="btnRefreshDBStats" class="btn-secondary">
            🔄 Refresh
          </button>
        </div>
      </div>
      
      <div class="db-section">
        <h3>📋 Upload History</h3>
        <div id="uploadHistoryContainer">
          <p class="loading-text">Loading upload history...</p>
        </div>
        <div class="db-actions">
          <button id="btnRefreshUploadHistory" class="btn-secondary">
            🔄 Refresh
          </button>
        </div>
      </div>
      
      <div class="db-section db-danger-zone">
        <h3>⚠️ Danger Zone</h3>
        <p class="hint-text">
          Clean up the database to free space. <strong>Create a backup first!</strong>
        </p>
        <button id="btnCleanupDB" class="btn-danger">
          🗑️ Clean Database
        </button>
      </div>
      
      <div id="dbNotification"></div>
    </div>
  `;
}

/**
 * Cleanup function
 */
export function cleanupDatabasePanel(): void {
  if (_refreshInterval) {
    clearInterval(_refreshInterval);
    _refreshInterval = null;
  }
}
