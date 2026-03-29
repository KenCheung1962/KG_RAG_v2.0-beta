/**
 * Configuration constants for LightRAG WebUI
 */

// API Configuration
const API_URL = 'http://localhost:8002';
const DEFAULT_TIMEOUT = 300000; // 5 minutes for queries
const STATS_REFRESH_INTERVAL = 10000; // 10 seconds
const MAX_INDEXING_POLLS = 30; // Maximum polling attempts for indexing

// Export for module systems (if needed)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { API_URL, DEFAULT_TIMEOUT, STATS_REFRESH_INTERVAL, MAX_INDEXING_POLLS };
}
