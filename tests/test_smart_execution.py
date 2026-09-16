import asyncio
from types import SimpleNamespace

import pytest

from trading.deriv_execution import (
    DerivProposal,
    expected_value_per_stake,
    required_win_probability,
)
from ai_core.trade_approval import TradeApprover


def test_expected_value_uses_gross_payout_quote():
    # $1 stake, $1.90 gross payout, 60% win probability => +$0.14 EV.
    assert expected_value_per_stake(0.60, 1.90, 1.0) == pytest.approx(0.14)


def test_break_even_probability():
    assert required_win_probability(1.90, 1.0) == pytest.approx(1 / 1.9)


def test_trade_approver_fails_closed_on_negative_ev():
    result = TradeApprover().approve(
        win_probability=0.50,
        payout=1.90,
        stake=1.0,
        min_expected_value=0.01,
        min_probability=0.55,
        risk_score=10,
        model_ready=True,
        market_data_fresh=True,
    )
    assert not result.approved
    assert any("win probability" in reason for reason in result.reasons)
    assert any("EV" in reason for reason in result.reasons)


@pytest.mark.asyncio
async def test_connection_request_correlation_without_raw_recv():
    from core.connection import DerivConnection

    class FakeSocket:
        def __init__(self):
            self.sent = []
            self.incoming = asyncio.Queue()
        async def send(self, text):
            self.sent.append(text)
        async def recv(self):
            return await self.incoming.get()
        async def close(self):
            pass

    conn = DerivConnection()
    sock = FakeSocket()
    conn.websocket = sock
    conn.connected = True
    conn.authorized = True
    conn._receiver_task = asyncio.create_task(conn._receiver_loop())

    t1 = asyncio.create_task(conn.request({"balance": 1}))
    t2 = asyncio.create_task(conn.request({"portfolio": 1}))
    await asyncio.sleep(0)
    assert len(sock.sent) == 2

    import json
    ids = [json.loads(item)["req_id"] for item in sock.sent]
    await sock.incoming.put(json.dumps({"req_id": ids[1], "portfolio": {"contracts": []}, "msg_type": "portfolio"}))
    await sock.incoming.put(json.dumps({"req_id": ids[0], "balance": {"balance": 100}, "msg_type": "balance"}))

    assert (await t1)["balance"]["balance"] == 100
    assert (await t2)["portfolio"]["contracts"] == []
    await conn.close()


def test_proposal_profit_multiple():
    p = DerivProposal(id="x", ask_price=1.0, payout=1.95, spot=100.0, proposal_raw={})
    assert p.gross_return_multiple == pytest.approx(1.95)
    assert p.profit_multiple == pytest.approx(0.95)

@pytest.mark.asyncio
async def test_deriv_execution_full_mock_lifecycle():
    from trading.deriv_execution import DerivExecutionAdapter

    class FakeConnection:
        authorized = True
        def __init__(self):
            self.handlers = {}
            self.calls = []
        def add_handler(self, msg_type, callback):
            self.handlers.setdefault(msg_type, []).append(callback)
        async def request(self, payload, timeout=8.0):
            self.calls.append(payload)
            if payload.get('proposal'):
                return {'proposal': {'id': 'p1', 'ask_price': 1.0, 'payout': 1.9, 'spot': 123.45}}
            if payload.get('buy'):
                return {'buy': {'contract_id': '12345', 'buy_price': 1.0, 'payout': 1.9, 'spot': 123.45,
                                 'underlying_symbol': 'R_10', 'contract_type': 'DIGITEVEN'}}
            if payload.get('proposal_open_contract'):
                return {'proposal_open_contract': {'contract_id': 12345, 'status': 'open', 'is_sold': 0, 'profit': 0}}
            raise AssertionError(f'unexpected request: {payload}')

    conn = FakeConnection()
    adapter = DerivExecutionAdapter(conn)
    proposal = await adapter.get_proposal(
        symbol='R_10', contract_type='DIGITEVEN', amount=1.0,
        currency='USD', duration=1, duration_unit='t'
    )
    trade = await adapter.buy(proposal, max_price=proposal.ask_price)
    assert trade.contract_id == '12345'
    assert '12345' in adapter.get_open_contracts()

    watcher = asyncio.create_task(adapter.watch_contract('12345', timeout=2))
    await asyncio.sleep(0)
    await conn.handlers['proposal_open_contract'][0]({
        'msg_type': 'proposal_open_contract',
        'proposal_open_contract': {'contract_id': 12345, 'status': 'won', 'is_sold': 1, 'profit': 0.9},
    })
    settled = await watcher
    assert settled['status'] == 'won'
    assert '12345' not in adapter.get_open_contracts()
    assert any(call.get('buy') == 'p1' for call in conn.calls)

@pytest.mark.asyncio
async def test_deriv_connection_uses_otp_for_demo_auth(monkeypatch):
    from core.connection import DerivConnection
    import httpx

    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {'data': {'url': 'wss://api.derivws.com/trading/v1/options/ws/demo?otp=test'}}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def post(self, url, headers):
            assert url.endswith('/trading/v1/options/accounts/VRTC-DEMO/otp')
            assert headers['Authorization'] == 'Bearer token'
            assert headers['Deriv-App-ID'] == 'APP123'
            return FakeResponse()

    monkeypatch.setattr(httpx, 'AsyncClient', FakeClient)
    conn = DerivConnection()
    conn.api_token = 'token'
    conn.app_id = 'APP123'
    conn.account_id = 'VRTC-DEMO'
    conn.demo_only = True
    url = await conn._get_authenticated_ws_url()
    assert '/ws/demo?' in url


@pytest.mark.asyncio
async def test_deriv_connection_rejects_real_url_when_demo_only(monkeypatch):
    from core.connection import DerivConnection
    import httpx

    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {'data': {'url': 'wss://api.derivws.com/trading/v1/options/ws/real?otp=test'}}

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return None
        async def post(self, url, headers): return FakeResponse()

    monkeypatch.setattr(httpx, 'AsyncClient', FakeClient)
    conn = DerivConnection()
    conn.api_token = 'token'
    conn.account_id = 'CR-REAL'
    conn.demo_only = True
    with pytest.raises(PermissionError):
        await conn._get_authenticated_ws_url()
