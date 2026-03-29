/**
 * Central application state store
 * Simple state management without external libraries
 */

import type { KGStats, DocStats } from '@/api';

interface AppState {
  // Stats
  kgStats: KGStats | null;
  docStats: DocStats | null;
  lastStatsUpdate: number | null;
  
  // Upload state
  selectedFiles: File[];
  folderFiles: File[];
  selectedQueryFiles: File[];
  isUploading: boolean;
  uploadProgress: number;
  
  // Query state
  activeQueryController: AbortController | null;
  isQuerying: boolean;
  
  // Config
  statsInterval: ReturnType<typeof setInterval> | null;
}

// Initial state
const state: AppState = {
  kgStats: null,
  docStats: null,
  lastStatsUpdate: null,
  selectedFiles: [],
  folderFiles: [],
  selectedQueryFiles: [],
  isUploading: false,
  uploadProgress: 0,
  activeQueryController: null,
  isQuerying: false,
  statsInterval: null,
};

// Listeners for state changes
const listeners = new Set<() => void>();

/**
 * Subscribe to state changes
 */
export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Notify all listeners
 */
function notify(): void {
  listeners.forEach(l => l());
}

// Getters
export const getState = () => ({ ...state });

export const getKGStats = () => state.kgStats;
export const getDocStats = () => state.docStats;
export const getSelectedFiles = () => [...state.selectedFiles];
export const getFolderFiles = () => [...state.folderFiles];
export const getSelectedQueryFiles = () => [...state.selectedQueryFiles];
export const isUploading = () => state.isUploading;
export const getUploadProgress = () => state.uploadProgress;
export const isQuerying = () => state.isQuerying;

// Setters
export function setKGStats(stats: KGStats): void {
  state.kgStats = stats;
  state.lastStatsUpdate = Date.now();
  notify();
}

export function setDocStats(stats: DocStats): void {
  state.docStats = stats;
  notify();
}

export function setSelectedFiles(files: File[]): void {
  state.selectedFiles = [...files];
  notify();
}

export function addSelectedFile(file: File): void {
  // Check for duplicates by name and size
  const exists = state.selectedFiles.some(
    f => f.name === file.name && f.size === file.size
  );
  if (!exists) {
    state.selectedFiles.push(file);
    notify();
  }
}

export function removeSelectedFile(index: number): void {
  state.selectedFiles.splice(index, 1);
  notify();
}

export function clearSelectedFiles(): void {
  state.selectedFiles = [];
  notify();
}

export function setFolderFiles(files: File[]): void {
  state.folderFiles = [...files];
  notify();
}

export function setSelectedQueryFiles(files: File[]): void {
  state.selectedQueryFiles = [...files];
  notify();
}

export function addSelectedQueryFile(file: File): void {
  const exists = state.selectedQueryFiles.some(
    f => f.name === file.name && f.size === file.size
  );
  if (!exists) {
    state.selectedQueryFiles.push(file);
    notify();
  }
}

export function removeSelectedQueryFile(index: number): void {
  state.selectedQueryFiles.splice(index, 1);
  notify();
}

export function clearSelectedQueryFiles(): void {
  state.selectedQueryFiles = [];
  notify();
}

export function setIsUploading(uploading: boolean): void {
  state.isUploading = uploading;
  notify();
}

export function setUploadProgress(progress: number): void {
  state.uploadProgress = progress;
  notify();
}

export function setActiveQueryController(controller: AbortController | null): void {
  state.activeQueryController = controller;
  notify();
}

export function cancelActiveQuery(): void {
  if (state.activeQueryController) {
    state.activeQueryController.abort();
    state.activeQueryController = null;
    state.isQuerying = false;
    notify();
  }
}

export function setIsQuerying(querying: boolean): void {
  state.isQuerying = querying;
  notify();
}

export function setStatsInterval(interval: ReturnType<typeof setInterval> | null): void {
  // Clear existing interval
  if (state.statsInterval) {
    clearInterval(state.statsInterval);
  }
  state.statsInterval = interval;
}

export function clearAllTimers(): void {
  if (state.statsInterval) {
    clearInterval(state.statsInterval);
    state.statsInterval = null;
  }
  cancelActiveQuery();
}

/**
 * Cleanup on app exit
 */
export function cleanup(): void {
  clearAllTimers();
  listeners.clear();
}
