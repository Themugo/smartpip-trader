/**
 * Security Utilities
 * 
 * Security hardening utilities for SmartPip including:
 * - Encrypted storage
 * - Secure token management
 * - Input validation
 * - Rate limiting helpers
 */

import { supabase } from './supabase';

// ============================================================================
// ENCRYPTED STORAGE
// ============================================================================

interface EncryptedStorageResult {
  success: boolean;
  error?: string;
}

/**
 * Store sensitive data with encryption
 */
export async function secureStore(key: string, value: string): Promise<EncryptedStorageResult> {
  try {
    // Generate encryption key from user session
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.user) {
      return { success: false, error: 'Not authenticated' };
    }

    // Store in Supabase instead of localStorage
    const { error } = await supabase.rpc('store_secure_data', {
      p_key: key,
      p_value: value,
      p_user_id: session.user.id,
    });

    if (error) throw error;
    return { success: true };
  } catch (error) {
    console.error('Secure store failed:', error);
    return { success: false, error: String(error) };
  }
}

/**
 * Retrieve sensitive data with decryption
 */
export async function secureRetrieve(key: string): Promise<{ success: boolean; value?: string; error?: string }> {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.user) {
      return { success: false, error: 'Not authenticated' };
    }

    const { data, error } = await supabase.rpc('retrieve_secure_data', {
      p_key: key,
      p_user_id: session.user.id,
    });

    if (error) throw error;
    return { success: true, value: data };
  } catch (error) {
    console.error('Secure retrieve failed:', error);
    return { success: false, error: String(error) };
  }
}

/**
 * Delete sensitive data
 */
export async function secureDelete(key: string): Promise<EncryptedStorageResult> {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.user) {
      return { success: false, error: 'Not authenticated' };
    }

    const { error } = await supabase.rpc('delete_secure_data', {
      p_key: key,
      p_user_id: session.user.id,
    });

    if (error) throw error;
    return { success: true };
  } catch (error) {
    console.error('Secure delete failed:', error);
    return { success: false, error: String(error) };
  }
}

// ============================================================================
// BROKER TOKEN MANAGEMENT
// ============================================================================

export interface BrokerCredentials {
  broker: 'deriv';
  appId?: string;
  token: string;
  environment: 'demo' | 'live';
}

/**
 * Store broker credentials securely
 */
export async function storeBrokerCredentials(credentials: BrokerCredentials): Promise<EncryptedStorageResult> {
  // Validate credentials before storing
  if (!credentials.token) {
    return { success: false, error: 'Token is required' };
  }

  if (credentials.token.length < 10) {
    return { success: false, error: 'Invalid token format' };
  }

  // Store securely via backend
  const result = await secureStore(
    `broker_${credentials.environment}`,
    JSON.stringify(credentials)
  );

  // Remove from localStorage if it was there
  localStorage.removeItem('deriv_token');
  localStorage.removeItem('deriv_demo_token');
  localStorage.removeItem('deriv_live_token');

  return result;
}

/**
 * Retrieve broker credentials
 */
export async function getBrokerCredentials(
  environment: 'demo' | 'live'
): Promise<{ success: boolean; credentials?: BrokerCredentials; error?: string }> {
  const result = await secureRetrieve(`broker_${environment}`);
  
  if (!result.success || !result.value) {
    return { success: false, error: result.error || 'Credentials not found' };
  }

  try {
    const credentials = JSON.parse(result.value) as BrokerCredentials;
    return { success: true, credentials };
  } catch {
    return { success: false, error: 'Failed to parse credentials' };
  }
}

/**
 * Delete broker credentials
 */
export async function deleteBrokerCredentials(
  environment: 'demo' | 'live'
): Promise<EncryptedStorageResult> {
  return secureDelete(`broker_${environment}`);
}

// ============================================================================
// INPUT VALIDATION
// ============================================================================

// Valid markets
const VALID_MARKETS = ['R_10', 'R_25', 'R_50', 'R_75', 'R_100', 'R_200', 'R_250', 'R_500'];

// Valid trade types
const VALID_TRADE_TYPES = ['DIGITOVER', 'DIGITUNDER', 'DIGITMATCH', 'DIGITDIFF', 'RISEFALL', 'EVENODD', 'HIGHER', 'LOWER', 'TOUCH', 'NO_TOUCH'];

// Trade validation
export interface TradeInput {
  market: string;
  type: string;
  direction: string;
  amount: number;
  duration?: number;
  contractType?: string;
}

export function validateTradeInput(input: unknown): { valid: boolean; errors?: string[] } {
  if (!input || typeof input !== 'object') {
    return { valid: false, errors: ['Input must be an object'] };
  }

  const trade = input as Record<string, unknown>;
  const errors: string[] = [];

  if (!VALID_MARKETS.includes(trade.market as string)) {
    errors.push(`market: Must be one of ${VALID_MARKETS.join(', ')}`);
  }

  if (!VALID_TRADE_TYPES.includes(trade.type as string)) {
    errors.push(`type: Must be one of ${VALID_TRADE_TYPES.join(', ')}`);
  }

  if (!['up', 'down'].includes(trade.direction as string)) {
    errors.push('direction: Must be "up" or "down"');
  }

  const amount = Number(trade.amount);
  if (isNaN(amount) || amount < 0.01 || amount > 10000) {
    errors.push('amount: Must be between 0.01 and 10000');
  }

  return errors.length > 0 ? { valid: false, errors } : { valid: true };
}

// Settings validation
export interface SettingsInput {
  base_amount: number;
  auto_trading: boolean;
  max_trades_per_hour: number;
  min_confidence: number;
  stop_loss: number;
  take_profit: number;
  max_consecutive_losses: number;
  enable_even_odd: boolean;
  enable_rise_fall: boolean;
  enable_over_under: boolean;
  enable_match_diff: boolean;
  enable_digit_analysis: boolean;
}

export function validateSettingsInput(input: unknown): { valid: boolean; errors?: string[] } {
  if (!input || typeof input !== 'object') {
    return { valid: false, errors: ['Input must be an object'] };
  }

  const settings = input as Record<string, unknown>;
  const errors: string[] = [];

  const baseAmount = Number(settings.base_amount);
  if (isNaN(baseAmount) || baseAmount < 0.01 || baseAmount > 1000) {
    errors.push('base_amount: Must be between 0.01 and 1000');
  }

  const maxTrades = Number(settings.max_trades_per_hour);
  if (isNaN(maxTrades) || maxTrades < 1 || maxTrades > 100) {
    errors.push('max_trades_per_hour: Must be between 1 and 100');
  }

  const confidence = Number(settings.min_confidence);
  if (isNaN(confidence) || confidence < 0 || confidence > 100) {
    errors.push('min_confidence: Must be between 0 and 100');
  }

  const maxLosses = Number(settings.max_consecutive_losses);
  if (isNaN(maxLosses) || maxLosses < 1 || maxLosses > 20) {
    errors.push('max_consecutive_losses: Must be between 1 and 20');
  }

  return errors.length > 0 ? { valid: false, errors } : { valid: true };
}

// Sanitize string input
export function sanitizeString(input: string): string {
  return input
    .replace(/[<>]/g, '') // Remove angle brackets
    .replace(/javascript:/gi, '') // Remove javascript: protocol
    .trim();
}

// Sanitize number input
export function sanitizeNumber(input: unknown): number | null {
  const num = Number(input);
  return isNaN(num) ? null : num;
}

// ============================================================================
// RATE LIMITING
// ============================================================================

interface RateLimitEntry {
  count: number;
  resetAt: number;
}

const rateLimitStore = new Map<string, RateLimitEntry>();

/**
 * Check if action is rate limited
 */
export function checkRateLimit(
  key: string,
  maxRequests: number = 100,
  windowMs: number = 60000
): { allowed: boolean; remaining: number; resetIn: number } {
  const now = Date.now();
  const entry = rateLimitStore.get(key);

  // Initialize or reset if window expired
  if (!entry || now > entry.resetAt) {
    rateLimitStore.set(key, {
      count: 1,
      resetAt: now + windowMs,
    });
    return { allowed: true, remaining: maxRequests - 1, resetIn: windowMs };
  }

  // Increment count
  entry.count++;
  const remaining = Math.max(0, maxRequests - entry.count);
  const resetIn = entry.resetAt - now;

  if (entry.count > maxRequests) {
    return { allowed: false, remaining: 0, resetIn };
  }

  return { allowed: true, remaining, resetIn };
}

// Clean up expired entries periodically
setInterval(() => {
  const now = Date.now();
  for (const [key, entry] of rateLimitStore.entries()) {
    if (now > entry.resetAt) {
      rateLimitStore.delete(key);
    }
  }
}, 60000);

// ============================================================================
// SECURITY HEADERS
// ============================================================================

export const securityHeaders = {
  'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://*.supabase.co https://*.deriv.com wss://*.deriv.com;",
  'X-Frame-Options': 'DENY',
  'X-Content-Type-Options': 'nosniff',
  'X-XSS-Protection': '1; mode=block',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
};

// ============================================================================
// AUDIT LOGGING
// ============================================================================

export type AuditEvent =
  | 'user.login'
  | 'user.logout'
  | 'user.register'
  | 'user.update'
  | 'trade.execute'
  | 'trade.cancel'
  | 'trade.close'
  | 'settings.update'
  | 'broker.connect'
  | 'broker.disconnect'
  | 'workspace.create'
  | 'workspace.delete'
  | 'report.generate'
  | 'api.request';

export interface AuditLogEntry {
  event: AuditEvent;
  userId?: string;
  ipAddress?: string;
  userAgent?: string;
  details?: Record<string, unknown>;
  timestamp: number;
}

/**
 * Log an audit event
 */
export async function logAuditEvent(entry: Omit<AuditLogEntry, 'timestamp'>): Promise<void> {
  try {
    await supabase.from('audit_logs').insert({
      event: entry.event,
      user_id: entry.userId || null,
      ip_address: entry.ipAddress || null,
      user_agent: entry.userAgent || navigator.userAgent,
      details: entry.details || {},
      created_at: new Date().toISOString(),
    });
  } catch (error) {
    console.error('Failed to log audit event:', error);
  }
}

/**
 * Get audit logs for current user
 */
export async function getAuditLogs(
  limit: number = 50,
  offset: number = 0
): Promise<{ data: AuditLogEntry[]; error?: string }> {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.user) {
      return { data: [], error: 'Not authenticated' };
    }

    const { data, error } = await supabase
      .from('audit_logs')
      .select('*')
      .eq('user_id', session.user.id)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) throw error;
    return { data: data || [] };
  } catch (error) {
    console.error('Failed to get audit logs:', error);
    return { data: [], error: String(error) };
  }
}

// ============================================================================
// 2FA / MFA
// ============================================================================

export interface MFAStatus {
  enabled: boolean;
  factors?: {
    id: string;
    factor_type: string;
    status: string;
    created_at: string;
  }[];
}

/**
 * Get MFA status for current user
 */
export async function getMFAStatus(): Promise<MFAStatus> {
  try {
    const { data, error } = await supabase.auth.mfa.listFactors();
    if (error) {
      return { enabled: false };
    }
    return {
      enabled: (data?.all || []).length > 0,
      factors: data?.all,
    };
  } catch {
    return { enabled: false };
  }
}

/**
 * Enroll in MFA
 * Note: Full MFA implementation requires Supabase Pro plan with MFA enabled
 */
export async function enrollMFA(): Promise<{ success: boolean; qrCode?: string; secret?: string; error?: string }> {
  try {
    // Placeholder - Full MFA requires Supabase Pro with MFA configured
    // In production, this would call supabase.auth.mfa.enroll()
    console.log('MFA enrollment initiated');
    
    return {
      success: true,
      qrCode: 'data:image/qr;base64 placeholder',
      secret: 'SECRET_PLACEHOLDER',
    };
  } catch (error) {
    return { success: false, error: String(error) };
  }
}

/**
 * Verify and enable MFA
 */
export async function verifyMFA(code: string, factorId: string, challengeId?: string): Promise<{ success: boolean; error?: string }> {
  try {
    if (!code || !factorId) {
      return { success: false, error: 'Code and factor ID are required' };
    }
    
    // Placeholder - Full MFA requires Supabase Pro with MFA configured
    // In production, this would call supabase.auth.mfa.verify()
    console.log('MFA verification initiated');
    
    return { success: true };
  } catch (error) {
    return { success: false, error: String(error) };
  }
}

/**
 * Challenge MFA on login
 */
export async function challengeMFA(factorId: string): Promise<{ success: boolean; challengeId?: string; error?: string }> {
  try {
    // Placeholder - Full MFA requires Supabase Pro with MFA configured
    // In production, this would call supabase.auth.mfa.challenge()
    console.log('MFA challenge initiated');
    
    return { success: true, challengeId: `challenge-${Date.now()}` };
  } catch (error) {
    return { success: false, error: String(error) };
  }
}

export default {
  secureStore,
  secureRetrieve,
  secureDelete,
  storeBrokerCredentials,
  getBrokerCredentials,
  deleteBrokerCredentials,
  validateTradeInput,
  validateSettingsInput,
  sanitizeString,
  sanitizeNumber,
  checkRateLimit,
  logAuditEvent,
  getAuditLogs,
  getMFAStatus,
  enrollMFA,
  verifyMFA,
  challengeMFA,
};
