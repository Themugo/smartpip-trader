from pathlib import Path


def test_frontend_trade_uses_canonical_backend_route():
    source = Path('src/lib/api.ts').read_text(encoding='utf-8')
    assert "`${API_BASE}/api/trade`" in source
    assert "v2Fetch<{\n    success: boolean" not in source


def test_frontend_review_and_journal_use_configurable_backend_origin():
    review = Path('src/components/ReviewPage.tsx').read_text(encoding='utf-8')
    journal = Path('src/components/TradeJournalPanel.tsx').read_text(encoding='utf-8')
    assert "API_BASE_URL}/api/review" in review
    assert "API_BASE_URL}/api/review/deriv-account" in review
    assert "API_BASE_URL}/api/review/profit-table" in review
    assert "`${API_BASE_URL}/api/journal`" in journal


def test_backend_exposes_canonical_trade_route():
    from fastapi import FastAPI
    from api.routes import setup_routes

    class Dummy:
        pass

    # setup_routes only registers routes; no broker connection is required.
    app = FastAPI()
    setup_routes(app, Dummy())
    paths = {route.path for route in app.routes if hasattr(route, 'path')}
    assert '/api/trade' in paths
    assert '/api/v2/trade' not in paths


def test_manual_trade_route_uses_backend_probability_not_browser_prediction():
    source = Path('api/routes.py').read_text(encoding='utf-8')
    assert 'raw_probability = float(best.get("confidence", 0) or 0) / 100.0' in source
    assert 'if payload.prediction is not None:' not in source
    assert 'max_stake = balance * trading_system.settings.max_stake_pct_equity' in source
    assert 'trading_system._canonical_trades[contract_id] = canonical' in source


def test_manual_rise_fall_trade_must_match_backend_ai_direction():
    source = Path('api/routes.py').read_text(encoding='utf-8')
    assert 'best_contract_type != "RISEFALL"' in source
    assert 'requested_direction != best_direction' in source


def test_end_user_foundation_has_user_scoped_settings_and_broker_connection():
    migration = Path('supabase/migrations/202609160002_005_end_user_trading_foundation.sql').read_text(encoding='utf-8')
    assert 'CREATE TABLE IF NOT EXISTS public.user_trading_settings' in migration
    assert 'CREATE TABLE IF NOT EXISTS public.broker_connections' in migration
    assert 'USING (user_id = auth.uid())' in migration
    assert 'ALTER TABLE public.trade_journal ADD COLUMN IF NOT EXISTS contract_id' in migration


def test_public_deriv_market_feed_uses_current_options_endpoint():
    source = Path('src/hooks/useDerivTicks.ts').read_text(encoding='utf-8')
    assert 'wss://api.derivws.com/trading/v1/options/ws/public' in source
    assert 'forget:' in source


def test_trade_api_disables_retries_to_avoid_duplicate_broker_orders():
    source = Path('src/lib/api.ts').read_text(encoding='utf-8')
    assert "timeout: 15000, retries: 0" in source
