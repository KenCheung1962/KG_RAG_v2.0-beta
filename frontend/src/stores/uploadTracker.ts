/**
 * Upload Tracker - Saves and resumes upload progress
 * Uses localStorage to persist upload state between sessions
 */

import { fetchDocuments } from '@/api';

const STORAGE_KEY = 'lightrag_upload_tracker';
const UPLOADED_FILES_KEY = 'lightrag_uploaded_files';

export interface UploadSession {
  id: string;
  folderPath: string;
  startedAt: number;
  lastUpdated: number;
  totalFiles: number;
  processedFiles: number;
  uploadedFileIds: string[]; // Array of successfully uploaded file names
  status: 'in_progress' | 'completed' | 'interrupted';
}

export interface UploadedFileRecord {
  filename: string;
  docId: string;
  uploadedAt: number;
  size: number;
  checksum?: string; // Optional: for integrity verification
}

/**
 * Generate a unique session ID
 */
function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Get current upload session from localStorage
 */
export function getCurrentSession(): UploadSession | null {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (!data) return null;
    return JSON.parse(data);
  } catch {
    return null;
  }
}

/**
 * Save current upload session to localStorage
 */
export function saveSession(session: UploadSession): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch (error) {
    console.error('Failed to save upload session:', error);
  }
}

/**
 * Clear current upload session
 */
export function clearSession(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Initialize a new upload session
 */
export function initSession(folderPath: string, totalFiles: number): UploadSession {
  const session: UploadSession = {
    id: generateSessionId(),
    folderPath,
    startedAt: Date.now(),
    lastUpdated: Date.now(),
    totalFiles,
    processedFiles: 0,
    uploadedFileIds: [],
    status: 'in_progress'
  };
  saveSession(session);
  return session;
}

/**
 * Mark a file as successfully uploaded
 */
export function markFileUploaded(filename: string, docId: string): void {
  const session = getCurrentSession();
  if (!session) return;
  
  if (!session.uploadedFileIds.includes(filename)) {
    session.uploadedFileIds.push(filename);
  }
  session.processedFiles = session.uploadedFileIds.length;
  session.lastUpdated = Date.now();
  saveSession(session);
  
  // Also save to persistent uploaded files list
  addToUploadedFilesList(filename, docId);
}

/**
 * Get list of uploaded files from persistent storage
 */
export function getUploadedFilesList(): UploadedFileRecord[] {
  try {
    const data = localStorage.getItem(UPLOADED_FILES_KEY);
    if (!data) return [];
    return JSON.parse(data);
  } catch {
    return [];
  }
}

/**
 * Add file to persistent uploaded files list
 */
function addToUploadedFilesList(filename: string, docId: string): void {
  try {
    const list = getUploadedFilesList();
    // Remove existing entry if present (update)
    const filtered = list.filter(f => f.filename !== filename);
    filtered.push({
      filename,
      docId,
      uploadedAt: Date.now(),
      size: 0 // Size not tracked in current implementation
    });
    // Keep only last 10000 entries to prevent storage overflow
    const trimmed = filtered.slice(-10000);
    localStorage.setItem(UPLOADED_FILES_KEY, JSON.stringify(trimmed));
  } catch (error) {
    console.error('Failed to save to uploaded files list:', error);
  }
}

/**
 * Check if a file has been uploaded (by filename)
 */
export function isFileUploaded(filename: string): boolean {
  const list = getUploadedFilesList();
  return list.some(f => f.filename === filename);
}

/**
 * Check for existing session and offer resume
 */
export async function checkForResumableSession(): Promise<{
  hasSession: boolean;
  session?: UploadSession;
  message?: string;
}> {
  const session = getCurrentSession();
  
  if (!session) {
    return { hasSession: false };
  }
  
  if (session.status === 'completed') {
    clearSession();
    return { hasSession: false };
  }
  
  // Check if backend has these files
  try {
    const existingDocs = await fetchDocuments(10000);
    const existingNames = new Set(existingDocs.map(d => d.filename));
    
    // Verify which files from session are actually on server
    const verifiedUploaded = session.uploadedFileIds.filter(id => existingNames.has(id));
    const missingFiles = session.uploadedFileIds.filter(id => !existingNames.has(id));
    
    if (missingFiles.length > 0) {
      console.warn(`${missingFiles.length} files from session not found on server`);
      // Update session to remove missing files
      session.uploadedFileIds = verifiedUploaded;
      session.processedFiles = verifiedUploaded.length;
      saveSession(session);
    }
    
    if (verifiedUploaded.length >= session.totalFiles) {
      // All files are uploaded
      session.status = 'completed';
      saveSession(session);
      return {
        hasSession: true,
        session,
        message: `Previous upload completed (${verifiedUploaded.length}/${session.totalFiles} files)`
      };
    }
    
    return {
      hasSession: true,
      session,
      message: `Found interrupted upload: ${verifiedUploaded.length}/${session.totalFiles} files processed`
    };
  } catch (error) {
    // Can't verify with server, assume session is valid
    return {
      hasSession: true,
      session,
      message: `Found previous upload session: ${session.processedFiles}/${session.totalFiles} files (server verification failed)`
    };
  }
}

/**
 * Mark session as completed
 */
export function markSessionCompleted(): void {
  const session = getCurrentSession();
  if (session) {
    session.status = 'completed';
    session.lastUpdated = Date.now();
    saveSession(session);
  }
}

/**
 * Mark session as interrupted
 */
export function markSessionInterrupted(): void {
  const session = getCurrentSession();
  if (session && session.status !== 'completed') {
    session.status = 'interrupted';
    session.lastUpdated = Date.now();
    saveSession(session);
  }
}

/**
 * Filter files to only those not yet uploaded
 */
export function filterNewFiles(files: File[]): {
  newFiles: File[];
  skippedFiles: string[];
  count: { new: number; skipped: number };
} {
  const uploadedList = getUploadedFilesList();
  const uploadedNames = new Set(uploadedList.map(f => f.filename));
  
  const newFiles: File[] = [];
  const skippedFiles: string[] = [];
  
  for (const file of files) {
    if (uploadedNames.has(file.name)) {
      skippedFiles.push(file.name);
    } else {
      newFiles.push(file);
    }
  }
  
  return {
    newFiles,
    skippedFiles,
    count: { new: newFiles.length, skipped: skippedFiles.length }
  };
}

/**
 * Get upload statistics
 */
export function getUploadStats(): {
  totalUploaded: number;
  lastUpload: number | null;
} {
  const list = getUploadedFilesList();
  const lastUpload = list.length > 0 
    ? Math.max(...list.map(f => f.uploadedAt))
    : null;
  
  return {
    totalUploaded: list.length,
    lastUpload
  };
}

/**
 * Clear all upload history (use with caution)
 */
export function clearUploadHistory(): void {
  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem(UPLOADED_FILES_KEY);
}
