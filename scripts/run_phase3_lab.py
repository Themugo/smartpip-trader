#!/usr/bin/env python3
"""Run Phase-3 historical opportunity analysis from tick + quote journals."""
import argparse, json
from research.historical_opportunity_engine import HistoricalOpportunityEngine, load_ticks

p=argparse.ArgumentParser()
p.add_argument('ticks')
p.add_argument('--contract', required=True)
p.add_argument('--duration', type=int, required=True)
p.add_argument('--payout', type=float, required=True)
p.add_argument('--probability', type=float, required=True)
p.add_argument('--regime', default='UNKNOWN')
p.add_argument('--output', default='phase3_report.json')
a=p.parse_args()
rows=HistoricalOpportunityEngine().generate(
    load_ticks(a.ticks), contract_type=a.contract, duration=a.duration, regime=a.regime,
    predictor=lambda history: a.probability,
    quote_provider=lambda tick, contract, duration: {'payout': a.payout, 'stake': 1.0},
)
report=HistoricalOpportunityEngine.matrix(rows, train_size=max(1,min(500,len(rows)//2)), test_size=max(1,min(100,len(rows)//4))) if rows else {'sample_size':0}
with open(a.output,'w',encoding='utf-8') as f: json.dump(report,f,indent=2,default=str)
print(json.dumps({'opportunities':len(rows),'output':a.output},indent=2))
