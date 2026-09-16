from validation.ai_calibration import Opportunity, summarize, validation_gate, walk_forward

def make(n=20):
    return [Opportunity(timestamp=f"2026-01-{(i//4)+1:02d}T00:{i%60:02d}:00", market="R_100", contract_type="CALL", duration=5, regime="TREND", probability=0.75, payout=1.25, stake=1.0, won=(i % 4 != 0)) for i in range(n)]

def test_ev_and_break_even():
    r=make(1)[0]
    assert r.break_even_probability == 0.8
    assert r.expected_value == -0.0625

def test_summary_and_groups():
    rep=summarize(make(20))
    assert rep.sample_size == 20
    assert rep.groups[0]["sample_size"] == 20
    assert 0 <= rep.ece <= 1

def test_gate_rejects_negative_ev():
    rep=summarize(make(20))
    gate=validation_gate(rep, min_samples=10, min_mean_ev=0.0)
    assert not gate.passed

def test_walk_forward_is_temporal():
    rows=make(30)
    windows=walk_forward(rows, train_size=10, test_size=5)
    assert windows
    assert windows[0]["train_end"] <= windows[0]["test_start"]
