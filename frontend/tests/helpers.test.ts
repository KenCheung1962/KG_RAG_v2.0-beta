/**
 * Tests for helper utilities
 */

import { describe, it, expect } from 'vitest';
import { escapeHtml, formatFileSize, truncate, exponentialBackoff } from '../src/utils/helpers';

describe('escapeHtml', () => {
  it('should escape HTML special characters', () => {
    expect(escapeHtml('<script>alert("xss")</script>')).toBe('&lt;script&gt;alert("xss")&lt;/script&gt;');
    expect(escapeHtml('Hello & World')).toBe('Hello &amp; World');
    expect(escapeHtml('A < B > C')).toBe('A &lt; B &gt; C');
  });

  it('should handle empty strings', () => {
    expect(escapeHtml('')).toBe('');
  });

  it('should handle strings without special characters', () => {
    expect(escapeHtml('Hello World')).toBe('Hello World');
  });
});

describe('formatFileSize', () => {
  it('should format bytes', () => {
    expect(formatFileSize(500)).toBe('500 B');
  });

  it('should format kilobytes', () => {
    expect(formatFileSize(1024)).toBe('1.0 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });

  it('should format megabytes', () => {
    expect(formatFileSize(1024 * 1024)).toBe('1.0 MB');
    expect(formatFileSize(2.5 * 1024 * 1024)).toBe('2.5 MB');
  });
});

describe('truncate', () => {
  it('should truncate long strings', () => {
    expect(truncate('Hello World', 5)).toBe('Hello...');
  });

  it('should not truncate short strings', () => {
    expect(truncate('Hi', 10)).toBe('Hi');
  });

  it('should handle exact length', () => {
    expect(truncate('Hello', 5)).toBe('Hello');
  });
});

describe('exponentialBackoff', () => {
  it('should increase delay exponentially', () => {
    expect(exponentialBackoff(0, 1000, 5000)).toBe(1000);
    expect(exponentialBackoff(1, 1000, 5000)).toBe(1500);
    expect(exponentialBackoff(2, 1000, 5000)).toBe(2250);
  });

  it('should respect max delay', () => {
    expect(exponentialBackoff(10, 1000, 5000)).toBe(5000);
  });
});
