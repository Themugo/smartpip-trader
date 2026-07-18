/**
 * @deprecated This file is deprecated
 * 
 * All API client functionality has been consolidated into api.ts
 * The unified API client now includes:
 * - Retry logic with exponential backoff
 * - Timeout handling
 * - Request/response interceptors
 * - Error standardization
 * - All trading and platform endpoints
 * 
 * Please update imports to use '../lib/api' instead
 * 
 * @removed_in 5.0.0
 */

// Re-export types and api from consolidated API
export type { ApiResponse, RequestConfig } from './api';
export { api, api as apiClient } from './api';

export default api;
