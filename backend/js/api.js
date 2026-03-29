/**
 * API client for LightRAG WebUI
 * All HTTP requests go through here
 */

/**
 * Fetch knowledge graph statistics
 * @returns {Promise<Object>} KG stats (entities, relationships, chunks)
 */
async function fetchKGStats() {
    const resp = await fetch(`${API_URL}/api/v1/kg/stats?t=${Date.now()}`);
    return await resp.json();
}

/**
 * Fetch document statistics
 * @returns {Promise<Object>} Document stats
 */
async function fetchDocStats() {
    const resp = await fetch(`${API_URL}/api/v1/documents/stats?t=${Date.now()}`);
    return await resp.json();
}

/**
 * Fetch all stats and update UI
 */
async function fetchStats() {
    try {
        const kg = await fetchKGStats();
        document.getElementById('entities').textContent = kg.entities || kg.total_entities || 0;
        document.getElementById('relations').textContent = kg.relationships || kg.total_relations || 0;
        document.getElementById('chunks').textContent = kg.chunks || 0;
        
        const docs = await fetchDocStats();
        document.getElementById('docs').textContent = docs.total_documents || 0;
    } catch(e) {
        console.error('Stats error:', e);
    }
}

/**
 * Get existing document filenames from server
 * @returns {Promise<Set<string>>} Set of existing filenames
 */
async function getExistingDocs() {
    try {
        const resp = await fetch(`${API_URL}/api/v1/documents?limit=1000`);
        if (resp.ok) {
            const docs = await resp.json();
            return new Set(docs.map(d => d.filename || '').filter(f => f));
        }
    } catch(e) {
        console.log('Error getting existing docs:', e);
    }
    return new Set();
}

/**
 * Upload a document to the server
 * @param {File} file - File to upload
 * @returns {Promise<Object>} Upload result
 */
async function uploadDocument(file) {
    const content = await file.text();
    
    // Base64 encode
    let base64;
    try {
        base64 = btoa(unescape(encodeURIComponent(content)));
    } catch(e) {
        base64 = btoa(content);
    }
    
    const response = await fetch(`${API_URL}/api/v1/documents/upload/json`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            content: base64,
            id: file.name,
            content_type: 'text/plain'
        })
    });
    
    return { ok: response.ok, data: await response.json() };
}

/**
 * Check document indexing status
 * @param {string} docId - Document ID
 * @returns {Promise<Object>} Status object
 */
async function getDocumentStatus(docId) {
    const resp = await fetch(`${API_URL}/api/v1/documents/${docId}/status`);
    if (resp.ok) {
        return await resp.json();
    }
    return null;
}

/**
 * Send a chat query
 * @param {string} message - Query message
 * @param {string} mode - Query mode (hybrid/local/global)
 * @param {AbortSignal} signal - AbortController signal
 * @returns {Promise<Object>} Query result
 */
async function sendQuery(message, mode = 'hybrid', signal = null) {
    const options = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, mode })
    };
    if (signal) options.signal = signal;
    
    const resp = await fetch(`${API_URL}/api/v1/chat?_=${Date.now()}`, options);
    return await resp.json();
}

/**
 * Send a query with file context
 * @param {string} message - Query message
 * @param {string[]} filenames - Filenames to include
 * @param {AbortSignal} signal - AbortController signal
 * @returns {Promise<Object>} Query result
 */
async function sendQueryWithFiles(message, filenames, signal = null) {
    const options = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, filenames })
    };
    if (signal) options.signal = signal;
    
    const resp = await fetch(`${API_URL}/api/v1/chat/with-doc?_=${Date.now()}`, options);
    return await resp.json();
}

/**
 * Test API connection
 * @returns {Promise<Object>} Health check result
 */
async function testConnection() {
    const resp = await fetch(`${API_URL}/health`);
    return await resp.json();
}

/**
 * Clear all database data
 * @returns {Promise<void>}
 */
async function clearDatabase() {
    await fetch(`${API_URL}/api/v1/clear`, { method: 'DELETE' });
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        fetchKGStats, fetchDocStats, fetchStats, getExistingDocs,
        uploadDocument, getDocumentStatus, sendQuery, sendQueryWithFiles,
        testConnection, clearDatabase
    };
}
