import os
import tempfile


def test_security_manager_revoke_all_tokens():
    from security.auth import SecurityManager

    manager = SecurityManager(secret_key="test-secret-key-with-at-least-32-bytes")
    token = manager.create_access_token({"sub": "user-1"})
    assert manager.verify_token(token) is not None
    manager.revoke_all_tokens()
    assert manager.verify_token(token) is None


def test_trade_memory_completed_contract_excludes_open():
    from intelligence.trade_memory import TradeMemory, TradeRecord

    with tempfile.TemporaryDirectory() as tmp:
        memory = TradeMemory(os.path.join(tmp, "memory.db"))
        base = dict(
            timestamp=1.0, market="R_50", direction="CALL", amount=1.0,
            entry_price=100.0, exit_price=101.0, profit=1.0, pnl_pct=1.0,
            confidence=80.0, analyzer_outputs={}, market_features={},
            regime="TRENDING_UP", entropy=2.0, volatility=0.01,
            digit_pattern=[1, 2, 3], duration_seconds=1.0, metadata={}
        )
        memory.record_trade(TradeRecord(trade_id="w", outcome="WIN", **base))
        memory.record_trade(TradeRecord(trade_id="l", outcome="LOSS", **{**base, "profit": -1.0, "pnl_pct": -1.0}))
        memory.record_trade(TradeRecord(trade_id="o", outcome="OPEN", **{**base, "profit": 0.0, "pnl_pct": 0.0}))
        assert {r.trade_id for r in memory.get_completed_trades()} == {"w", "l"}


def test_settings_redacts_foreign_bot_api_key():
    from config.settings import Settings

    settings = Settings()
    settings.foreign_bot_api_key = "super-secret"
    assert settings.to_dict()["foreign_bot_api_key"] == "***REDACTED***"


def test_redis_rate_limiter_falls_back_without_disabling_limits():
    from utils.redis_rate_limiter import RedisRateLimiter

    limiter = RedisRateLimiter(redis_url="redis://127.0.0.1:1", default_limit=2, default_window=60)
    assert limiter.is_allowed("client", limit=2, window=60)[0] is True
    assert limiter.is_allowed("client", limit=2, window=60)[0] is True
    assert limiter.is_allowed("client", limit=2, window=60)[0] is False


def test_database_persistence_accepts_canonical_entry_time(tmp_path):
    from database.database import DatabaseManager

    db = DatabaseManager(db_path=str(tmp_path / 'trades.db'))
    trade = {
        'id': 'persist-1',
        'market': 'R_10',
        'type': 'DIGITEVEN',
        'direction': 'EVEN',
        'amount': 1.0,
        'confidence': 80.0,
        'entry_price': 100.0,
        'entry_time': '2026-09-16T00:00:00+00:00',
        'profit': 0.9,
    }
    assert db.save_trade(trade) is True
    saved = db.get_trade('persist-1')
    assert saved is not None
    assert saved['profit'] == 0.9


def test_database_persistence_falls_back_to_created_at(tmp_path):
    from database.database import DatabaseManager

    db = DatabaseManager(db_path=str(tmp_path / 'trades.db'))
    trade = {
        'id': 'persist-2',
        'market': 'R_10',
        'type': 'DIGITEVEN',
        'direction': 'EVEN',
        'amount': 1.0,
        'confidence': 80.0,
        'entry_price': 100.0,
        'created_at': '2026-09-16T00:00:00+00:00',
        'completed_at': '2026-09-16T00:00:01+00:00',
        'profit': 0.9,
    }
    assert db.save_trade(trade) is True
    saved = db.get_trade('persist-2')
    assert saved is not None
    assert saved['entry_time'] == trade['created_at']
    assert saved['exit_time'] == trade['completed_at']
