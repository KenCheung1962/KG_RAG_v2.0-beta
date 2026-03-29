/**
 * DOM manipulation utilities
 */

/**
 * Get element by ID with type safety
 */
export function getElement<T extends HTMLElement>(id: string): T | null {
  return document.getElementById(id) as T | null;
}

/**
 * Set text content safely (escaped)
 */
export function setText(elementId: string, text: string): void {
  const el = getElement(elementId);
  if (el) el.textContent = text;
}

/**
 * Set HTML content (use with caution - XSS risk)
 */
export function setHTML(elementId: string, html: string): void {
  const el = getElement(elementId);
  if (el) el.innerHTML = html;
}

/**
 * Show/hide element
 */
export function setVisible(elementId: string, visible: boolean): void {
  const el = getElement(elementId);
  if (el) el.style.display = visible ? 'block' : 'none';
}

/**
 * Add/remove CSS class
 */
export function toggleClass(elementId: string, className: string, force?: boolean): void {
  const el = getElement(elementId);
  if (el) el.classList.toggle(className, force);
}

/**
 * Set button disabled state
 */
export function setDisabled(elementId: string, disabled: boolean): void {
  const el = getElement<HTMLButtonElement>(elementId);
  if (el) el.disabled = disabled;
}

/**
 * Update progress bar
 */
export function setProgress(elementId: string, percent: number): void {
  const el = getElement(elementId);
  if (el) el.style.width = `${percent}%`;
}

/**
 * Create a spinner element
 */
export function createSpinner(): HTMLSpanElement {
  const spinner = document.createElement('span');
  spinner.className = 'spinner';
  return spinner;
}

/**
 * Show tab content
 */
export function showTab(tabId: string, clickedTab?: HTMLElement): void {
  // Hide all tabs
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  
  // Activate clicked tab
  if (clickedTab) {
    clickedTab.classList.add('active');
  } else {
    document.querySelector(`[data-tab="${tabId}"]`)?.classList.add('active');
  }
  
  // Show content
  getElement(tabId)?.classList.add('active');
}
