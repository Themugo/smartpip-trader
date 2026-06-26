-- Shadow Mode Signals Table
CREATE TABLE IF NOT EXISTS shadow_signals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    timestamp timestamptz DEFAULT now(),
    symbol text NOT NULL,
    contract_type text NOT NULL,
    predicted_direction text NOT NULL,
    confidence numeric NOT NULL,
    expected_outcome text NOT NULL CHECK (expected_outcome IN ('win', 'loss', 'unknown')),
    actual_outcome text CHECK (actual_outcome IN ('win', 'loss', 'pending', 'missed')),
    expected_pnl numeric NOT NULL DEFAULT 0,
    actual_pnl numeric,
    latency_ms integer NOT NULL DEFAULT 0,
    executed boolean NOT NULL DEFAULT false,
    missed_reason text,
    model_version text NOT NULL DEFAULT 'v1.0',
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_shadow_signals_user ON shadow_signals(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_shadow_signals_symbol ON shadow_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_shadow_signals_outcome ON shadow_signals(actual_outcome);

-- Shadow Mode Daily Metrics Table
CREATE TABLE IF NOT EXISTS shadow_daily_metrics (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    date date NOT NULL DEFAULT CURRENT_DATE,
    total_signals integer NOT NULL DEFAULT 0,
    executed_signals integer NOT NULL DEFAULT 0,
    missed_signals integer NOT NULL DEFAULT 0,
    signal_accuracy numeric NOT NULL DEFAULT 0,
    paper_pnl numeric NOT NULL DEFAULT 0,
    real_pnl numeric NOT NULL DEFAULT 0,
    pnl_delta numeric NOT NULL DEFAULT 0,
    avg_latency_ms numeric NOT NULL DEFAULT 0,
    model_drift numeric NOT NULL DEFAULT 0,
    is_profitable boolean NOT NULL DEFAULT false,
    created_at timestamptz DEFAULT now(),
    UNIQUE(user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_shadow_daily_user_date ON shadow_daily_metrics(user_id, date DESC);

-- Shadow Mode Qualification Tracking
CREATE TABLE IF NOT EXISTS shadow_qualification (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    start_date timestamptz NOT NULL DEFAULT now(),
    days_in_shadow integer NOT NULL DEFAULT 0,
    profitable_days integer NOT NULL DEFAULT 0,
    total_paper_pnl numeric NOT NULL DEFAULT 0,
    is_qualified boolean NOT NULL DEFAULT false,
    qualified_at timestamptz,
    last_evaluated_at timestamptz DEFAULT now(),
    created_at timestamptz DEFAULT now(),
    UNIQUE(user_id)
);

-- Trade Journal Entries Table
CREATE TABLE IF NOT EXISTS trade_journal (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    timestamp timestamptz DEFAULT now(),
    symbol text NOT NULL,
    contract_type text NOT NULL,
    entry_price numeric NOT NULL,
    entry_digit integer,
    exit_price numeric,
    exit_digit integer,
    amount numeric NOT NULL,
    confidence numeric NOT NULL,
    regime text NOT NULL,
    entry_conditions jsonb NOT NULL DEFAULT '[]',
    exit_conditions jsonb NOT NULL DEFAULT '[]',
    profit numeric,
    pnl numeric,
    drawdown_impact numeric NOT NULL DEFAULT 0,
    running_balance numeric NOT NULL DEFAULT 1000,
    peak_balance numeric NOT NULL DEFAULT 1000,
    notes text,
    created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trade_journal_user ON trade_journal(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trade_journal_regime ON trade_journal(regime);
CREATE INDEX IF NOT EXISTS idx_trade_journal_contract ON trade_journal(contract_type);

-- Weekly Insights Table
CREATE TABLE IF NOT EXISTS weekly_insights (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
    week_start date NOT NULL,
    week_end date NOT NULL,
    total_trades integer NOT NULL DEFAULT 0,
    win_rate numeric NOT NULL DEFAULT 0,
    profit_factor numeric NOT NULL DEFAULT 0,
    best_setup jsonb,
    worst_setup jsonb,
    time_of_day jsonb NOT NULL DEFAULT '{}',
    regime_performance jsonb NOT NULL DEFAULT '{}',
    recommendations jsonb NOT NULL DEFAULT '[]',
    created_at timestamptz DEFAULT now(),
    UNIQUE(user_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_weekly_insights_user ON weekly_insights(user_id, week_start DESC);

-- Enable RLS
ALTER TABLE shadow_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE shadow_daily_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE shadow_qualification ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_journal ENABLE ROW LEVEL SECURITY;
ALTER TABLE weekly_insights ENABLE ROW LEVEL SECURITY;

-- RLS Policies: user-scoped
CREATE POLICY "select_own_shadow_signals" ON shadow_signals FOR SELECT
    TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "insert_own_shadow_signals" ON shadow_signals FOR INSERT
    TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own_shadow_signals" ON shadow_signals FOR UPDATE
    TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own_shadow_signals" ON shadow_signals FOR DELETE
    TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "select_own_shadow_metrics" ON shadow_daily_metrics FOR SELECT
    TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "insert_own_shadow_metrics" ON shadow_daily_metrics FOR INSERT
    TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own_shadow_metrics" ON shadow_daily_metrics FOR UPDATE
    TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "select_own_shadow_qual" ON shadow_qualification FOR SELECT
    TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "insert_own_shadow_qual" ON shadow_qualification FOR INSERT
    TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own_shadow_qual" ON shadow_qualification FOR UPDATE
    TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "select_own_journal" ON trade_journal FOR SELECT
    TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "insert_own_journal" ON trade_journal FOR INSERT
    TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own_journal" ON trade_journal FOR UPDATE
    TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "delete_own_journal" ON trade_journal FOR DELETE
    TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "select_own_insights" ON weekly_insights FOR SELECT
    TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "insert_own_insights" ON weekly_insights FOR INSERT
    TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "update_own_insights" ON weekly_insights FOR UPDATE
    TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
