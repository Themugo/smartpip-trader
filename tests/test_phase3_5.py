from research.historical_opportunity_engine import HistoricalOpportunityEngine, HistoricalTick
from phase4.paper_trader import PaperTrader
from phase5.certification import ProductionCertification, CertificationPolicy


def ticks(n=30):
    return [HistoricalTick(timestamp=f"2026-01-01T00:{i:02d}:00", symbol="R_100", price=100+i, digit=(100+i)%10) for i in range(n)]


def quote_provider(tick, contract, duration):
    return {"payout": 1.9, "stake": 1.0}


def predictor(history):
    return 0.60


def test_phase3_generates_realized_opportunities():
    rows = HistoricalOpportunityEngine().generate(ticks(), contract_type="CALL", duration=2, predictor=predictor, quote_provider=quote_provider)
    assert len(rows) == 28
    assert all(r.won for r in rows)
    assert all(r.payout == 1.9 for r in rows)


def test_phase4_uses_same_ev_gate():
    rows = HistoricalOpportunityEngine().generate(ticks(), contract_type="CALL", duration=2, predictor=predictor, quote_provider=quote_provider)
    report = PaperTrader(min_probability=.55, min_expected_value=.01).run(rows)
    assert report["approved_trades"] == 28
    assert report["equity_change"] > 0


def test_phase5_fails_closed_until_evidence_exists():
    result = ProductionCertification(CertificationPolicy(min_oos_samples=10, min_paper_trades=10, min_paper_approved_trades=5)).evaluate(
        oos_report={"sample_size": 20, "mean_ev": .1, "positive_ev_rate": .7, "ece": .03},
        paper_report={"paper_decisions": 20, "approved_trades": 10, "max_drawdown": .05},
        calibration_ready=False,
        model_version="test",
    )
    assert not result.certified
    assert "calibration artifact is not ready" in result.reasons

def test_phase5_live_gate_requires_two_explicit_conditions(tmp_path):
    from phase5.live_gate import LiveCertificateGate
    path = tmp_path / 'certificate.json'
    path.write_text('{"certified": true}', encoding='utf-8')
    gate = LiveCertificateGate(str(path))
    assert not gate.status(live_enabled=True, confirmation='').get('allowed')
    assert gate.status(live_enabled=True, confirmation='I_UNDERSTAND_LIVE_RISK').get('allowed')
