/**
 * File list component for displaying selected files
 */

import { escapeHtml, formatFileSize } from '@/utils/helpers';

export interface FileListConfig {
  containerId: string;
  onRemove?: (index: number) => void;
  emptyText?: string;
}

/**
 * Render file list
 */
export function renderFileList(
  files: File[],
  config: FileListConfig
): void {
  const container = document.getElementById(config.containerId);
  if (!container) return;
  
  if (files.length === 0) {
    container.style.display = 'none';
    return;
  }
  
  container.style.display = 'block';
  
  const listHtml = files.map((file, index) => `
    <div class="file-item" data-index="${index}">
      <span class="file-name">${escapeHtml(file.name)}</span>
      <span class="file-size">${formatFileSize(file.size)}</span>
      ${config.onRemove ? `
        <button class="btn-remove" data-index="${index}" title="Remove">✕</button>
      ` : ''}
    </div>
  `).join('');
  
  container.innerHTML = `
    <strong>${config.emptyText || 'Selected files:'}</strong>
    <div class="file-list-content">${listHtml}</div>
  `;
  
  // Attach remove handlers
  if (config.onRemove) {
    container.querySelectorAll('.btn-remove').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const index = parseInt((btn as HTMLElement).dataset.index || '0', 10);
        config.onRemove?.(index);
      });
    });
  }
}

/**
 * Get file list CSS
 */
export function getFileListCSS(): string {
  return `
    .file-list {
      background: rgba(0,0,0,0.2);
      padding: 15px;
      border-radius: 8px;
      max-height: 200px;
      overflow-y: auto;
      margin: 10px 0;
    }
    
    .file-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px;
      border-bottom: 1px solid rgba(255,255,255,0.1);
      font-size: 13px;
    }
    
    .file-item:last-child {
      border-bottom: none;
    }
    
    .file-name {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    
    .file-size {
      color: #aaa;
      font-size: 12px;
    }
    
    .btn-remove {
      padding: 2px 8px;
      font-size: 12px;
      background: #f44336;
      border: none;
      border-radius: 3px;
      color: white;
      cursor: pointer;
    }
    
    .btn-remove:hover {
      opacity: 0.8;
    }
  `;
}
