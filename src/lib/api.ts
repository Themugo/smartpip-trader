import { supabase } from './supabase';

const EDGE_FUNCTION_URL = `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/trading-api`;

async function apiFetch(path: string, options?: RequestInit) {
  const url = `${EDGE_FUNCTION_URL}/${path}`;

  // Get current session token
  const { data: { session } } = await supabase.auth.getSession();
  const token = session?.access_token ?? import.meta.env.VITE_SUPABASE_ANON_KEY;

  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  getTrades: () => apiFetch('trades'),
  getStatistics: () => apiFetch('statistics'),
  getSettings: () => apiFetch('settings'),
  updateSettings: (data: Record<string, unknown>) => apiFetch('settings', { method: 'PATCH', body: JSON.stringify(data) }),
  getAuditLog: () => apiFetch('audit'),
  logAudit: (data: { action: string; actor: string; ip_address?: string; details?: Record<string, unknown> }) =>
    apiFetch('audit', { method: 'POST', body: JSON.stringify(data) }),
  health: () => apiFetch('health'),
};
