# KG RAG WebUI Enhancement Proposal

## 1. Error Handling

### Current Issue
No global error handling - errors may fail silently.

### Implementation Plan

```typescript
// src/utils/errorHandler.ts

/**
 * Global error handler with user-friendly messages
 */
export function initGlobalErrorHandler(): void {
  // Uncaught errors
  window.onerror = (message, source, lineno, colno, error) => {
    console.error('[Global Error]', { message, source, lineno, colno, error });
    
    // Show user-friendly toast
    showToast('An unexpected error occurred. Please refresh the page.', 'error');
    return false;
  };
  
  // Unhandled promise rejections
  window.onunhandledrejection = (event) => {
    console.error('[Unhandled Rejection]', event.reason);
    showToast('Something went wrong. Please try again.', 'error');
  };
}

/**
 * Toast notification system
 */
export function showToast(message: string, type: 'success' | 'error' | 'warning' = 'info'): void {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  
  setTimeout(() => toast.classList.add('show'), 10);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 5000);
}
```

### Effort: **Small** (1-2 hours)

---

## 2. Loading States

### Current Issue
Inconsistent loading indicators - some areas show spinners, others don't.

### Implementation Plan

```typescript
// src/components/LoadingOverlay.ts

/**
 * Loading overlay component
 */
export function showLoadingOverlay(message = 'Loading...'): void {
  const overlay = document.createElement('div');
  overlay.id = 'loading-overlay';
  overlay.innerHTML = `
    <div class="loading-spinner"></div>
    <p>${escapeHtml(message)}</p>
  `;
  document.body.appendChild(overlay);
}

export function hideLoadingOverlay(): void {
  document.getElementById('loading-overlay')?.remove();
}

// Usage in components:
async function handleQuery() {
  showLoadingOverlay('Searching knowledge base...');
  try {
    const result = await sendQuery({ message });
    showResult(result);
  } finally {
    hideLoadingOverlay();
  }
}
```

### Skeleton Loader for Stats

```typescript
// src/components/SkeletonStats.ts

export function getSkeletonStatsHTML(): string {
  return `
    <div class="skeleton-card">
      <div class="skeleton skeleton-title"></div>
      <div class="skeleton skeleton-value"></div>
    </div>
    `.repeat(4);
}
```

### Effort: **Medium** (3-4 hours)

---

## 3. Accessibility (a11y)

### Current Issue
Missing ARIA labels and keyboard navigation.

### Implementation Plan

```typescript
// Add to buttons in components:
// Before: <button>
// After: <button aria-label="Upload files" tabindex="0">

// Keyboard navigation handler
export function initKeyboardNav(): void {
  document.addEventListener('keydown', (e) => {
    // Tab through elements
    if (e.key === 'Tab') {
      document.body.classList.add('keyboard-mode');
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
      closeAllModals();
    }
    
    // Enter/Space to activate buttons
    if ((e.key === 'Enter' || e.key === ' ') && document.activeElement?.matches('.btn')) {
      (document.activeElement as HTMLButtonElement).click();
    }
  });
}
```

### HTML Improvements

```html
<!-- Add to all interactive elements -->
<button 
  aria-label="Upload files to ingest"
  aria-describedby="file-input-desc"
  tabindex="0"
  role="button"
>
  📥 Ingest
</button>

<span id="file-input-desc" class="sr-only">
  Select files from your computer to add to the knowledge base
</span>
```

### CSS for Keyboard Focus

```css
/* Visible focus indicator */
:focus-visible {
  outline: 3px solid #00d4ff;
  outline-offset: 2px;
}

.keyboard-mode *:focus {
  outline: 3px solid #00d4ff;
}
```

### Effort: **Medium** (4-5 hours)

---

## 4. Testing Strategy

### Current Issue
Tests are scaffolded but not implemented.

### Implementation Plan

#### Unit Tests (Vitest)

```typescript
// tests/helpers.test.ts
import { describe, it, expect } from 'vitest';
import { escapeHtml, formatFileSize, truncate } from '../src/utils/helpers';

describe('escapeHtml', () => {
  it('escapes HTML tags', () => {
    expect(escapeHtml('<script>alert(1)</script>')).toBe('&lt;script&gt;alert(1)&lt;/script&gt;');
  });
  
  it('preserves text content', () => {
    expect(escapeHtml('Hello World')).toBe('Hello World');
  });
});

describe('formatFileSize', () => {
  it('formats bytes', () => {
    expect(formatFileSize(500)).toBe('500 B');
  });
  
  it('formats KB', () => {
    expect(formatFileSize(1024)).toBe('1.0 KB');
  });
});
```

#### E2E Tests (Playwright)

```typescript
// tests/e2e/app.spec.ts
import { test, expect } from '@playwright/test';

test.describe('KG RAG WebUI', () => {
  test('loads main page', async ({ page }) => {
    await page.goto('http://localhost:8081');
    await expect(page.locator('h1')).toContainText('LightRAG');
  });
  
  test('shows stats after load', async ({ page }) => {
    await page.goto('http://localhost:8081');
    await page.waitForSelector('.stat-box', { timeout: 10000 });
    const stats = await page.locator('.stat-number').allTextContents();
    expect(stats.length).toBeGreaterThan(0);
  });
  
  test('can run query', async ({ page }) => {
    await page.goto('http://localhost:8081');
    await page.fill('#queryText', 'test');
    await page.click('#runQueryBtn');
    await page.waitForSelector('#queryResult', { timeout: 60000 });
  });
});
```

### Run Commands

```bash
# Unit tests
npm run test

# E2E tests
npx playwright test

# With coverage
npm run test:coverage
```

### Effort: **Large** (8-10 hours)

---

## Summary

| Enhancement | Effort | Priority |
|-------------|--------|----------|
| Error Handling | Small | High |
| Loading States | Medium | High |
| Accessibility | Medium | Medium |
| Testing | Large | Medium |

**Recommended Order:**
1. Error Handling (quick win)
2. Loading States (UX improvement)
3. Accessibility (compliance)
4. Testing (long-term maintainability)

---

## Implementation Files to Create/Modify

1. `src/utils/errorHandler.ts` - NEW
2. `src/components/LoadingOverlay.ts` - NEW
3. `src/components/SkeletonStats.ts` - NEW
4. `src/main.ts` - Add init calls
5. `src/styles.css` - Add loading/a11y styles
6. `tests/helpers.test.ts` - IMPLEMENT
7. `tests/e2e/app.spec.ts` - IMPLEMENT
