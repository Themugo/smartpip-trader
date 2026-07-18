/**
 * @deprecated This file is deprecated
 * 
 * All API functionality has been consolidated into api.ts
 * Please update imports to use '../lib/api' instead
 * 
 * Migration:
 *   import { api } from '../lib/api_v2';
 *   // Change to:
 *   import { api } from '../lib/api';
 * 
 * The unified API client includes all endpoints from this file:
 *   - api.plugins.* (formerly pluginApi.*)
 *   - api.marketplace.* (formerly marketplaceApi.*)
 *   - api.orchestrator.* (formerly orchestratorApi.*)
 *   - api.accounts.* (formerly accountApi.*)
 *   - api.workspaces.* (formerly workspaceApi.*)
 *   - api.risk.* (formerly riskApi.*)
 *   - api.sync.* (formerly syncApi.*)
 * 
 * @removed_in 5.0.0
 */

// Re-export from consolidated API for backwards compatibility
export { api } from './api';

// @ts-ignore - Legacy exports for backwards compatibility
const api = null;
export default api;
