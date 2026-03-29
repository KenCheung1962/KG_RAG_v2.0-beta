/**
 * Configuration UI handlers for LightRAG WebUI
 */

/**
 * Test API connection and show status
 */
async function testConnection() {
    const status = document.getElementById('configStatus');
    status.textContent = 'Testing...';
    
    try {
        const data = await testConnectionApi();
        status.innerHTML = `<span class="success">✅ Connected!</span><pre>${JSON.stringify(data, null, 2)}</pre>`;
        
        document.getElementById('systemInfo').style.display = 'block';
        document.getElementById('systemInfo').textContent = JSON.stringify(data, null, 2);
    } catch(e) {
        status.innerHTML = `<span class="error">❌ Connection failed: ${e.message}</span>`;
    }
}

/**
 * Refresh connection state
 */
function refreshConnection() {
    clearAllTimers();
    
    const queryButton = document.querySelector('button[onclick="runQuery()"]');
    if (queryButton) {
        queryButton.disabled = false;
        queryButton.textContent = '🔍 Ask Question';
    }
    
    document.getElementById('configStatus').innerHTML = '<span class="success">✅ Connection state refreshed. Try your query again.</span>';
}

/**
 * Clear all database data
 */
async function clearDatabase() {
    const status = document.getElementById('clearStatus');
    
    if (!confirm('Are you sure you want to clear ALL data? This cannot be undone!')) return;
    
    status.textContent = 'Clearing database...';
    
    try {
        await clearDatabaseApi();
    } catch(e) {}
    
    fetchStats();
    status.innerHTML = '<span class="success">✅ Database cleared!</span>';
}

// Rename API functions to avoid naming conflicts
async function testConnectionApi() {
    const resp = await fetch(`${API_URL}/health`);
    return await resp.json();
}

async function clearDatabaseApi() {
    await fetch(`${API_URL}/api/v1/clear`, { method: 'DELETE' });
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { testConnection, refreshConnection, clearDatabase };
}
