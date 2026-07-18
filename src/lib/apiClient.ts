/**
 * API Client
 * 
 * Centralized API client with retry logic, timeout handling,
 * request/response interceptors, and error standardization.
 */

import { supabase } from './supabase';

// Types
export interface ApiResponse<T> {
  data: T | null;
  error: ApiError | null;
  status: number;
}

export interface ApiError {
  message: string;
  code?: string;
  status?: number;
  details?: unknown;
}

export interface RequestConfig {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  headers?: Record<string, string>;
}

// Default configuration
const DEFAULT_TIMEOUT = 10000;
const DEFAULT_RETRIES = 3;
const DEFAULT_RETRY_DELAY = 1000;

/**
 * Sleep utility for retry delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Check if error is retryable
 */
function isRetryable(error: ApiError): boolean {
  // Network errors
  if (!error.status) return true;
  
  // 5xx server errors and 429 rate limiting
  if (error.status >= 500 || error.status === 429) return true;
  
  // Network timeout
  if (error.message.includes('timeout')) return true;
  
  return false;
}

/**
 * Create standardized error object
 */
function createError(error: unknown, status?: number): ApiError {
  if (error instanceof Error) {
    return {
      message: error.message || 'An unexpected error occurred',
      status,
    };
  }
  return {
    message: 'An unexpected error occurred',
    status,
  };
}

/**
 * Fetch with timeout
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeout: number
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Request timeout after ${timeout}ms`);
    }
    throw error;
  }
}

/**
 * Request with retry logic
 */
async function requestWithRetry<T>(
  url: string,
  options: RequestInit,
  config: RequestConfig
): Promise<ApiResponse<T>> {
  const { timeout = DEFAULT_TIMEOUT, retries = DEFAULT_RETRIES, retryDelay = DEFAULT_RETRY_DELAY } = config;
  
  let lastError: ApiError | null = null;
  
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetchWithTimeout(url, options, timeout);
      
      // Handle HTTP errors
      if (!response.ok) {
        let errorData: { message?: string; code?: string; details?: unknown } = {};
        try {
          errorData = await response.json();
        } catch {
          // Response might not be JSON
        }
        
        const error: ApiError = {
          message: errorData.message || `HTTP error ${response.status}`,
          code: errorData.code,
          status: response.status,
          details: errorData.details,
        };
        
        // Don't retry client errors (4xx) except 429
        if (response.status >= 400 && response.status < 500 && response.status !== 429) {
          return { data: null, error, status: response.status };
        }
        
        lastError = error;
        if (attempt < retries && isRetryable(error)) {
          await sleep(retryDelay * (attempt + 1)); // Exponential backoff
          continue;
        }
        
        return { data: null, error, status: response.status };
      }
      
      // Parse response
      const data = await response.json();
      return { data, error: null, status: response.status };
      
    } catch (error) {
      lastError = createError(error);
      
      if (attempt < retries && isRetryable(lastError)) {
        await sleep(retryDelay * (attempt + 1));
        continue;
      }
      
      return { data: null, error: lastError, status: 0 };
    }
  }
  
  return { data: null, error: lastError || createError(new Error('Max retries exceeded')), status: 0 };
}

/**
 * API Client class
 */
export class ApiClient {
  private baseUrl: string;
  private defaultHeaders: Record<string, string>;

  constructor(baseUrl: string = '/api') {
    this.baseUrl = baseUrl;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Add auth token to requests
   */
  private async getAuthHeaders(): Promise<Record<string, string>> {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      return { Authorization: `Bearer ${session.access_token}` };
    }
    return {};
  }

  /**
   * Make GET request
   */
  async get<T>(endpoint: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    const authHeaders = await this.getAuthHeaders();
    
    return requestWithRetry<T>(
      `${this.baseUrl}${endpoint}`,
      {
        method: 'GET',
        headers: {
          ...this.defaultHeaders,
          ...authHeaders,
          ...config?.headers,
        },
      },
      config || {}
    );
  }

  /**
   * Make POST request
   */
  async post<T>(endpoint: string, body: unknown, config?: RequestConfig): Promise<ApiResponse<T>> {
    const authHeaders = await this.getAuthHeaders();
    
    return requestWithRetry<T>(
      `${this.baseUrl}${endpoint}`,
      {
        method: 'POST',
        headers: {
          ...this.defaultHeaders,
          ...authHeaders,
          ...config?.headers,
        },
        body: JSON.stringify(body),
      },
      config || {}
    );
  }

  /**
   * Make PUT request
   */
  async put<T>(endpoint: string, body: unknown, config?: RequestConfig): Promise<ApiResponse<T>> {
    const authHeaders = await this.getAuthHeaders();
    
    return requestWithRetry<T>(
      `${this.baseUrl}${endpoint}`,
      {
        method: 'PUT',
        headers: {
          ...this.defaultHeaders,
          ...authHeaders,
          ...config?.headers,
        },
        body: JSON.stringify(body),
      },
      config || {}
    );
  }

  /**
   * Make PATCH request
   */
  async patch<T>(endpoint: string, body: unknown, config?: RequestConfig): Promise<ApiResponse<T>> {
    const authHeaders = await this.getAuthHeaders();
    
    return requestWithRetry<T>(
      `${this.baseUrl}${endpoint}`,
      {
        method: 'PATCH',
        headers: {
          ...this.defaultHeaders,
          ...authHeaders,
          ...config?.headers,
        },
        body: JSON.stringify(body),
      },
      config || {}
    );
  }

  /**
   * Make DELETE request
   */
  async delete<T>(endpoint: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    const authHeaders = await this.getAuthHeaders();
    
    return requestWithRetry<T>(
      `${this.baseUrl}${endpoint}`,
      {
        method: 'DELETE',
        headers: {
          ...this.defaultHeaders,
          ...authHeaders,
          ...config?.headers,
        },
      },
      config || {}
    );
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// Export convenience functions
export const api = {
  get: <T>(endpoint: string, config?: RequestConfig) => apiClient.get<T>(endpoint, config),
  post: <T>(endpoint: string, body: unknown, config?: RequestConfig) => apiClient.post<T>(endpoint, body, config),
  put: <T>(endpoint: string, body: unknown, config?: RequestConfig) => apiClient.put<T>(endpoint, body, config),
  patch: <T>(endpoint: string, body: unknown, config?: RequestConfig) => apiClient.patch<T>(endpoint, body, config),
  delete: <T>(endpoint: string, config?: RequestConfig) => apiClient.delete<T>(endpoint, config),
};

export default api;
