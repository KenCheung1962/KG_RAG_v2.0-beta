/**
 * Ingest Tab Component
 */

import { uploadDocument, fetchDocuments, uploadFolder, isBackendHealthy } from '@/api';
import { updateStats } from '@/components/StatsCard';
import { renderFileList } from '@/components/FileList';
import { showProgress, updateProgress, setProgressStatus } from '@/components/ProgressBar';
import { getElement, setVisible, setDisabled } from '@/utils/dom';
import { escapeHtml } from '@/utils/helpers';
import { initDatabasePanel, getDatabasePanelHTML, showNotification } from '@/components/DatabasePanel';
import { createBackup as createBackupAPI } from '@/api/dbManagement';
import {
  getSelectedFiles, getFolderFiles,
  addSelectedFile, removeSelectedFile, clearSelectedFiles,
  setFolderFiles, setIsUploading
} from '@/stores/appStore';
import {
  checkForResumableSession,
  initSession,
  markFileUploaded,
  markSessionCompleted,
  markSessionInterrupted,
  filterNewFiles,
  getUploadStats,
  clearSession,
  isFileUploaded,
  type UploadSession
} from '@/stores/uploadTracker';

let _currentMethod: 'files' | 'folder' = 'files';
let _currentSession: UploadSession | null = null;

// Auto-backup settings
const AUTO_BACKUP_ENABLED_KEY = 'lightrag_auto_backup_enabled';
const AUTO_BACKUP_INTERVAL = 10; // Create backup every N files

function isAutoBackupEnabled(): boolean {
  return localStorage.getItem(AUTO_BACKUP_ENABLED_KEY) === 'true';
}

function setAutoBackupEnabled(enabled: boolean): void {
  localStorage.setItem(AUTO_BACKUP_ENABLED_KEY, String(enabled));
}

/**
 * Initialize ingest tab
 */
export function initIngestTab(): void {
  // Method toggle
  getElement('btnMethodFiles')?.addEventListener('click', () => setMethod('files'));
  getElement('btnMethodFolder')?.addEventListener('click', () => setMethod('folder'));
  
  // File input
  getElement('fileInput')?.addEventListener('change', handleFileSelect);
  getElement('clearFilesBtn')?.addEventListener('click', handleClearFiles);
  getElement('ingestFilesBtn')?.addEventListener('click', handleIngestFiles);
  
  // Folder input
  getElement('folderInput')?.addEventListener('change', handleFolderSelect);
  getElement('browseFolderBtn')?.addEventListener('click', () => {
    getElement<HTMLInputElement>('folderInput')?.click();
  });
  getElement('ingestFolderBtn')?.addEventListener('click', handleIngestFolder);
  
  // Auto-backup checkboxes (sync both)
  const autoBackupFolder = getElement<HTMLInputElement>('autoBackup');
  const autoBackupFiles = getElement<HTMLInputElement>('autoBackupFiles');
  
  autoBackupFolder?.addEventListener('change', (e) => {
    const enabled = (e.target as HTMLInputElement).checked;
    setAutoBackupEnabled(enabled);
    if (autoBackupFiles) autoBackupFiles.checked = enabled;
    console.log(`Auto-backup ${enabled ? 'enabled' : 'disabled'}`);
  });
  
  autoBackupFiles?.addEventListener('change', (e) => {
    const enabled = (e.target as HTMLInputElement).checked;
    setAutoBackupEnabled(enabled);
    if (autoBackupFolder) autoBackupFolder.checked = enabled;
    console.log(`Auto-backup ${enabled ? 'enabled' : 'disabled'}`);
  });
  
  // Resume buttons
  getElement('resumeUploadBtn')?.addEventListener('click', resumePreviousUpload);
  getElement('discardSessionBtn')?.addEventListener('click', discardSession);
  getElement('clearUploadHistoryBtn')?.addEventListener('click', clearUploadHistoryHandler);
  
  // Check for resumable sessions on load
  checkForResumeSession();
  
  // Update stats display
  updateUploadStatsDisplay();
  
  // Initialize database management panel
  initDatabasePanel();
}

/**
 * Set upload method
 */
function setMethod(method: 'files' | 'folder'): void {
  _currentMethod = method;
  
  setVisible('methodFiles', method === 'files');
  setVisible('methodFolder', method === 'folder');
  
  const filesBtn = getElement('btnMethodFiles');
  const folderBtn = getElement('btnMethodFolder');
  
  filesBtn?.classList.toggle('active', method === 'files');
  filesBtn?.classList.toggle('inactive', method !== 'files');
  filesBtn?.setAttribute('aria-pressed', String(method === 'files'));
  
  folderBtn?.classList.toggle('active', method === 'folder');
  folderBtn?.classList.toggle('inactive', method !== 'folder');
  folderBtn?.setAttribute('aria-pressed', String(method === 'folder'));
}

/**
 * Handle file selection
 */
function handleFileSelect(): void {
  const input = getElement<HTMLInputElement>('fileInput');
  if (!input?.files?.length) return;
  
  Array.from(input.files).forEach(file => addSelectedFile(file));
  renderFileList(getSelectedFiles(), {
    containerId: 'selectedFilesList',
    onRemove: handleRemoveFile,
    emptyText: 'Selected files:'
  });
  
  input.value = ''; // Reset for re-selection
}

/**
 * Handle file removal
 */
function handleRemoveFile(index: number): void {
  removeSelectedFile(index);
  renderFileList(getSelectedFiles(), {
    containerId: 'selectedFilesList',
    onRemove: handleRemoveFile,
    emptyText: 'Selected files:'
  });
}

/**
 * Handle clear all files
 */
function handleClearFiles(): void {
  clearSelectedFiles();
  renderFileList([], {
    containerId: 'selectedFilesList',
    onRemove: handleRemoveFile
  });
  getElement<HTMLInputElement>('fileInput')!.value = '';
}

/**
 * Check for duplicates
 */
export async function checkDuplicates(files: File[]): Promise<{ 
  duplicates: string[]; 
  newFiles: File[];
  duplicateDocIds?: Map<string, string>;  // filename -> doc_id mapping
}> {
  const existingDocs = await fetchDocuments(1000);
  const existingNames = new Set(existingDocs.map(d => d.filename));
  const existingDocMap = new Map(existingDocs.map(d => [d.filename, d.doc_id]));
  
  const duplicates: string[] = [];
  const newFiles: File[] = [];
  
  for (const file of files) {
    if (existingNames.has(file.name)) {
      duplicates.push(file.name);
    } else {
      newFiles.push(file);
    }
  }
  
  // Build map of duplicate filenames to their doc_ids
  const duplicateDocIds = new Map<string, string>();
  for (const dupName of duplicates) {
    const docId = existingDocMap.get(dupName);
    if (docId) {
      duplicateDocIds.set(dupName, docId);
    }
  }
  
  return { duplicates, newFiles, duplicateDocIds };
}

/**
 * Show duplicate confirmation dialog
 */
function confirmDuplicates(
  duplicates: string[],
  newFilesCount: number,
  context = 'files'
): boolean {
  const dupList = duplicates.slice(0, 5).join(', ') + (duplicates.length > 5 ? '...' : '');
  
  if (newFilesCount > 0) {
    return confirm(
      `Found ${duplicates.length} existing ${context}:\n${dupList}\n\n` +
      `Click OK to upload all (overwrite duplicates), Cancel to skip duplicates.`
    );
  } else {
    return confirm(
      `All ${duplicates.length} ${context} already exist. ` +
      `Click OK to overwrite all, Cancel to skip.`
    );
  }
}

/**
 * Handle ingest files
 */
async function handleIngestFiles(): Promise<void> {
  const files = getSelectedFiles();
  if (files.length === 0) {
    alert('Please select files first');
    return;
  }
  
  setIsUploading(true);
  setDisabled('ingestFilesBtn', true);
  showProgress('ingestProgress');
  setProgressStatus('ingestProgress', 'Checking for existing files...');
  
  try {
    // Check duplicates
    const { duplicates, newFiles } = await checkDuplicates(files);
    
    if (duplicates.length > 0) {
      const shouldUpload = confirmDuplicates(duplicates, newFiles.length, 'file(s)');
      
      if (!shouldUpload) {
        if (newFiles.length === 0) {
          setProgressStatus('ingestProgress', '⏭️ All files already exist. Skipped.', false);
          setDisabled('ingestFilesBtn', false);
          setIsUploading(false);
          return;
        }
        // Continue with only new files
        clearSelectedFiles();
        newFiles.forEach(f => addSelectedFile(f));
      }
    }
    
    const filesToUpload = getSelectedFiles();
    let processed = 0;
    let errors = 0;
    const uploadErrorLog: Array<{file: string; error: string}> = [];
    
    for (let i = 0; i < filesToUpload.length; i++) {
      const file = filesToUpload[i];
      const percent = ((i + 1) / filesToUpload.length) * 100;
      
      setProgressStatus('ingestProgress', `📄 Processing ${i + 1}/${filesToUpload.length}: <strong>${escapeHtml(file.name)}</strong>`);
      updateProgress('ingestProgress', percent);
      
      try {
        await uploadDocument(file);
        processed++;
        await updateStats();
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
        const errorMsg = error instanceof Error ? error.message : String(error);
        
        // Provide clearer message for timeout errors
        const isTimeout = error instanceof Error && 
          (error.name === 'TimeoutError' || 
           errorMsg.includes('timeout') ||
           errorMsg.includes('Abort'));
        
        const displayError = isTimeout 
          ? 'Upload timeout - file too large or backend busy' 
          : errorMsg;
        
        uploadErrorLog.push({file: file.name, error: displayError});
        errors++;
      }
    }
    
    setProgressStatus('ingestProgress', `✅ Processed ${processed} files${errors > 0 ? `, ${errors} errors` : ''}`, false);
    
    // Show error details if there are errors
    if (errors > 0 && uploadErrorLog.length > 0) {
      displayErrorDetails(uploadErrorLog);
    }
    
    handleClearFiles();
    await updateStats();
    
  } catch (error) {
    console.error('Ingest failed:', error);
    setProgressStatus('ingestProgress', `❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`, false);
  } finally {
    setDisabled('ingestFilesBtn', false);
    setIsUploading(false);
  }
}

/**
 * Display error details
 */
function displayErrorDetails(errorLog: Array<{file: string; error: string}>): void {
  const errorContainer = getElement('uploadErrorLog');
  if (!errorContainer) return;
  
  // Group by error message
  const errorGroups = new Map<string, string[]>();
  errorLog.forEach(({file, error}) => {
    const files = errorGroups.get(error) || [];
    files.push(file);
    errorGroups.set(error, files);
  });
  
  let html = '<div class="error-log"><h4>⚠️ Error Details:</h4>';
  
  // Show unique errors with counts
  Array.from(errorGroups.entries())
    .slice(0, 5)
    .forEach(([error, files]) => {
      html += `<div class="error-item"><strong>${files.length} files:</strong> ${escapeHtml(error)}`;
      if (files.length <= 3) {
        html += `<br><small>${files.map(escapeHtml).join(', ')}</small>`;
      }
      html += '</div>';
    });
  
  if (errorGroups.size > 5) {
    html += `<p><em>... and ${errorGroups.size - 5} more error types</em></p>`;
  }
  
  html += '</div>';
  errorContainer.innerHTML = html;
  errorContainer.style.display = 'block';
}

/**
 * Handle folder selection
 */
function handleFolderSelect(): void {
  const input = getElement<HTMLInputElement>('folderInput');
  if (!input?.files?.length) return;
  
  let files = Array.from(input.files);
  const firstFile = files[0];
  const folderPath = firstFile.webkitRelativePath?.split('/')[0] || '/';
  
  // Check for existing files and filter
  const filterResult = filterNewFiles(files);
  
  if (filterResult.skippedFiles.length > 0) {
    console.log(`${filterResult.skippedFiles.length} files already uploaded, skipping`);
    
    // Show notification
    const notificationEl = getElement('duplicateNotification');
    if (notificationEl) {
      notificationEl.innerHTML = `
        <div class="notification info">
          📋 <strong>${filterResult.skippedFiles.length}</strong> files already uploaded (skipped)<br>
          <strong>${filterResult.newFiles.length}</strong> new files to upload
        </div>
      `;
      notificationEl.style.display = 'block';
    }
    
    // Use only new files
    files = filterResult.newFiles;
  }
  
  setFolderFiles(files);
  
  getElement<HTMLInputElement>('folderPath')!.value = folderPath;
  getElement('folderFileCount')!.textContent = `${files.length} files selected`;
  setVisible('folderFiles', true);
}

/**
 * Handle ingest folder
 */
async function handleIngestFolder(): Promise<void> {
  const folderPath = getElement<HTMLInputElement>('folderPath')?.value ?? '';
  const recursive = getElement<HTMLInputElement>('recursive')?.checked ?? true;
  let files = getFolderFiles();
  
  if (!folderPath && files.length === 0) {
    alert('Please select a folder first');
    return;
  }
  
  // Filter out already uploaded files (pre-filter before upload)
  const filterResult = filterNewFiles(files);
  const preFilteredCount = filterResult.skippedFiles.length;
  
  if (preFilteredCount > 0) {
    console.log(`📋 Pre-filtered ${preFilteredCount} already uploaded files`);
    showNotification(`📋 ${preFilteredCount} files already uploaded, will be skipped`, 'info');
  }
  
  files = filterResult.newFiles;
  
  if (files.length === 0) {
    setProgressStatus('ingestProgress', '✅ All files already uploaded! Nothing to upload.', false);
    return;
  }
  
  console.log(`📤 Starting upload of ${files.length} new files (${preFilteredCount} already uploaded)`);
  
  // Initialize upload session
  _currentSession = initSession(folderPath, files.length);
  
  setIsUploading(true);
  setDisabled('ingestFolderBtn', true);
  showProgress('ingestProgress');
  setProgressStatus('ingestProgress', `Starting upload of ${files.length} new files...`);
  
  try {
    if (files.length > 0) {
      // Browser folder selection
      const { duplicates, newFiles } = await checkDuplicates(files);
      
      if (duplicates.length > 0) {
        const shouldUpload = confirmDuplicates(duplicates, newFiles.length, 'file(s) in folder');
        
        if (!shouldUpload && newFiles.length === 0) {
          setProgressStatus('ingestProgress', '⏭️ All files already exist in database. Skipped.', false);
          setDisabled('ingestFolderBtn', false);
          setIsUploading(false);
          return;
        }
        
        // Upload only new files if user chose to skip duplicates
        const filesToUpload = shouldUpload ? files : newFiles;
        await uploadFilesBatch(filesToUpload);
      } else {
        await uploadFilesBatch(files);
      }
    } else {
      // Server-side folder scanning
      const result = await uploadFolder({ folder_path: folderPath, recursive });
      setProgressStatus('ingestProgress', `✅ Processed ${result.total_files} files`, false);
      // Update stats after server-side upload
      await updateStats().catch(console.error);
    }
    
  } catch (error) {
    console.error('Folder ingest failed:', error);
    setProgressStatus('ingestProgress', `❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`, false);
  } finally {
    setDisabled('ingestFolderBtn', false);
    setIsUploading(false);
  }
}

// Store recent errors for display
let uploadErrorLog: Array<{file: string; error: string}> = [];

/**
 * Delay utility
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Check backend health with retries and exponential backoff
 */
async function checkBackendHealthWithRetry(
  maxRetries = 3,
  baseDelay = 2000
): Promise<boolean> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const isHealthy = await isBackendHealthy();
    if (isHealthy) return true;
    
    if (attempt < maxRetries - 1) {
      const delayMs = baseDelay * Math.pow(2, attempt); // 2s, 4s, 8s
      console.log(`Health check failed, retrying in ${delayMs}ms... (attempt ${attempt + 1}/${maxRetries})`);
      await delay(delayMs);
    }
  }
  return false;
}

/**
 * Upload files in batch with health checks and rate limiting
 * CONSERVATIVE: Small batches, longer delays to prevent backend overload
 */
async function uploadFilesBatch(files: File[]): Promise<void> {
  let processed = 0;
  let errors = 0;
  let skipped = 0;
  let consecutiveErrors = 0;
  let lastBackupFileCount = 0;
  uploadErrorLog = []; // Reset error log
  
  // VERY CONSERVATIVE settings to prevent backend crashes
  const BATCH_SIZE = 5; // Reduced from 10 to 5 files at a time
  const DELAY_BETWEEN_FILES = 300; // 300ms between each file
  const DELAY_BETWEEN_BATCHES = 2000; // 2 seconds between batches
  const MAX_CONSECUTIVE_ERRORS = 5; // Stop if 5 errors in a row
  const STATS_UPDATE_INTERVAL = 5; // Update stats every N files during upload
  
  // Auto-backup settings
  const autoBackupEnabled = isAutoBackupEnabled();
  const autoBackupInterval = AUTO_BACKUP_INTERVAL;
  
  // Filter out tiny files first
  const validFiles = files.filter(file => {
    if (file.size < 50) {
      skipped++;
      return false;
    }
    return true;
  });
  
  const totalBatches = Math.ceil(validFiles.length / BATCH_SIZE);
  
  // Create initial backup if auto-backup is enabled
  if (autoBackupEnabled && validFiles.length > autoBackupInterval) {
    try {
      setProgressStatus('ingestProgress', '💾 Creating initial backup before upload...', false);
      await createBackupAPI();
      lastBackupFileCount = 0;
      showNotification('✅ Initial backup created', 'success');
    } catch (e) {
      console.error('Initial backup failed:', e);
      showNotification('⚠️ Initial backup failed, continuing anyway', 'error');
    }
  }
  
  for (let batchIndex = 0; batchIndex < totalBatches; batchIndex++) {
    const startIdx = batchIndex * BATCH_SIZE;
    const batch = validFiles.slice(startIdx, startIdx + BATCH_SIZE);
    const isLastBatch = batchIndex === totalBatches - 1;
    
    // Check backend health before each batch (with retries)
    const isHealthy = await checkBackendHealthWithRetry(3, 2000);
    if (!isHealthy) {
      console.error(`Backend health check failed before batch ${batchIndex + 1} after retries`);
      
      // Mark all remaining files as failed
      const remainingFiles = validFiles.slice(startIdx);
      remainingFiles.forEach(file => {
        uploadErrorLog.push({
          file: file.name,
          error: 'Backend unavailable - upload stopped'
        });
      });
      errors += remainingFiles.length;
      
      setProgressStatus(
        'ingestProgress', 
        `❌ Backend unavailable after ${processed} files. ${remainingFiles.length} files not processed.`, 
        false
      );
      break; // Stop processing
    }
    
    // Process this batch
    for (let i = 0; i < batch.length; i++) {
      const file = batch[i];
      const globalIndex = startIdx + i + 1;
      const percent = (globalIndex / validFiles.length) * 100;
      
      // Check if file was already uploaded (resume functionality)
      if (isFileUploaded(file.name)) {
        console.log(`⏭️ Skipping already uploaded: ${file.name}`);
        skipped++;
        processed++; // Count as processed since it's already done
        
        setProgressStatus(
          'ingestProgress', 
          `⏭️ Skipping ${skipped} already uploaded... (${globalIndex}/${validFiles.length})<br><strong>${escapeHtml(file.name.substring(0, 50))}${file.name.length > 50 ? '...' : ''}</strong>`
        );
        updateProgress('ingestProgress', percent);
        continue; // Skip to next file
      }
      
      setProgressStatus(
        'ingestProgress', 
        `📂 Batch ${batchIndex + 1}/${totalBatches}: ${i + 1}/${batch.length} (${globalIndex}/${validFiles.length})<br><strong>${escapeHtml(file.name.substring(0, 50))}${file.name.length > 50 ? '...' : ''}</strong>`
      );
      updateProgress('ingestProgress', percent);
      
      try {
        const result = await uploadDocument(file);
        processed++;
        consecutiveErrors = 0; // Reset consecutive errors on success
        
        // Mark file as uploaded in session and persistent storage
        markFileUploaded(file.name, result.doc_id || file.name);
        
        // Update session display
        if (_currentSession) {
          _currentSession.processedFiles++;
        }
        
        // Update stats every N files to show progress in real-time
        if (processed % STATS_UPDATE_INTERVAL === 0) {
          console.log(`[Upload] Updating stats after ${processed} files...`);
          updateStats().catch(e => console.error('[Upload] Stats update failed:', e));
        }
        
        // Small delay after each file to prevent overwhelming backend
        if (i < batch.length - 1) { // Don't delay after last file in batch
          await delay(DELAY_BETWEEN_FILES);
        }
      } catch (error) {
        errors++;
        consecutiveErrors++;
        const errorMsg = error instanceof Error ? error.message : String(error);
        
        // Check if it's a timeout error
        const isTimeout = error instanceof Error && 
          (error.name === 'TimeoutError' || 
           errorMsg.includes('timeout') ||
           errorMsg.includes('Abort'));
        
        if (isTimeout) {
          console.warn(`⏱️ Timeout uploading ${file.name}: ${errorMsg}`);
          uploadErrorLog.push({file: file.name, error: 'Upload timeout (file too large or backend busy)'});
        } else {
          uploadErrorLog.push({file: file.name, error: errorMsg});
        }
        
        console.error(`Failed to upload ${file.name}:`, error);
        
        // If too many consecutive errors, check if backend is down
        if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
          console.warn(`Too many consecutive errors (${consecutiveErrors}), checking backend health...`);
          const isBackendOk = await isBackendHealthy();
          if (!isBackendOk) {
            const remainingFiles = validFiles.slice(globalIndex);
            remainingFiles.forEach(f => {
              uploadErrorLog.push({
                file: f.name,
                error: 'Backend crashed - upload stopped'
              });
            });
            errors += remainingFiles.length;
            
            setProgressStatus(
              'ingestProgress', 
              `❌ Backend crashed after ${processed} files. Stopping upload.`, 
              false
            );
            displayErrorDetails(uploadErrorLog);
            return; // Exit completely
          }
          // Backend is ok, just slow - reset counter and continue
          consecutiveErrors = 0;
        }
        
        // Delay after error
        await delay(DELAY_BETWEEN_FILES * 2);
      }
    }
    
    // Auto-backup check after each batch
    if (autoBackupEnabled && processed - lastBackupFileCount >= autoBackupInterval) {
      try {
        console.log(`💾 Auto-creating backup after ${processed} files...`);
        setProgressStatus('ingestProgress', `💾 Creating backup after ${processed} files...`, false);
        await createBackupAPI();
        lastBackupFileCount = processed;
        showNotification(`✅ Backup created after ${processed} files`, 'success');
      } catch (e) {
        console.error('Auto-backup failed:', e);
        // Continue upload even if backup fails
      }
    }
    
    // Pause between batches (except last)
    if (!isLastBatch) {
      setProgressStatus(
        'ingestProgress', 
        `⏳ Cooling down... (${batchIndex + 1}/${totalBatches} batches complete)`, 
        false
      );
      await delay(DELAY_BETWEEN_BATCHES);
    }
  }
  
  // Create final backup if auto-backup enabled and files were uploaded
  if (autoBackupEnabled && processed > 0) {
    try {
      console.log('💾 Creating final backup after upload...');
      setProgressStatus('ingestProgress', '💾 Creating final backup...', false);
      await createBackupAPI();
      showNotification('✅ Final backup created', 'success');
    } catch (e) {
      console.error('Final backup failed:', e);
    }
  }
  
  const statusParts = [`✅ Processed ${processed} files`];
  if (skipped > 0) statusParts.push(`skipped ${skipped} already uploaded`);
  if (errors > 0) statusParts.push(`${errors} errors`);
  
  setProgressStatus('ingestProgress', statusParts.join(', '), false);
  
  // Show error details if there are errors
  if (errors > 0 && uploadErrorLog.length > 0) {
    displayErrorDetails(uploadErrorLog);
  }
  
  // Final stats update to reflect all uploaded files
  console.log('[Upload] Final stats update...');
  await updateStats().catch(e => console.error('[Upload] Final stats update failed:', e));
  
  // Mark session as completed or interrupted
  if (errors === 0 && processed + skipped === files.length) {
    markSessionCompleted();
    setProgressStatus('ingestProgress', `✅ Upload completed! ${processed} new files uploaded (${skipped} skipped).`, false);
  } else if (errors > 0) {
    markSessionInterrupted();
  }
}

// ============ RESUME FUNCTIONALITY ============

/**
 * Check for resumable session on page load
 */
async function checkForResumeSession(): Promise<void> {
  const result = await checkForResumableSession();
  
  if (result.hasSession && result.session) {
    _currentSession = result.session;
    showResumeDialog(result.message || 'Found previous upload session');
  } else {
    hideResumeDialog();
  }
}

/**
 * Show resume dialog
 */
function showResumeDialog(message: string): void {
  const dialog = getElement('resumeDialog');
  const messageEl = getElement('resumeMessage');
  
  if (dialog && messageEl) {
    messageEl.textContent = message;
    dialog.style.display = 'block';
  }
}

/**
 * Hide resume dialog
 */
function hideResumeDialog(): void {
  const dialog = getElement('resumeDialog');
  if (dialog) {
    dialog.style.display = 'none';
  }
}

/**
 * Resume previous upload session
 */
async function resumePreviousUpload(): Promise<void> {
  if (!_currentSession) {
    alert('No session to resume');
    return;
  }
  
  hideResumeDialog();
  
  // Show a message that we're resuming
  setProgressStatus(
    'ingestProgress', 
    `🔄 Resuming upload: ${_currentSession.processedFiles}/${_currentSession.totalFiles} files already processed`,
    false
  );
  showProgress('ingestProgress');
  
  // User needs to select the same folder again to get the files
  alert(`Please select the same folder again to resume upload.\n\nAlready uploaded: ${_currentSession.processedFiles}/${_currentSession.totalFiles} files`);
}

/**
 * Discard previous session and start fresh
 */
function discardSession(): void {
  if (confirm('Are you sure you want to discard the previous upload session?')) {
    clearSession();
    _currentSession = null;
    hideResumeDialog();
    setProgressStatus('ingestProgress', 'Previous session discarded. Ready to start new upload.', false);
  }
}

/**
 * Update upload stats display
 */
function updateUploadStatsDisplay(): void {
  const stats = getUploadStats();
  const statsEl = getElement('uploadStats');
  
  if (statsEl && stats.totalUploaded > 0) {
    const date = stats.lastUpload ? new Date(stats.lastUpload).toLocaleDateString() : 'Unknown';
    statsEl.innerHTML = `📊 Total files uploaded: <strong>${stats.totalUploaded}</strong> (last: ${date})`;
    statsEl.style.display = 'block';
  }
}

/**
 * Clear upload history handler
 */
function clearUploadHistoryHandler(): void {
  if (confirm('⚠️ WARNING: This will clear ALL upload history!\n\nFiles already in the database will remain, but the system will not remember which files were uploaded.\n\nAre you sure?')) {
    clearUploadHistory();
    updateUploadStatsDisplay();
    alert('Upload history cleared.');
  }
}

/**
 * Clear upload history and session
 */
function clearUploadHistory(): void {
  localStorage.removeItem('lightrag_upload_tracker');
  localStorage.removeItem('lightrag_uploaded_files');
  _currentSession = null;
}

/**
 * Get tab HTML
 */
export function getIngestTabHTML(): string {
  return `
    <div id="ingest" class="tab-content card" role="tabpanel" aria-labelledby="tab-ingest">
      <h2>📥 Ingest Documents</h2>
      
      <!-- Resume Dialog -->
      <div id="resumeDialog" class="resume-dialog" style="display: none;">
        <div class="resume-content">
          <h3>🔄 Resume Previous Upload?</h3>
          <p id="resumeMessage">Found previous upload session</p>
          <div class="resume-actions">
            <button id="resumeUploadBtn" class="btn">🔄 Resume Upload</button>
            <button id="discardSessionBtn" class="btn danger">🗑️ Discard & Start New</button>
          </div>
        </div>
      </div>
      
      <!-- Upload Stats -->
      <div id="uploadStats" class="upload-stats" style="display: none;"></div>
      
      <!-- Duplicate Notification -->
      <div id="duplicateNotification" class="notification-container" style="display: none;"></div>
      
      <div class="method-toggle" role="group" aria-label="Upload method selection">
        <button class="active" id="btnMethodFiles" aria-pressed="true">📄 Upload Files</button>
        <button class="inactive" id="btnMethodFolder" aria-pressed="false">📂 Select Folder</button>
      </div>
      
      <div id="methodFiles">
        <h3>📄 Upload Files</h3>
        <label for="fileInput" class="sr-only">Select files to upload</label>
        <input type="file" id="fileInput" multiple accept=".txt,.md,.pdf,.doc,.docx,.csv,.json,.html,.xml" aria-describedby="fileInput-hint">
        <p id="fileInput-hint" class="hint">Select multiple files to upload to the knowledge base</p>
        <div id="selectedFilesList" class="file-list" style="display: none;"></div>
        
        <div class="checkbox-wrapper auto-backup-wrapper" style="margin: 15px 0; padding: 10px; background: rgba(0, 212, 255, 0.05); border-radius: 8px;">
          <input type="checkbox" id="autoBackupFiles" ${isAutoBackupEnabled() ? 'checked' : ''}>
          <label for="autoBackupFiles" style="font-weight: 500;">
            💾 Auto-backup during upload
            <span style="display: block; font-size: 12px; font-weight: normal; color: var(--text-secondary); margin-top: 4px;">
              Creates backups every ${AUTO_BACKUP_INTERVAL} files and at completion
            </span>
          </label>
        </div>
        
        <button id="ingestFilesBtn" class="btn" aria-label="Start ingesting selected files">📥 Ingest Files</button>
        <button id="clearFilesBtn" class="btn danger" aria-label="Clear all selected files">🗑️ Clear All</button>
      </div>
      
      <div id="methodFolder" style="display: none;">
        <h3>📂 Select Folder</h3>
        <div class="folder-input-wrapper">
          <label for="folderPath" class="sr-only">Folder path</label>
          <input type="text" id="folderPath" placeholder="Select or enter folder path...">
          <button class="folder-btn" id="browseFolderBtn" aria-label="Browse for folder">📂 Browse</button>
          <input type="file" id="folderInput" webkitdirectory style="display: none;" aria-label="Select folder">
        </div>
        
        <div id="folderFiles" class="file-list" style="display: none;">
          <strong>Files to ingest:</strong>
          <div id="folderFileCount"></div>
        </div>
        
        <div class="checkbox-wrapper">
          <input type="checkbox" id="recursive" checked>
          <label for="recursive">Scan subfolders recursively</label>
        </div>
        
        <div class="checkbox-wrapper auto-backup-wrapper" style="margin-top: 10px; padding: 10px; background: rgba(0, 212, 255, 0.05); border-radius: 8px;">
          <input type="checkbox" id="autoBackup" ${isAutoBackupEnabled() ? 'checked' : ''}>
          <label for="autoBackup" style="font-weight: 500;">
            💾 Auto-backup during upload
            <span style="display: block; font-size: 12px; font-weight: normal; color: var(--text-secondary); margin-top: 4px;">
              Creates backups every ${AUTO_BACKUP_INTERVAL} files and at completion
            </span>
          </label>
        </div>
        
        <button id="ingestFolderBtn" class="btn" aria-label="Start ingesting folder" style="margin-top: 15px;">📥 Ingest Folder</button>
      </div>
      
      <div id="ingestProgress"></div>
      <div id="uploadErrorLog" class="error-log-container" style="display: none;"></div>
      
      <!-- Management Actions -->
      <div class="management-actions" style="margin-top: 20px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
        <button id="clearUploadHistoryBtn" class="btn" style="background: rgba(255,255,255,0.1); font-size: 12px;">
          🗑️ Clear Upload History
        </button>
        <p class="hint" style="margin-top: 5px;">This will reset the list of previously uploaded files</p>
      </div>
      
      <!-- Database Management Panel -->
      ${getDatabasePanelHTML()}
    </div>
  `;
}
