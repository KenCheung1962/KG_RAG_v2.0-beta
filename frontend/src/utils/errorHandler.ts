/**
 * Global Error Handler with Toast Notifications
 * Provides centralized error handling and user notifications
 */

import { formatError } from './helpers';

/**
 * Toast types for different notification levels
 */
export type ToastType = 'success' | 'error' | 'warning' | 'info';

/**
 * Toast notification options
 */
export interface ToastOptions {
  duration?: number;  // milliseconds, default 4000
  dismissible?: boolean;
}

/**
 * Create and show a toast notification
 */
export function showToast(
  message: string,
  type: ToastType = 'info',
  options: ToastOptions = {}
): HTMLElement {
  const { duration = 4000, dismissible = true } = options;
  
  // Remove existing toasts of same type to avoid clutter
  const existingToasts = document.querySelectorAll(`.toast-container .toast.${type}`);
  existingToasts.forEach(toast => toast.remove());
  
  // Create toast container if not exists
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    container.setAttribute('role', 'region');
    container.setAttribute('aria-label', 'Notifications');
    container.setAttribute('aria-live', 'polite');
    document.body.appendChild(container);
  }
  
  // Create toast element
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  
  // Icon mapping
  const icons: Record<ToastType, string> = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  };
  
  toast.innerHTML = `
    <span class="toast-icon">${icons[type]}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
    ${dismissible ? '<button class="toast-close" aria-label="Dismiss notification">×</button>' : ''}
  `;
  
  // Add close handler
  if (dismissible) {
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn?.addEventListener('click', () => removeToast(toast));
  }
  
  container.appendChild(toast);
  
  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.add('toast-show');
  });
  
  // Auto dismiss
  if (duration > 0) {
    setTimeout(() => removeToast(toast), duration);
  }
  
  // Focus for accessibility
  toast.setAttribute('tabindex', '-1');
  toast.focus();
  
  return toast;
}

/**
 * Remove toast with animation
 */
function removeToast(toast: HTMLElement): void {
  toast.classList.remove('toast-show');
  toast.classList.add('toast-hide');
  
  toast.addEventListener('transitionend', () => {
    toast.remove();
    
    // Clean up container if empty
    const container = document.querySelector('.toast-container');
    if (container && container.children.length === 0) {
      container.remove();
    }
  }, { once: true });
}

/**
 * Show success toast
 */
export function showSuccess(message: string, options?: ToastOptions): void {
  showToast(message, 'success', options);
}

/**
 * Show error toast
 */
export function showError(message: string, options?: ToastOptions): void {
  showToast(message, 'error', options);
}

/**
 * Show warning toast
 */
export function showWarning(message: string, options?: ToastOptions): void {
  showToast(message, 'warning', options);
}

/**
 * Show info toast
 */
export function showInfo(message: string, options?: ToastOptions): void {
  showToast(message, 'info', options);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Global error handler for uncaught errors
 */
export function initGlobalErrorHandler(): void {
  // Handle uncaught JavaScript errors
  window.onerror = (
    message: Event | string,
    source?: string,
    lineno?: number,
    colno?: number,
    error?: Error
  ): boolean => {
    const errorMsg = error instanceof Error 
      ? `${error.message}\n${error.stack}` 
      : String(message);
    
    console.error('🚨 Global Error:', {
      message: errorMsg,
      source,
      lineno,
      colno,
      error
    });
    
    // Show user-friendly error toast
    const userMessage = error instanceof Error 
      ? error.message 
      : 'An unexpected error occurred';
    
    showError(`Error: ${userMessage}`, { duration: 6000 });
    
    return false; // Let default error handling proceed
  };
  
  // Handle unhandled promise rejections
  window.onunhandledrejection = (event: PromiseRejectionEvent): void => {
    const reason = event.reason;
    const errorMsg = reason instanceof Error 
      ? `${reason.message}\n${reason.stack}` 
      : String(reason);
    
    console.error('🚨 Unhandled Promise Rejection:', {
      reason: errorMsg,
      promise: event.promise
    });
    
    // Show user-friendly error toast
    const userMessage = reason instanceof Error 
      ? reason.message 
      : 'An unexpected error occurred';
    
    showError(`Async Error: ${userMessage}`, { duration: 6000 });
    
    // Prevent default console error (optional)
    // event.preventDefault(); 
  };
  
  console.log('✅ Global error handlers initialized');
}

/**
 * Initialize toast styles dynamically
 * Call this once on app initialization
 */
export function initToastStyles(): void {
  if (document.getElementById('toast-styles')) return;
  
  const style = document.createElement('style');
  style.id = 'toast-styles';
  style.textContent = `
    .toast-container {
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 10000;
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-width: 400px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    .toast {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 18px;
      border-radius: 8px;
      background: rgba(30, 30, 40, 0.95);
      color: #fff;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
      backdrop-filter: blur(10px);
      opacity: 0;
      transform: translateX(100%);
      transition: opacity 0.3s ease, transform 0.3s ease;
    }
    
    .toast.toast-show {
      opacity: 1;
      transform: translateX(0);
    }
    
    .toast.toast-hide {
      opacity: 0;
      transform: translateX(100%);
    }
    
    .toast-icon {
      font-size: 18px;
      flex-shrink: 0;
    }
    
    .toast-message {
      flex: 1;
      font-size: 14px;
      line-height: 1.4;
      word-break: break-word;
    }
    
    .toast-close {
      background: none;
      border: none;
      color: rgba(255, 255, 255, 0.6);
      font-size: 20px;
      cursor: pointer;
      padding: 0 4px;
      line-height: 1;
      transition: color 0.2s;
      flex-shrink: 0;
    }
    
    .toast-close:hover {
      color: #fff;
    }
    
    .toast-success {
      border-left: 4px solid #4caf50;
    }
    
    .toast-error {
      border-left: 4px solid #f44336;
    }
    
    .toast-warning {
      border-left: 4px solid #ff9800;
    }
    
    .toast-info {
      border-left: 4px solid #00d4ff;
    }
    
    @media (max-width: 480px) {
      .toast-container {
        left: 10px;
        right: 10px;
        max-width: none;
      }
    }
  `;
  
  document.head.appendChild(style);
}

/**
 * Initialize the error handler module
 * Call this in your app's initialization
 */
export function initErrorHandler(): void {
  initToastStyles();
  initGlobalErrorHandler();
}

// Export default for convenience
export default {
  initErrorHandler,
  showToast,
  showSuccess,
  showError,
  showWarning,
  showInfo
};
