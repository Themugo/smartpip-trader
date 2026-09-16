/* SmartPip end-user trading foundation.
 * No broker secrets are stored here. Deriv PAT/JWT material must remain in
 * a server-side secret store or secure broker connection service.
 */

CREATE TABLE IF NOT EXISTS public.user_trading_settings (
  user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  auto_trading_enabled boolean NOT NULL DEFAULT false,
  min_confidence numeric NOT NULL DEFAULT 70 CHECK (min_confidence BETWEEN 0 AND 100),
  max_stake numeric NOT NULL DEFAULT 1 CHECK (max_stake > 0),
  max_trades_per_hour integer NOT NULL DEFAULT 5 CHECK (max_trades_per_hour BETWEEN 1 AND 100),
  daily_loss_limit numeric NOT NULL DEFAULT 10 CHECK (daily_loss_limit >= 0),
  max_open_contracts integer NOT NULL DEFAULT 1 CHECK (max_open_contracts BETWEEN 1 AND 20),
  preferred_markets text[] NOT NULL DEFAULT ARRAY['R_50','R_75','R_100']::text[],
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.user_trading_settings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "user_trading_settings_select_own" ON public.user_trading_settings;
CREATE POLICY "user_trading_settings_select_own" ON public.user_trading_settings
  FOR SELECT TO authenticated USING (user_id = auth.uid());
DROP POLICY IF EXISTS "user_trading_settings_insert_own" ON public.user_trading_settings;
CREATE POLICY "user_trading_settings_insert_own" ON public.user_trading_settings
  FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "user_trading_settings_update_own" ON public.user_trading_settings;
CREATE POLICY "user_trading_settings_update_own" ON public.user_trading_settings
  FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());

CREATE TABLE IF NOT EXISTS public.broker_connections (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  broker text NOT NULL DEFAULT 'deriv' CHECK (broker = 'deriv'),
  account_id text NOT NULL,
  environment text NOT NULL DEFAULT 'demo' CHECK (environment IN ('demo','real')),
  currency text,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','connected','disconnected','error')),
  last_connected_at timestamptz,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, broker, account_id)
);

CREATE INDEX IF NOT EXISTS idx_broker_connections_user ON public.broker_connections(user_id, updated_at DESC);
ALTER TABLE public.broker_connections ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "broker_connections_select_own" ON public.broker_connections;
CREATE POLICY "broker_connections_select_own" ON public.broker_connections
  FOR SELECT TO authenticated USING (user_id = auth.uid());
DROP POLICY IF EXISTS "broker_connections_insert_own" ON public.broker_connections;
CREATE POLICY "broker_connections_insert_own" ON public.broker_connections
  FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "broker_connections_update_own" ON public.broker_connections;
CREATE POLICY "broker_connections_update_own" ON public.broker_connections
  FOR UPDATE TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "broker_connections_delete_own" ON public.broker_connections;
CREATE POLICY "broker_connections_delete_own" ON public.broker_connections
  FOR DELETE TO authenticated USING (user_id = auth.uid());

/* A trade journal row can be reconciled with a broker settlement without
 * exposing broker credentials to the browser. Existing rows remain valid. */
ALTER TABLE public.trade_journal ADD COLUMN IF NOT EXISTS contract_id text;
CREATE INDEX IF NOT EXISTS idx_trade_journal_contract_user ON public.trade_journal(user_id, contract_id)
  WHERE contract_id IS NOT NULL;

CREATE OR REPLACE FUNCTION public.handle_new_user_trading_settings()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.user_trading_settings (user_id)
  VALUES (NEW.id)
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created_trading_settings ON auth.users;
CREATE TRIGGER on_auth_user_created_trading_settings
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user_trading_settings();
