/**
 * Vitest Setup File
 * Global test configuration and mocks
 */

import { afterEach, vi } from 'vitest';

// Mock environment variables
Object.defineProperty(import.meta, 'env', {
  value: {
    VITE_SUPABASE_URL: 'https://test.supabase.co',
    VITE_SUPABASE_ANON_KEY: 'test-anon-key',
    DEV: true,
    PROD: false,
  },
  writable: true,
});

// Global test timeout
const DEFAULT_TIMEOUT = 10000;
vi.setConfig({
  testTimeout: DEFAULT_TIMEOUT,
  hookTimeout: DEFAULT_TIMEOUT,
});

// Cleanup after each test
afterEach(() => {
  // Clear all mocks
  vi.clearAllMocks();
});
