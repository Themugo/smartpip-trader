import { createClient, SupabaseClient, User } from '@supabase/supabase-js';

export type { User };

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || '';
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export const supabaseConfigured = Boolean(supabaseUrl && supabaseKey);

// Create a real client only when env vars are present; otherwise export a
// stub whose auth methods resolve to safe no-ops so the app can still
// render (public / demo mode) without crashing.
export const supabase: SupabaseClient = supabaseConfigured
  ? createClient(supabaseUrl, supabaseKey)
  : createClient('https://placeholder.supabase.co', 'placeholder');

export type Trade = {
  id: string;
  market: string;
  type: string;
  direction: string;
  amount: number;
  confidence: number;
  reason: string | null;
  entry_price: number;
  entry_time: string;
  exit_time: string | null;
  profit: number | null;
  contract_id: string | null;
  created_at: string;
};

export type TradeStatistics = {
  id: number;
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_profit: number;
  session_pnl: number;
  best_trade: number;
  worst_trade: number;
  avg_win: number;
  avg_loss: number;
  updated_at: string;
};

export type SystemSettings = {
  id: number;
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
  updated_at: string;
};

export type AuditLogEntry = {
  id: string;
  action: string;
  actor: string;
  ip_address: string | null;
  details: Record<string, unknown>;
  timestamp: string;
};

export type AuthState = {
  user: User | null;
  loading: boolean;
};
