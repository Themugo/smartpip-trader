/*
# SmartPip Trading System Database Schema

1. New Tables
- `trades`: Stores all executed trades with full audit trail
  - `id` (uuid, primary key)
  - `market` (text, not null) - trading market symbol
  - `type` (text, not null) - trade type (Rise/Fall, Even/Odd, etc.)
  - `direction` (text, not null) - CALL or PUT
  - `amount` (numeric, not null) - trade amount
  - `confidence` (numeric, not null) - AI confidence score
  - `reason` (text) - analysis reason
  - `entry_price` (numeric, not null) - entry price
  - `entry_time` (timestamptz, not null) - when trade opened
  - `exit_time` (timestamptz) - when trade closed
  - `profit` (numeric) - realized profit/loss
  - `contract_id` (text) - Deriv contract ID
  - `created_at` (timestamptz, default now())

- `trade_statistics`: Aggregated trading statistics
  - `id` (integer, primary key, fixed row 1)
  - `total_trades` (integer, default 0)
  - `wins` (integer, default 0)
  - `losses` (integer, default 0)
  - `win_rate` (numeric, default 0)
  - `total_profit` (numeric, default 0)
  - `session_pnl` (numeric, default 0)
  - `best_trade` (numeric, default 0)
  - `worst_trade` (numeric, default 0)
  - `avg_win` (numeric, default 0)
  - `avg_loss` (numeric, default 0)
  - `updated_at` (timestamptz, default now())

- `performance_metrics`: Time-series performance data
  - `id` (uuid, primary key)
  - `metric_name` (text, not null)
  - `metric_value` (numeric, not null)
  - `timestamp` (timestamptz, default now())

- `audit_log`: Security audit trail for all critical operations
  - `id` (uuid, primary key)
  - `action` (text, not null) - what was done (START_BOT, STOP_BOT, etc.)
  - `actor` (text, not null) - who performed the action
  - `ip_address` (text) - client IP
  - `details` (jsonb) - structured details
  - `timestamp` (timestamptz, default now())

- `system_settings`: Persistent system configuration
  - `id` (integer, primary key, fixed row 1)
  - `base_amount` (numeric, default 1.0)
  - `auto_trading` (boolean, default false)
  - `max_trades_per_hour` (integer, default 10)
  - `min_confidence` (integer, default 70)
  - `stop_loss` (numeric, default 50.0)
  - `take_profit` (numeric, default 100.0)
  - `max_consecutive_losses` (integer, default 3)
  - `enable_even_odd` (boolean, default true)
  - `enable_rise_fall` (boolean, default true)
  - `enable_over_under` (boolean, default true)
  - `enable_match_diff` (boolean, default true)
  - `enable_digit_analysis` (boolean, default true)
  - `updated_at` (timestamptz, default now())

2. Security
- Enable RLS on all tables
- Single-tenant policies (anon + authenticated) since this is a trading bot dashboard
- Audit log is append-only

3. Indexes
- `idx_trades_entry_time` on trades(entry_time)
- `idx_trades_market` on trades(market)
- `idx_metrics_name_time` on performance_metrics(metric_name, timestamp)
- `idx_audit_timestamp` on audit_log(timestamp)
*/

-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    market text NOT NULL,
    type text NOT NULL,
    direction text NOT NULL,
    amount numeric NOT NULL,
    confidence numeric NOT NULL,
    reason text,
    entry_price numeric NOT NULL,
    entry_time timestamptz NOT NULL,
    exit_time timestamptz,
    profit numeric,
    contract_id text,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market);

-- Trade statistics table (single row)
CREATE TABLE IF NOT EXISTS trade_statistics (
    id integer PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    total_trades integer NOT NULL DEFAULT 0,
    wins integer NOT NULL DEFAULT 0,
    losses integer NOT NULL DEFAULT 0,
    win_rate numeric NOT NULL DEFAULT 0,
    total_profit numeric NOT NULL DEFAULT 0,
    session_pnl numeric NOT NULL DEFAULT 0,
    best_trade numeric NOT NULL DEFAULT 0,
    worst_trade numeric NOT NULL DEFAULT 0,
    avg_win numeric NOT NULL DEFAULT 0,
    avg_loss numeric NOT NULL DEFAULT 0,
    updated_at timestamptz DEFAULT now()
);

INSERT INTO trade_statistics (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- Performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name text NOT NULL,
    metric_value numeric NOT NULL,
    timestamp timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_metrics_name_time ON performance_metrics(metric_name, timestamp DESC);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    action text NOT NULL,
    actor text NOT NULL,
    ip_address text,
    details jsonb DEFAULT '{}',
    timestamp timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);

-- System settings table (single row)
CREATE TABLE IF NOT EXISTS system_settings (
    id integer PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    base_amount numeric NOT NULL DEFAULT 1.0,
    auto_trading boolean NOT NULL DEFAULT false,
    max_trades_per_hour integer NOT NULL DEFAULT 10,
    min_confidence integer NOT NULL DEFAULT 70,
    stop_loss numeric NOT NULL DEFAULT 50.0,
    take_profit numeric NOT NULL DEFAULT 100.0,
    max_consecutive_losses integer NOT NULL DEFAULT 3,
    enable_even_odd boolean NOT NULL DEFAULT true,
    enable_rise_fall boolean NOT NULL DEFAULT true,
    enable_over_under boolean NOT NULL DEFAULT true,
    enable_match_diff boolean NOT NULL DEFAULT true,
    enable_digit_analysis boolean NOT NULL DEFAULT true,
    updated_at timestamptz DEFAULT now()
);

INSERT INTO system_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- Enable RLS
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_statistics ENABLE ROW LEVEL SECURITY;
ALTER TABLE performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_settings ENABLE ROW LEVEL SECURITY;

-- Single-tenant policies (shared data, no auth required)
DROP POLICY IF EXISTS "anon_select_trades" ON trades;
CREATE POLICY "anon_select_trades" ON trades FOR SELECT
TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_trades" ON trades;
CREATE POLICY "anon_insert_trades" ON trades FOR INSERT
TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_update_trades" ON trades;
CREATE POLICY "anon_update_trades" ON trades FOR UPDATE
TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_delete_trades" ON trades;
CREATE POLICY "anon_delete_trades" ON trades FOR DELETE
TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_select_stats" ON trade_statistics;
CREATE POLICY "anon_select_stats" ON trade_statistics FOR SELECT
TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_update_stats" ON trade_statistics;
CREATE POLICY "anon_update_stats" ON trade_statistics FOR UPDATE
TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "anon_insert_stats" ON trade_statistics;
CREATE POLICY "anon_insert_stats" ON trade_statistics FOR INSERT
TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_select_metrics" ON performance_metrics;
CREATE POLICY "anon_select_metrics" ON performance_metrics FOR SELECT
TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_metrics" ON performance_metrics;
CREATE POLICY "anon_insert_metrics" ON performance_metrics FOR INSERT
TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_select_audit" ON audit_log;
CREATE POLICY "anon_select_audit" ON audit_log FOR SELECT
TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_insert_audit" ON audit_log;
CREATE POLICY "anon_insert_audit" ON audit_log FOR INSERT
TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "anon_select_settings" ON system_settings;
CREATE POLICY "anon_select_settings" ON system_settings FOR SELECT
TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "anon_update_settings" ON system_settings;
CREATE POLICY "anon_update_settings" ON system_settings FOR UPDATE
TO anon, authenticated USING (true) WITH CHECK (true);
