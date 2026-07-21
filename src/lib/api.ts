/**
 * SmartPip Unified API Client
 * 
 * Consolidated API client with:
 * - Supabase Edge Function integration
 * - Retry logic with exponential backoff
 * - Timeout handling
 * - All trading and platform endpoints
 * 
 * @version 4.0.0
 */

import { supabase } from './supabase';

// ============================================
// Configuration
// ============================================

const EDGE_FUNCTION_URL = `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/trading-api`;
const API_V2_BASE = '/api/v2';

// Retry configuration
const DEFAULT_TIMEOUT = 10000;
const DEFAULT_RETRIES = 3;
const DEFAULT_RETRY_DELAY = 1000;

// ============================================
// Types
// ============================================

export interface ApiResponse<T = unknown> {
  data: T | null;
  error: string | null;
  status: number;
}

export interface RequestConfig {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  headers?: Record<string, string>;
}

export interface WorkspaceListResponse {
  workspaces: Array<{
    id: string;
    type: string;
    name: string;
    description: string;
    icon: string;
    route: string;
    order: number;
    is_default: boolean;
  }>;
  favorites: string[];
}

// ============================================
// Utilities
// ============================================

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetryable(error: { status?: number; message?: string }): boolean {
  if (!error.status) return true;
  if (error.status >= 500 || error.status === 429) return true;
  if (error.message?.includes('timeout')) return true;
  return false;
}

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

// ============================================
// Core Fetch Function
// ============================================

async function apiFetch<T = unknown>(
  url: string,
  options: RequestInit = {},
  config: RequestConfig = {}
): Promise<ApiResponse<T>> {
  const {
    timeout = DEFAULT_TIMEOUT,
    retries = DEFAULT_RETRIES,
    retryDelay = DEFAULT_RETRY_DELAY,
  } = config;

  // Get auth token
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token ?? import.meta.env.VITE_SUPABASE_ANON_KEY;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers as Record<string, string>,
  };

  let lastError: string | null = null;

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const response = await fetchWithTimeout(url, {
        ...options,
        headers,
      }, timeout);

      if (!response.ok) {
        let errorData: { error?: string; detail?: string } = {};
        try {
          errorData = await response.json();
        } catch {
          // Response might not be JSON
        }
        
        const errorMsg = errorData.error || errorData.detail || `HTTP ${response.status}`;
        
        // Don't retry client errors (except 429)
        if (response.status >= 400 && response.status < 500 && response.status !== 429) {
          return { data: null, error: errorMsg, status: response.status };
        }
        
        lastError = errorMsg;
        if (attempt < retries && isRetryable({ status: response.status })) {
          await sleep(retryDelay * (attempt + 1));
          continue;
        }
        
        return { data: null, error: errorMsg, status: response.status };
      }

      const data = await response.json();
      return { data, error: null, status: response.status };

    } catch (error) {
      lastError = error instanceof Error ? error.message : 'Unknown error';
      
      if (attempt < retries && isRetryable({ message: lastError })) {
        await sleep(retryDelay * (attempt + 1));
        continue;
      }
      
      return { data: null, error: lastError, status: 0 };
    }
  }

  return { data: null, error: lastError || 'Max retries exceeded', status: 0 };
}

// ============================================
// Edge Function API (trading-api)
// ============================================

const edgeFunctionFetch = <T = unknown>(
  path: string,
  options: RequestInit = {},
  config: RequestConfig = {}
): Promise<ApiResponse<T>> => {
  const url = `${EDGE_FUNCTION_URL}/${path}`;
  return apiFetch<T>(url, options, config);
};

// ============================================
// V2 API Fetch
// ============================================

const v2Fetch = <T = unknown>(
  path: string,
  options: RequestInit = {},
  config: RequestConfig = {}
): Promise<ApiResponse<T>> => {
  const url = `${window.location.origin}${API_V2_BASE}${path}`;
  return apiFetch<T>(url, options, config);
};

// ============================================
// API Exports
// ============================================

export const api = {
  // Core trading operations (Edge Function)
  getTrades: () => edgeFunctionFetch('trades'),
  getStatistics: () => edgeFunctionFetch('statistics'),
  getSettings: () => edgeFunctionFetch('settings'),
  updateSettings: (data: Record<string, unknown>) =>
    edgeFunctionFetch('settings', { method: 'PATCH', body: JSON.stringify(data) }),
  getAuditLog: () => edgeFunctionFetch('audit'),
  logAudit: (data: { action: string; actor: string; ip_address?: string; details?: Record<string, unknown> }) =>
    edgeFunctionFetch('audit', { method: 'POST', body: JSON.stringify(data) }),
  health: () => edgeFunctionFetch('health'),

  // Plugin API (v2)
  plugins: {
    list: () => v2Fetch('/plugins/'),
    load: (pluginId: string, pluginClass: string, config?: object, enabled?: boolean) =>
      v2Fetch('/plugins/load', {
        method: 'POST',
        body: JSON.stringify({ pluginId, pluginClass, config, enabled }),
      }),
    enable: (pluginId: string) =>
      v2Fetch(`/plugins/${pluginId}/enable`, { method: 'POST' }),
    disable: (pluginId: string) =>
      v2Fetch(`/plugins/${pluginId}/disable`, { method: 'POST' }),
    reload: (pluginId: string) =>
      v2Fetch(`/plugins/${pluginId}/reload`, { method: 'POST' }),
    uninstall: (pluginId: string) =>
      v2Fetch(`/plugins/${pluginId}`, { method: 'DELETE' }),
    getConfig: (pluginId: string) =>
      v2Fetch(`/plugins/${pluginId}/config`),
    updateConfig: (pluginId: string, config: object) =>
      v2Fetch(`/plugins/${pluginId}/config`, {
        method: 'PUT',
        body: JSON.stringify(config),
      }),
  },

  // Marketplace API (v2)
  marketplace: {
    list: (params?: { status?: string; tags?: string; search?: string }) => {
      const query = new URLSearchParams(params as Record<string, string>).toString();
      return v2Fetch(`/marketplace/${query ? `?${query}` : ''}`);
    },
    search: (q: string, maxResults?: number) =>
      v2Fetch(`/marketplace/search?q=${encodeURIComponent(q)}${maxResults ? `&max_results=${maxResults}` : ''}`),
    install: (pluginId: string, version?: string) =>
      v2Fetch(`/marketplace/${pluginId}/install`, {
        method: 'POST',
        body: JSON.stringify({ version }),
      }),
    uninstall: (pluginId: string) =>
      v2Fetch(`/marketplace/${pluginId}/uninstall`, { method: 'POST' }),
    update: (pluginId: string, version: string) =>
      v2Fetch(`/marketplace/${pluginId}/update`, {
        method: 'POST',
        body: JSON.stringify({ version }),
      }),
    checkUpdates: () => v2Fetch('/marketplace/updates'),
    getInstalled: () => v2Fetch('/marketplace/installed'),
    getFavorites: () => v2Fetch('/marketplace/favorites'),
    addFavorite: (pluginId: string) =>
      v2Fetch(`/marketplace/${pluginId}/favorite`, { method: 'POST' }),
    removeFavorite: (pluginId: string) =>
      v2Fetch(`/marketplace/${pluginId}/favorite`, { method: 'DELETE' }),
  },

  // Orchestrator API (v2)
  orchestrator: {
    getConfig: () => v2Fetch('/orchestrator/config'),
    updateConfig: (config: object) =>
      v2Fetch('/orchestrator/config', {
        method: 'PUT',
        body: JSON.stringify(config),
      }),
    getSignals: (limit?: number, direction?: string) => {
      const params = new URLSearchParams();
      if (limit) params.set('limit', limit.toString());
      if (direction) params.set('direction', direction);
      const query = params.toString();
      return v2Fetch(`/orchestrator/signals${query ? `?${query}` : ''}`);
    },
    getStatistics: () => v2Fetch('/orchestrator/statistics'),
    reset: () => v2Fetch('/orchestrator/reset', { method: 'POST' }),
  },

  // Account API (v2)
  accounts: {
    getStatus: () => v2Fetch('/accounts/status'),
    login: (apiToken: string) =>
      v2Fetch('/accounts/login', {
        method: 'POST',
        body: JSON.stringify({ api_token: apiToken }),
      }),
    logout: () => v2Fetch('/accounts/logout', { method: 'POST' }),
    listAccounts: () => v2Fetch('/accounts/accounts'),
    getAccount: (accountId: string) =>
      v2Fetch(`/accounts/accounts/${accountId}`),
    switchAccount: (accountId: string) =>
      v2Fetch(`/accounts/accounts/${accountId}/switch`, { method: 'POST' }),
    switchToDemo: () => v2Fetch('/accounts/switch/demo', { method: 'POST' }),
    switchToReal: () => v2Fetch('/accounts/switch/real', { method: 'POST' }),
    getBalances: () => v2Fetch('/accounts/balances'),
  },

  // Workspace API (v2)
  workspaces: {
    list: () => v2Fetch<WorkspaceListResponse>('/workspaces/'),
    get: (workspaceId: string) =>
      v2Fetch(`/workspaces/${workspaceId}`),
    addFavorite: (workspaceId: string) =>
      v2Fetch(`/workspaces/${workspaceId}/favorites`, { method: 'POST' }),
    removeFavorite: (workspaceId: string) =>
      v2Fetch(`/workspaces/${workspaceId}/favorites`, { method: 'DELETE' }),
    getFavorites: () => v2Fetch('/workspaces/favorites'),
    getCurrent: () => v2Fetch('/workspaces/current'),
    activate: (workspaceId: string) =>
      v2Fetch(`/workspaces/${workspaceId}/activate`, { method: 'POST' }),
    getPreferences: (workspaceId: string) =>
      v2Fetch(`/workspaces/${workspaceId}/preferences`),
    updatePreferences: (workspaceId: string, preferences: object) =>
      v2Fetch(`/workspaces/${workspaceId}/preferences`, {
        method: 'PUT',
        body: JSON.stringify(preferences),
      }),
  },

  // Risk API (v2)
  risk: {
    getStatus: () => v2Fetch('/risk/status'),
    getLimits: () => v2Fetch('/risk/limits'),
    updateLimits: (limits: object) =>
      v2Fetch('/risk/limits', {
        method: 'PUT',
        body: JSON.stringify(limits),
      }),
    validateTrade: (params: {
      pluginId: string;
      market: string;
      direction: string;
      amount: number;
      balance: number;
    }) => v2Fetch('/risk/validate', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
    getMetrics: () => v2Fetch('/risk/metrics'),
    getEvents: (params?: { since?: string; level?: string; limit?: number }) => {
      const query = new URLSearchParams(params as Record<string, string>).toString();
      return v2Fetch(`/risk/events${query ? `?${query}` : ''}`);
    },
    reset: () => v2Fetch('/risk/reset', { method: 'POST' }),
    emergencyStop: (reason: string) =>
      v2Fetch('/risk/emergency-stop', {
        method: 'POST',
        body: JSON.stringify({ reason }),
      }),
    getKillSwitchStatus: () => v2Fetch('/risk/kill-switch'),
    resetKillSwitch: () =>
      v2Fetch('/risk/kill-switch/reset', { method: 'POST' }),
  },

  // Cloud Sync API (v2)
  sync: {
    getStatus: () => v2Fetch('/sync/status'),
    sync: () => v2Fetch('/sync/sync', { method: 'POST' }),
    getConflicts: () => v2Fetch('/sync/conflicts'),
    resolveConflict: (key: string, resolution: 'local' | 'remote') =>
      v2Fetch(`/sync/conflicts/${key}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ resolution }),
      }),
    getData: () => v2Fetch('/sync/data'),
    updateData: (key: string, data: object) =>
      v2Fetch(`/sync/data/${key}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },

  // Generic request methods for extensibility
  get: <T = unknown>(url: string, config?: RequestConfig) => v2Fetch<T>(url, {}, config),
  post: <T = unknown>(url: string, body: unknown, config?: RequestConfig) =>
    v2Fetch<T>(url, { method: 'POST', body: JSON.stringify(body) }, config),
  put: <T = unknown>(url: string, body: unknown, config?: RequestConfig) =>
    v2Fetch<T>(url, { method: 'PUT', body: JSON.stringify(body) }, config),
  patch: <T = unknown>(url: string, body: unknown, config?: RequestConfig) =>
    v2Fetch<T>(url, { method: 'PATCH', body: JSON.stringify(body) }, config),
  delete: <T = unknown>(url: string, config?: RequestConfig) =>
    v2Fetch<T>(url, { method: 'DELETE' }, config),
};

export default api;
