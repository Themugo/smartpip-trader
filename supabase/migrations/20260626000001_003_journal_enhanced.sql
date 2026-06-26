-- Migration 003: Enhance trade_journal with quant analyst fields
-- Adds: entropy, streak, chi2, rsi, macd, score, exit_reason, duration_ticks, status, closed_at
-- Safe: uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS patterns

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trade_journal' AND column_name='entropy') THEN
    ALTER TABLE trade_journal ADD COLUMN entropy numeric;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trade_journal' AND column_name='streak') THEN
    ALTER TABLE trade_journal ADD COLUMN streak integer;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trade_journal' AND column_name='chi2') THEN
    ALTER TABLE trade_journal ADD COLUMN chi2 numeric;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trade_journal' AND column_name='rsi') THEN
    ALTER TABLE trade_journal ADD COLUMN rsi numeric;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trade_journal' AND column_name='macd') THEN
    ALTER TABLE trade_journal ADD COLUMN macd numeric;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trade_journal' AND column_name='score') THEN
    ALTER TABLE trade_journal ADD COLUMN score integer;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trade_journal' AND column_name='exit_reason') THEN
    ALTER TABLE trade_journal ADD COLUMN exit_reason text;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trade_journal' AND column_name='duration_ticks') THEN
    ALTER TABLE trade_journal ADD COLUMN duration_ticks integer;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trade_journal' AND column_name='status') THEN
    ALTER TABLE trade_journal ADD COLUMN status text NOT NULL DEFAULT 'closed';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trade_journal' AND column_name='closed_at') THEN
    ALTER TABLE trade_journal ADD COLUMN closed_at timestamptz;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='trade_journal' AND column_name='peak_balance') THEN
    ALTER TABLE trade_journal ADD COLUMN peak_balance numeric NOT NULL DEFAULT 1000;
  END IF;
END $$;

-- Performance index on status for open-trade queries
CREATE INDEX IF NOT EXISTS idx_trade_journal_status ON trade_journal(status);
CREATE INDEX IF NOT EXISTS idx_trade_journal_closed_at ON trade_journal(closed_at DESC);

-- Performance analytics view
CREATE OR REPLACE VIEW trade_journal_analytics AS
SELECT
  user_id,
  DATE_TRUNC('week', timestamp) AS week_start,
  COUNT(*)                                               AS total_trades,
  COUNT(*) FILTER (WHERE pnl > 0)                        AS wins,
  ROUND(COUNT(*) FILTER (WHERE pnl > 0)::numeric /
        NULLIF(COUNT(*), 0) * 100, 2)                    AS win_rate,
  ROUND(SUM(CASE WHEN pnl > 0 THEN pnl ELSE 0 END) /
        NULLIF(SUM(CASE WHEN pnl < 0 THEN ABS(pnl) ELSE 0 END), 0), 4)
                                                         AS profit_factor,
  ROUND(SUM(pnl)::numeric, 4)                            AS total_pnl,
  ROUND(AVG(pnl)::numeric, 4)                            AS avg_pnl,
  ROUND(AVG(confidence)::numeric, 1)                     AS avg_confidence,
  ROUND(MAX(drawdown_impact)::numeric, 2)                AS max_drawdown_impact,
  regime                                                 AS regime
FROM trade_journal
WHERE status = 'closed' AND pnl IS NOT NULL
GROUP BY user_id, DATE_TRUNC('week', timestamp), regime
ORDER BY week_start DESC;

COMMENT ON VIEW trade_journal_analytics IS 'Weekly P&L and win-rate breakdown by regime for the quant analytics dashboard.';
