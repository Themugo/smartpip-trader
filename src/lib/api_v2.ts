/**
 * API v2 Client for Modular Trading Platform
 */

const API_BASE = '/api/v2';

interface ApiResponse<T = unknown> {
  data?: T;
  error?: string;
}

async function fetchApi<T = unknown>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return { error: data.detail || 'API request failed' };
    }

    return { data };
  } catch (error) {
    return { error: (error as Error).message };
  }
}

// Plugin API
export const pluginApi = {
  list: () => fetchApi('/plugins/'),
  
  load: (pluginId: string, pluginClass: string, config?: object, enabled?: boolean) =>
    fetchApi('/plugins/load', {
      method: 'POST',
      body: JSON.stringify({ pluginId, pluginClass, config, enabled }),
    }),
  
  enable: (pluginId: string) =>
    fetchApi(`/plugins/${pluginId}/enable`, { method: 'POST' }),
  
  disable: (pluginId: string) =>
    fetchApi(`/plugins/${pluginId}/disable`, { method: 'POST' }),
  
  reload: (pluginId: string) =>
    fetchApi(`/plugins/${pluginId}/reload`, { method: 'POST' }),
  
  uninstall: (pluginId: string) =>
    fetchApi(`/plugins/${pluginId}`, { method: 'DELETE' }),
  
  getConfig: (pluginId: string) =>
    fetchApi(`/plugins/${pluginId}/config`),
  
  updateConfig: (pluginId: string, config: object) =>
    fetchApi(`/plugins/${pluginId}/config`, {
      method: 'PUT',
      body: JSON.stringify(config),
    }),
};

// Marketplace API
export const marketplaceApi = {
  list: (params?: { status?: string; tags?: string; search?: string }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return fetchApi(`/marketplace/${query ? `?${query}` : ''}`);
  },
  
  search: (q: string, maxResults?: number) =>
    fetchApi(`/marketplace/search?q=${encodeURIComponent(q)}${maxResults ? `&max_results=${maxResults}` : ''}`),
  
  install: (pluginId: string, version?: string) =>
    fetchApi(`/marketplace/${pluginId}/install`, {
      method: 'POST',
      body: JSON.stringify({ version }),
    }),
  
  uninstall: (pluginId: string) =>
    fetchApi(`/marketplace/${pluginId}/uninstall`, { method: 'POST' }),
  
  update: (pluginId: string, version: string) =>
    fetchApi(`/marketplace/${pluginId}/update`, {
      method: 'POST',
      body: JSON.stringify({ version }),
    }),
  
  checkUpdates: () => fetchApi('/marketplace/updates'),
  
  getInstalled: () => fetchApi('/marketplace/installed'),
  
  getFavorites: () => fetchApi('/marketplace/favorites'),
  
  addFavorite: (pluginId: string) =>
    fetchApi(`/marketplace/${pluginId}/favorite`, { method: 'POST' }),
  
  removeFavorite: (pluginId: string) =>
    fetchApi(`/marketplace/${pluginId}/favorite`, { method: 'DELETE' }),
};

// Orchestrator API
export const orchestratorApi = {
  getConfig: () => fetchApi('/orchestrator/config'),
  
  updateConfig: (config: object) =>
    fetchApi('/orchestrator/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    }),
  
  getSignals: (limit?: number, direction?: string) => {
    const params = new URLSearchParams();
    if (limit) params.set('limit', limit.toString());
    if (direction) params.set('direction', direction);
    const query = params.toString();
    return fetchApi(`/orchestrator/signals${query ? `?${query}` : ''}`);
  },
  
  getStatistics: () => fetchApi('/orchestrator/statistics'),
  
  reset: () => fetchApi('/orchestrator/reset', { method: 'POST' }),
};

// Account API
export const accountApi = {
  getStatus: () => fetchApi('/accounts/status'),
  
  login: (apiToken: string) =>
    fetchApi('/accounts/login', {
      method: 'POST',
      body: JSON.stringify({ api_token: apiToken }),
    }),
  
  logout: () => fetchApi('/accounts/logout', { method: 'POST' }),
  
  listAccounts: () => fetchApi('/accounts/accounts'),
  
  getAccount: (accountId: string) =>
    fetchApi(`/accounts/accounts/${accountId}`),
  
  switchAccount: (accountId: string) =>
    fetchApi(`/accounts/accounts/${accountId}/switch`, { method: 'POST' }),
  
  switchToDemo: () => fetchApi('/accounts/switch/demo', { method: 'POST' }),
  
  switchToReal: () => fetchApi('/accounts/switch/real', { method: 'POST' }),
  
  getBalances: () => fetchApi('/accounts/balances'),
};

// Workspace API
export const workspaceApi = {
  list: () => fetchApi('/workspaces/'),
  
  get: (workspaceId: string) =>
    fetchApi(`/workspaces/${workspaceId}`),
  
  addFavorite: (workspaceId: string) =>
    fetchApi(`/workspaces/${workspaceId}/favorites`, { method: 'POST' }),
  
  removeFavorite: (workspaceId: string) =>
    fetchApi(`/workspaces/${workspaceId}/favorites`, { method: 'DELETE' }),
  
  getFavorites: () => fetchApi('/workspaces/favorites'),
  
  getCurrent: () => fetchApi('/workspaces/current'),
  
  activate: (workspaceId: string) =>
    fetchApi(`/workspaces/${workspaceId}/activate`, { method: 'POST' }),
  
  getPreferences: (workspaceId: string) =>
    fetchApi(`/workspaces/${workspaceId}/preferences`),
  
  updatePreferences: (workspaceId: string, preferences: object) =>
    fetchApi(`/workspaces/${workspaceId}/preferences`, {
      method: 'PUT',
      body: JSON.stringify(preferences),
    }),
};

// Risk API
export const riskApi = {
  getStatus: () => fetchApi('/risk/status'),
  
  getLimits: () => fetchApi('/risk/limits'),
  
  updateLimits: (limits: object) =>
    fetchApi('/risk/limits', {
      method: 'PUT',
      body: JSON.stringify(limits),
    }),
  
  validateTrade: (params: {
    pluginId: string;
    market: string;
    direction: string;
    amount: number;
    balance: number;
  }) => fetchApi('/risk/validate', {
    method: 'POST',
    body: JSON.stringify(params),
  }),
  
  getMetrics: () => fetchApi('/risk/metrics'),
  
  getEvents: (params?: { since?: string; level?: string; limit?: number }) => {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return fetchApi(`/risk/events${query ? `?${query}` : ''}`);
  },
  
  reset: () => fetchApi('/risk/reset', { method: 'POST' }),
  
  emergencyStop: (reason: string) =>
    fetchApi('/risk/emergency-stop', {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  
  getKillSwitchStatus: () => fetchApi('/risk/kill-switch'),
  
  resetKillSwitch: () =>
    fetchApi('/risk/kill-switch/reset', { method: 'POST' }),
};

// Cloud Sync API
export const syncApi = {
  getStatus: () => fetchApi('/sync/status'),
  
  sync: () => fetchApi('/sync/sync', { method: 'POST' }),
  
  getConflicts: () => fetchApi('/sync/conflicts'),
  
  resolveConflict: (key: string, resolution: 'local' | 'remote') =>
    fetchApi(`/sync/conflicts/${key}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution }),
    }),
  
  getData: () => fetchApi('/sync/data'),
  
  updateData: (key: string, data: object) =>
    fetchApi(`/sync/data/${key}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
};

// Export all APIs
export const api = {
  plugins: pluginApi,
  marketplace: marketplaceApi,
  orchestrator: orchestratorApi,
  accounts: accountApi,
  workspaces: workspaceApi,
  risk: riskApi,
  sync: syncApi,
};

export default api;
