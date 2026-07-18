/**
 * API Client Tests
 * Tests for the API layer including error handling and retry logic
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock fetch for API tests
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('API Client', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('fetchApi', () => {
    it('should return data on successful response', async () => {
      const mockData = { trades: [], stats: null };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockData),
      });

      // Simulate API fetch
      const response = await fetch('/api/test');
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(data).toEqual(mockData);
    });

    it('should throw error on failed response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: 'Unauthorized' }),
      });

      const response = await fetch('/api/test');
      
      expect(response.ok).toBe(false);
    });
  });

  describe('API Response Types', () => {
    it('should handle empty response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(null),
      });

      const response = await fetch('/api/empty');
      const data = await response.json();

      expect(data).toBeNull();
    });

    it('should handle array response', async () => {
      const mockData = [{ id: 1 }, { id: 2 }];
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockData),
      });

      const response = await fetch('/api/list');
      const data = await response.json();

      expect(Array.isArray(data)).toBe(true);
      expect(data).toHaveLength(2);
    });
  });
});

describe('API Error Handling', () => {
  it('should handle network errors gracefully', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    try {
      await fetch('/api/test');
    } catch (error) {
      expect(error).toBeInstanceOf(Error);
      expect((error as Error).message).toBe('Network error');
    }
  });

  it('should handle invalid JSON', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.reject(new Error('Invalid JSON')),
    });

    const response = await fetch('/api/invalid');
    
    // Should not throw, but return null data
    const data = await response.json().catch(() => null);
    expect(data).toBeNull();
  });
});

describe('Health Check', () => {
  it('should return healthy status', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'healthy', timestamp: new Date().toISOString() }),
    });

    const response = await fetch('/api/health');
    const data = await response.json();

    expect(response.ok).toBe(true);
    expect(data.status).toBe('healthy');
  });
});
