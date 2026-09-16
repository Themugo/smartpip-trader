
from pathlib import Path
import json
from phase6 import DatasetBuilder, DriftMonitor
from phase7 import ShadowSession, ModelHealthMonitor
from phase8 import ConstrainedOptimizer

def test_dataset_manifest_is_reproducible(tmp_path):
    p=tmp_path/"ticks.csv"
    p.write_text("timestamp,symbol,price\n2026-01-01T00:00:00Z,R_100,100.1\n", encoding="utf-8")
    b=DatasetBuilder(); rows=b.load([p]); m=b.manifest([p], rows)
    assert m.row_count == 1 and m.symbols == ["R_100"] and len(m.dataset_id)==24

def test_drift_monitor_flags_large_shift():
    r=DriftMonitor().compare([1,1,1,1],[2,2,2,2])
    assert r.alert is True

def test_shadow_session_never_places_orders():
    s=ShadowSession()
    d=s.record(decision_id="x",symbol="R_100",contract_type="RISE",probability=.7,payout=.8,stake=1,ev=.26,approved=True)
    s.settle("x",1)
    assert d.pnl == .8
    assert not hasattr(s, "buy")

def test_model_health_blocks_insufficient_data():
    h=ModelHealthMonitor().evaluate([.7],[1],[.2],min_samples=100)
    assert not h.healthy

def test_optimizer_rejects_in_sample_only_candidate():
    o=ConstrainedOptimizer(min_oos_samples=500)
    r=o.evaluate("s",.1,.5,10,.05,{"model_version":"v2"})
    assert not r.accepted

def test_optimizer_accepts_sufficient_oos_candidate():
    o=ConstrainedOptimizer(min_oos_samples=500,min_improvement=.02)
    r=o.evaluate("s",.1,.14,1000,.10,{"model_version":"v2"})
    assert r.accepted
