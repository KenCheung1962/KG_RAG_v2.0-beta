/**
 * Query functionality for LightRAG WebUI
 */

/**
 * Run a simple query against the knowledge graph
 */
async function runQuery() {
    const query = document.getElementById('queryText').value;
    const mode = document.querySelector('input[name="queryMode"]:checked').value;
    const resultDiv = document.getElementById('queryResult');
    const answerText = document.getElementById('answerText');
    const sourcesText = document.getElementById('sourcesText');
    const queryButton = event.target;
    
    // Cancel any previous active request
    if (activeRequestController) {
        activeRequestController.abort();
        activeRequestController = null;
    }
    
    if (!query) {
        alert('Please enter a question');
        return;
    }
    
    const originalButtonText = queryButton.textContent;
    queryButton.disabled = true;
    queryButton.textContent = '⏳ Querying...';
    
    resultDiv.style.display = 'block';
    answerText.innerHTML = '<span class="spinner"></span> Querying... (This may take several minutes)';
    sourcesText.textContent = '';
    
    try {
        const controller = new AbortController();
        activeRequestController = controller;
        const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT);
        
        const result = await sendQuery(query, mode, controller.signal);
        clearTimeout(timeoutId);
        activeRequestController = null;
        
        const responseText = result.response || result.answer || JSON.stringify(result, null, 2);
        
        // Check if LLM timed out
        if (responseText.startsWith('Found') && responseText.includes('relevant chunks')) {
            formatTimeoutResponse(responseText, answerText);
        } else {
            answerText.textContent = responseText;
        }
        
        // Show sources
        if (result.sources || result.source_documents) {
            const sources = result.sources || result.source_documents;
            sourcesText.innerHTML = Array.isArray(sources) ? 
                sources.map(s => `<div class="source-item">${typeof s === 'string' ? s : JSON.stringify(s)}</div>`).join('') :
                `Found ${sources} sources`;
        } else {
            sourcesText.textContent = 'No sources available';
        }
    } catch(e) {
        handleQueryError(e, answerText, query, mode);
    } finally {
        queryButton.disabled = false;
        queryButton.textContent = originalButtonText;
        activeRequestController = null;
    }
}

/**
 * Format response when LLM times out
 * @param {string} responseText - Raw response
 * @param {HTMLElement} answerText - Answer container
 */
function formatTimeoutResponse(responseText, answerText) {
    const chunkMatch = responseText.match(/Found (\d+) relevant chunks/);
    const chunkCount = chunkMatch ? chunkMatch[1] : 'some';
    
    let formattedResponse = `## ⚠️ LLM Processing Timed Out\n\n`;
    formattedResponse += `The AI processing timed out after 25 seconds. Showing ${chunkCount} raw text chunks instead:\n\n---\n\n`;
    
    const chunksStart = responseText.indexOf('\n\n');
    if (chunksStart > 0) {
        const chunks = responseText.substring(chunksStart + 2);
        const chunkLines = chunks.split('\n\n');
        chunkLines.forEach((chunk, index) => {
            if (chunk.trim()) {
                formattedResponse += `### Chunk ${index + 1}\n\n${chunk}\n\n---\n\n`;
            }
        });
    } else {
        formattedResponse += responseText;
    }
    
    answerText.innerHTML = formattedResponse;
    
    // Add retry button
    const retryButton = document.createElement('button');
    retryButton.textContent = '🔄 Retry with Simpler Query';
    retryButton.style.marginTop = '10px';
    retryButton.onclick = () => {
        const currentQuery = document.getElementById('queryText').value;
        const simplerQuery = currentQuery.replace(/explain|in detail|with examples|comprehensive|detailed/gi, '').trim();
        if (simplerQuery && simplerQuery !== currentQuery) {
            document.getElementById('queryText').value = simplerQuery;
            runQuery();
        } else {
            alert('Try a simpler, more specific query. Example: "What is Bayesian probability?" instead of "Explain Bayesian probability in detail with examples"');
        }
    };
    answerText.appendChild(document.createElement('br'));
    answerText.appendChild(retryButton);
}

/**
 * Handle query errors with retry logic
 * @param {Error} e - Error object
 * @param {HTMLElement} answerText - Answer container
 * @param {string} query - Original query
 * @param {string} mode - Query mode
 */
async function handleQueryError(e, answerText, query, mode) {
    console.error("Query error:", e);
    
    let errorMsg = e.message || String(e);
    if (e.name === 'AbortError') {
        answerText.textContent = '⏰ Query timed out after 5 minutes. The API is taking too long to respond.';
    } else if (errorMsg.includes('Load failed') || errorMsg.includes('Failed to fetch') || errorMsg.includes('network')) {
        answerText.textContent = '⚠️ Network error detected. Retrying in 2 seconds...';
        
        try {
            await new Promise(resolve => setTimeout(resolve, 2000));
            const retryResult = await sendQuery(query, mode);
            answerText.textContent = retryResult.response || retryResult.answer || JSON.stringify(retryResult);
        } catch(retryErr) {
            answerText.textContent = `❌ Network error after retry: ${errorMsg}. Please refresh the page or use the "Refresh Connection" button.`;
        }
    } else {
        answerText.textContent = `❌ Error: ${errorMsg}`;
    }
}

/**
 * Set test query text
 * @param {string} q - Query text
 */
function testQuery(q) {
    document.getElementById('queryText').value = q;
    runQuery();
}

/**
 * Query database only (no file upload)
 * @param {string} queryText - Query text
 */
async function queryDatabaseOnly(queryText) {
    const resultDiv = document.getElementById('queryFileResult');
    const answerDiv = document.getElementById('queryFileAnswer');
    
    resultDiv.style.display = 'block';
    answerDiv.innerHTML = '<span class="spinner"></span> Searching database (may take ~30 seconds for LLM)...';
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);
    
    try {
        const result = await sendQuery(queryText, 'hybrid', controller.signal);
        clearTimeout(timeoutId);
        answerDiv.textContent = result.response || result.answer || JSON.stringify(result);
    } catch(e) {
        if (e.name === 'AbortError') {
            answerDiv.textContent = '⏰ Query timed out. The LLM is taking too long. Please try a simpler query.';
        } else {
            answerDiv.textContent = `❌ Error: ${e.message}`;
        }
    }
}

/**
 * Run query with file context
 */
async function runQueryWithFile() {
    const queryText = document.getElementById('queryFileText').value;
    const resultDiv = document.getElementById('queryFileResult');
    const answerDiv = document.getElementById('queryFileAnswer');
    let files = selectedQueryFiles;
    
    if (!files.length || !queryText) {
        alert('Please upload file(s) and enter a question');
        return;
    }
    
    resultDiv.style.display = 'block';
    answerDiv.innerHTML = '<span class="spinner"></span> Processing... (This may take several minutes)';
    
    const existingDocs = await getExistingDocs();
    let { duplicates, newFiles } = filterDuplicates(files, existingDocs);
    
    // Handle duplicates
    if (duplicates.length > 0) {
        if (files.length === 1) {
            const action = confirm(`File "${escapeHtml(duplicates[0])}" already exists. Click OK to overwrite, Cancel to skip.`);
            if (!action) {
                answerDiv.textContent = '⏭️ Skipped file. Searching database...';
                selectedQueryFiles = [];
                await queryDatabaseOnly(queryText);
                return;
            }
        } else {
            const dupFileList = escapeHtml(duplicates.join(', '));
            const newFileList = newFiles.map(f => escapeHtml(f.name)).join(', ');
            let action = true;
            if (newFiles.length > 0) {
                action = confirm(`Found ${duplicates.length} existing file(s): ${dupFileList}\n\nNew files to upload: ${newFileList}\n\nClick OK to upload all (overwrite duplicates), Cancel to skip duplicates only.`);
            } else {
                action = confirm(`All ${duplicates.length} file(s) already exist: ${dupFileList}\n\nClick OK to overwrite all, Cancel to skip all.`);
            }
            if (!action) {
                if (newFiles.length === 0) {
                    answerDiv.textContent = '⏭️ Skipped all files. Searching database...';
                    selectedQueryFiles = [];
                    await queryDatabaseOnly(queryText);
                    return;
                } else {
                    files = newFiles;
                }
            }
        }
    }
    
    if (files.length === 0) {
        answerDiv.textContent = '⏭️ No files selected. Searching database...';
        await queryDatabaseOnly(queryText);
        return;
    }
    
    try {
        const uploadedDocs = [];
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            answerDiv.textContent = `📤 Uploading file ${i+1}/${files.length}: ${escapeHtml(file.name)}...`;
            
            try {
                const result = await uploadDocument(file);
                if (result.ok) {
                    const docId = result.data.doc_id;
                    if (docId) {
                        uploadedDocs.push({ filename: file.name, doc_id: docId });
                    }
                } else {
                    answerDiv.textContent = `❌ Upload failed for ${escapeHtml(file.name)}`;
                }
            } catch(e) {
                answerDiv.textContent = `❌ Error uploading ${escapeHtml(file.name)}: ${e.message}`;
            }
        }
        
        if (uploadedDocs.length === 0) {
            answerDiv.textContent = '❌ Upload failed. No files were uploaded. Please try again.';
            return;
        }
        
        // Wait for indexing with exponential backoff
        await waitForIndexing(uploadedDocs, answerDiv);
        
        // Query with files
        const allFilenames = uploadedDocs.map(d => d.filename);
        answerDiv.textContent = `🔍 Querying with files: ${allFilenames.map(escapeHtml).join(', ')}...`;
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT);
        
        const result = await sendQueryWithFiles(queryText, allFilenames, controller.signal);
        clearTimeout(timeoutId);
        
        if (result.response || result.answer) {
            answerDiv.textContent = result.response || result.answer;
        } else if (result.detail) {
            answerDiv.textContent = `❌ Error: ${result.detail}`;
        } else {
            answerDiv.textContent = JSON.stringify(result, null, 2);
        }
    } catch(e) {
        if (e.name === 'AbortError') {
            answerDiv.textContent = '⏰ Query timed out after 5 minutes. The API is taking too long to respond.';
        } else {
            answerDiv.textContent = `❌ Error: ${e.message}`;
        }
    }
}

/**
 * Wait for documents to be indexed with exponential backoff
 * @param {Object[]} uploadedDocs - Uploaded documents
 * @param {HTMLElement} answerDiv - Status container
 */
async function waitForIndexing(uploadedDocs, answerDiv) {
    let allIndexed = false;
    let pollCount = 0;
    let delay = 1000; // Start with 1 second
    
    while (!allIndexed && pollCount < MAX_INDEXING_POLLS) {
        await new Promise(r => setTimeout(r, delay));
        pollCount++;
        delay = Math.min(delay * 1.5, 5000); // Exponential backoff, max 5s
        
        let indexedCount = 0;
        
        for (const doc of uploadedDocs) {
            try {
                const status = await getDocumentStatus(doc.doc_id);
                if (status && (status.indexed === true || status.ready === true || status.chunks > 0)) {
                    indexedCount++;
                }
            } catch(e) {
                console.log('Status check error:', e);
            }
        }
        
        answerDiv.textContent = `⏳ Indexing... (${pollCount}s) - ${indexedCount}/${uploadedDocs.length} files ready`;
        
        if (indexedCount === uploadedDocs.length) {
            allIndexed = true;
            break;
        }
    }
    
    if (!allIndexed) {
        answerDiv.textContent = '⚠️ Indexing in progress, but proceeding with query...';
    } else {
        answerDiv.textContent = '✅ Files indexed! Now querying...';
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        runQuery, testQuery, queryDatabaseOnly, runQueryWithFile,
        formatTimeoutResponse, handleQueryError, waitForIndexing
    };
}
