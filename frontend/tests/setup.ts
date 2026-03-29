/**
 * Test setup file
 */

// Add any global test setup here
// For example: mocking, global stubs, etc.

// Mock fetch globally for tests
global.fetch = vi.fn();

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
});
