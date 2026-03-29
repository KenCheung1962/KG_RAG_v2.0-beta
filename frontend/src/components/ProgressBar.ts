/**
 * Progress bar component
 */

import { getElement } from '@/utils/dom';

interface ProgressState {
  percent: number;
  status: string;
  isActive: boolean;
}

let currentState: ProgressState = {
  percent: 0,
  status: '',
  isActive: false
};

/**
 * Initialize progress bar
 */
export function initProgressBar(containerId: string): void {
  const container = getElement(containerId);
  if (!container) return;
  
  container.innerHTML = `
    <div class="progress-container" style="display: none;">
      <div class="progress-bar">
        <div class="progress-fill" style="width: 0%"></div>
      </div>
      <div class="progress-status"></div>
    </div>
  `;
}

/**
 * Show progress bar
 */
export function showProgress(containerId: string): void {
  const container = getElement(containerId);
  const progressContainer = container?.querySelector('.progress-container');
  if (progressContainer) {
    (progressContainer as HTMLElement).style.display = 'block';
    currentState.isActive = true;
  }
}

/**
 * Hide progress bar
 */
export function hideProgress(containerId: string): void {
  const container = getElement(containerId);
  const progressContainer = container?.querySelector('.progress-container');
  if (progressContainer) {
    (progressContainer as HTMLElement).style.display = 'none';
    currentState.isActive = false;
    currentState.percent = 0;
  }
}

/**
 * Update progress
 */
export function updateProgress(
  containerId: string,
  percent: number,
  status?: string
): void {
  const container = getElement(containerId);
  const fill = container?.querySelector('.progress-fill');
  const statusEl = container?.querySelector('.progress-status');
  
  if (fill) {
    (fill as HTMLElement).style.width = `${percent}%`;
  }
  
  if (statusEl && status !== undefined) {
    statusEl.innerHTML = status;
  }
  
  currentState.percent = percent;
  if (status !== undefined) {
    currentState.status = status;
  }
}

/**
 * Set status with spinner
 */
export function setProgressStatus(
  containerId: string,
  message: string,
  showSpinner = true
): void {
  const spinner = showSpinner ? '<span class="spinner"></span>' : '';
  updateProgress(containerId, currentState.percent, 
    `${spinner}<span style="color: #00d4ff;">${message}</span>`);
}

/**
 * Check if upload is currently active
 */
export function isProgressActive(): boolean {
  return currentState.isActive;
}

/**
 * Get progress bar CSS
 */
export function getProgressCSS(): string {
  return `
    .progress-container {
      margin: 15px 0;
    }
    
    .progress-bar {
      width: 100%;
      height: 20px;
      background: rgba(255,255,255,0.1);
      border-radius: 10px;
      overflow: hidden;
    }
    
    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #00d4ff, #7b2ff7);
      transition: width 0.3s ease;
    }
    
    .progress-status {
      margin-top: 10px;
      font-size: 14px;
    }
    
    .spinner {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255,255,255,0.3);
      border-radius: 50%;
      border-top-color: #00d4ff;
      animation: spin 1s linear infinite;
      margin-right: 8px;
      vertical-align: middle;
    }
    
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `;
}
