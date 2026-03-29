/**
 * File upload functionality for LightRAG WebUI
 */

// State for file uploads
let selectedFiles = [];
let folderFiles = [];
let selectedQueryFiles = [];

/**
 * Filter duplicates from file list
 * @param {File[]} files - Files to check
 * @param {Set<string>} existingDocs - Existing document names
 * @returns {Object} { duplicates, newFiles }
 */
function filterDuplicates(files, existingDocs) {
    const duplicates = [];
    const newFiles = [];
    for (const file of files) {
        if (existingDocs.has(file.name)) {
            duplicates.push(file.name);
        } else {
            newFiles.push(file);
        }
    }
    return { duplicates, newFiles };
}

/**
 * Show duplicate confirmation dialog
 * @param {string[]} duplicates - Duplicate filenames
 * @param {File[]} newFiles - New files
 * @param {string} context - Context for message
 * @returns {boolean} User confirmed
 */
function confirmDuplicates(duplicates, newFiles, context = 'files') {
    const dupList = duplicates.slice(0, 5).join(', ') + (duplicates.length > 5 ? '...' : '');
    if (newFiles.length > 0) {
        return confirm(`Found ${duplicates.length} existing ${context}:\n${dupList}\n\nClick OK to upload all (overwrite duplicates), Cancel to skip duplicates.`);
    } else {
        return confirm(`All ${duplicates.length} ${context} already exist. Click OK to overwrite all, Cancel to skip.`);
    }
}

/**
 * Handle file selection (accumulates files)
 */
function handleFileSelect() {
    const input = document.getElementById('fileInput');
    const filesList = document.getElementById('selectedFiles');
    
    if (input.files.length > 0) {
        const newFiles = Array.from(input.files);
        for (const f of newFiles) {
            if (!selectedFiles.some(existing => existing.name === f.name && existing.size === f.size)) {
                selectedFiles.push(f);
            }
        }
        filesList.style.display = 'block';
        updateFilesDisplay();
    }
}

/**
 * Update file list display
 */
function updateFilesDisplay() {
    const filesList = document.getElementById('selectedFiles');
    if (selectedFiles.length === 0) {
        filesList.style.display = 'none';
    } else {
        filesList.style.display = 'block';
        document.getElementById('fileCount').innerHTML = selectedFiles.map((f, idx) => 
            `<div class="file-item">
                <span>${escapeHtml(f.name)} (${(f.size/1024).toFixed(1)} KB)</span>
                <button onclick="removeFile(${idx}); event.stopPropagation();" style="padding: 2px 8px; margin-left: 10px; font-size: 12px; background: #f44336;">✕</button>
            </div>`
        ).join('');
    }
}

/**
 * Remove a single file from selection
 * @param {number} index - File index
 */
function removeFile(index) {
    selectedFiles.splice(index, 1);
    updateFilesDisplay();
}

/**
 * Clear all selected files
 */
function clearAllFiles() {
    selectedFiles = [];
    document.getElementById('fileInput').value = '';
    updateFilesDisplay();
}

/**
 * Handle folder selection
 */
function handleFolderSelect() {
    const input = document.getElementById('folderInput');
    const pathInput = document.getElementById('folderPath');
    const filesList = document.getElementById('folderFiles');
    
    if (input.files.length > 0) {
        folderFiles = Array.from(input.files);
        const firstFile = input.files[0].webkitRelativePath || input.files[0].name;
        const folderPath = firstFile.split('/').slice(0, -1).join('/') || '/';
        pathInput.value = folderPath;
        
        filesList.style.display = 'block';
        document.getElementById('folderFileCount').textContent = `${folderFiles.length} files selected`;
    }
}

/**
 * Ingest selected files
 */
async function ingestFiles() {
    if (selectedFiles.length === 0) {
        alert('Please select files first');
        return;
    }
    
    const progress = document.getElementById('ingestProgress');
    const status = document.getElementById('ingestStatus');
    const progressFill = document.getElementById('progressFill');
    
    progress.style.display = 'block';
    status.innerHTML = '<span class="spinner"></span><span style="color: #00d4ff; font-size: 16px;">Checking for existing files...</span>';
    document.getElementById('ingestFilesBtn').disabled = true;
    
    const existingDocs = await getExistingDocs();
    let { duplicates, newFiles } = filterDuplicates(selectedFiles, existingDocs);
    
    if (duplicates.length > 0) {
        const shouldUpload = confirmDuplicates(duplicates, newFiles, 'file(s)');
        
        if (!shouldUpload) {
            if (newFiles.length === 0) {
                status.textContent = '⏭️ All files already exist. Skipped.';
                document.getElementById('ingestFilesBtn').disabled = false;
                return;
            }
            selectedFiles = newFiles;
        }
    }
    
    status.innerHTML = '<span class="spinner"></span><span style="color: #00d4ff; font-size: 16px;">Starting upload...</span>';
    
    let processed = 0;
    let errors = 0;
    
    for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        status.innerHTML = '<span class="spinner"></span><span style="color: #00d4ff; font-size: 16px;">📄 Processing ' + (i+1) + '/' + selectedFiles.length + ': <strong>' + escapeHtml(file.name) + '</strong></span>';
        progressFill.style.width = `${((i+1)/selectedFiles.length)*100}%`;
        
        try {
            const result = await uploadDocument(file);
            if (result.ok) {
                processed++;
                fetchStats();
            } else {
                errors++;
            }
        } catch(e) {
            errors++;
        }
    }
    
    status.textContent = `✅ Processed ${processed} files${errors > 0 ? ', ' + errors + ' errors' : ''}`;
    document.getElementById('ingestFilesBtn').disabled = false;
    clearAllFiles();
    fetchStats();
}

/**
 * Ingest files from folder
 */
async function ingestFolder() {
    const folderPath = document.getElementById('folderPath').value;
    const recursive = document.getElementById('recursive').checked;
    const progress = document.getElementById('ingestProgress');
    const status = document.getElementById('ingestStatus');
    const progressFill = document.getElementById('progressFill');
    
    if (!folderPath && folderFiles.length === 0) {
        alert('Please select a folder first');
        return;
    }
    
    progress.style.display = 'block';
    status.innerHTML = '<span class="spinner"></span><span style="color: #00d4ff; font-size: 16px;">Starting folder upload...</span>';
    document.getElementById('ingestFolderBtn').disabled = true;
    
    try {
        if (folderFiles.length > 0) {
            status.innerHTML = '<span class="spinner"></span><span style="color: #00d4ff; font-size: 16px;">Checking for existing files...</span>';
            
            const existingDocs = await getExistingDocs();
            let { duplicates, newFiles } = filterDuplicates(folderFiles, existingDocs);
            
            if (duplicates.length > 0) {
                const shouldUpload = confirmDuplicates(duplicates, newFiles, 'file(s) in folder');
                
                if (!shouldUpload) {
                    if (newFiles.length === 0) {
                        status.textContent = '⏭️ All files already exist. Skipped.';
                        document.getElementById('ingestFolderBtn').disabled = false;
                        return;
                    }
                    folderFiles = newFiles;
                }
            }
            
            let processed = 0;
            for (let i = 0; i < folderFiles.length; i++) {
                const file = folderFiles[i];
                status.innerHTML = '<span class="spinner"></span><span style="color: #00d4ff; font-size: 16px;">📂 Processing ' + (i+1) + '/' + folderFiles.length + ': <strong>' + escapeHtml(file.name) + '</strong></span>';
                progressFill.style.width = `${((i+1)/folderFiles.length)*100}%`;
                
                try {
                    const content = await file.text();
                    if (content.length < 50) continue;
                    await uploadDocument(file);
                    processed++;
                    fetchStats();
                } catch(e) {}
            }
            status.textContent = `✅ Processed ${processed} files!`;
        } else {
            status.textContent = 'Processing folder...';
            const resp = await fetch(`${API_URL}/api/v1/documents/upload/folder/json`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ folder_path: folderPath, recursive })
            });
            const result = await resp.json();
            status.textContent = `✅ Processed ${result.total_files || 0} files`;
        }
        fetchStats();
    } catch(e) {
        status.textContent = `❌ Error: ${e.message}`;
    }
    
    document.getElementById('ingestFolderBtn').disabled = false;
}

/**
 * Handle file selection for query+file tab
 */
function handleQueryFileSelect() {
    const fileInput = document.getElementById('queryFileInput');
    const newFiles = Array.from(fileInput.files);
    
    for (const f of newFiles) {
        if (!selectedQueryFiles.some(existing => existing.name === f.name && existing.size === f.size)) {
            selectedQueryFiles.push(f);
        }
    }
    
    updateQueryFileDisplay();
    fileInput.value = '';
}

/**
 * Update query file list display
 */
function updateQueryFileDisplay() {
    const filesDiv = document.getElementById('querySelectedFiles');
    const fileCount = document.getElementById('queryFileCount');
    
    if (selectedQueryFiles.length > 0) {
        filesDiv.style.display = 'block';
        fileCount.innerHTML = selectedQueryFiles.map((f, idx) => 
            `<div style="display: flex; align-items: center; justify-content: space-between; padding: 5px 10px; margin: 5px 0; background: rgba(255,255,255,0.1); border-radius: 5px;">
                <span>${escapeHtml(f.name)} (${(f.size/1024).toFixed(1)} KB)</span>
                <button onclick="removeQueryFile(${idx}); event.stopPropagation();" style="padding: 2px 8px; margin-left: 10px; font-size: 12px; background: #f44336; border: none; border-radius: 3px; color: white; cursor: pointer;">✕</button>
            </div>`
        ).join('');
    } else {
        filesDiv.style.display = 'none';
    }
}

/**
 * Remove a query file
 * @param {number} index - File index
 */
function removeQueryFile(index) {
    selectedQueryFiles.splice(index, 1);
    updateQueryFileDisplay();
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        selectedFiles, folderFiles, selectedQueryFiles,
        filterDuplicates, confirmDuplicates, handleFileSelect,
        updateFilesDisplay, removeFile, clearAllFiles, handleFolderSelect,
        ingestFiles, ingestFolder, handleQueryFileSelect, updateQueryFileDisplay, removeQueryFile
    };
}
