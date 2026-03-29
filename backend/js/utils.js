/**
 * Utility functions for LightRAG WebUI
 */

// State management
let statsInterval = null;
let activeRequestController = null;

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML string
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show a tab by ID
 * @param {string} tabId - Tab ID to show
 * @param {Event} event - Click event
 */
function showTab(tabId, event) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    (event?.target || document.querySelector(`[onclick*="showTab('${tabId}')"]`)).classList.add('active');
    document.getElementById(tabId).classList.add('active');
}

/**
 * Set upload method (files vs folder)
 * @param {string} method - 'files' or 'folder'
 */
function setMethod(method) {
    document.getElementById('methodFiles').style.display = method === 'files' ? 'block' : 'none';
    document.getElementById('methodFolder').style.display = method === 'folder' ? 'block' : 'none';
    document.getElementById('btnMethodFiles').className = method === 'files' ? 'active' : 'inactive';
    document.getElementById('btnMethodFolder').className = method === 'folder' ? 'active' : 'inactive';
}

/**
 * Initialize auto-refresh for stats (guarded to prevent multiple intervals)
 */
function initStatsAutoRefresh() {
    if (!statsInterval) {
        statsInterval = setInterval(fetchStats, STATS_REFRESH_INTERVAL);
    }
}

/**
 * Clear all pending timers and requests
 */
function clearAllTimers() {
    if (activeRequestController) {
        activeRequestController.abort();
        activeRequestController = null;
    }
    // Clear timeouts (best effort)
    const maxTimeoutId = setTimeout(() => {}, 0);
    for (let i = 0; i < maxTimeoutId; i++) {
        clearTimeout(i);
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        statsInterval, activeRequestController,
        escapeHtml, showTab, setMethod, initStatsAutoRefresh, clearAllTimers
    };
}
