/**
 * Main initialization for LightRAG WebUI
 * Loads all modules and sets up event handlers
 */

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('🧠 LightRAG WebUI initializing...');
    
    // Initial stats fetch
    fetchStats();
    
    // Start auto-refresh (guarded)
    initStatsAutoRefresh();
    
    console.log('✅ LightRAG WebUI ready');
});

// Global error handler
window.onerror = (msg, url, line) => {
    console.error('Global error:', msg, 'at', url, 'line', line);
    return false;
};

// Handle page unload to clean up
window.addEventListener('beforeunload', () => {
    if (activeRequestController) {
        activeRequestController.abort();
    }
    if (statsInterval) {
        clearInterval(statsInterval);
    }
});
