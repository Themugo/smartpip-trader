#!/usr/bin/env python3
"""Run Phase-4 paper execution from an Opportunity JSONL journal."""
import argparse, json
from validation.ai_calibration import load_jsonl
from phase4.paper_trader import PaperTrader
p=argparse.ArgumentParser(); p.add_argument('input'); p.add_argument('--output',default='phase4_paper_report.json'); p.add_argument('--min-probability',type=float,default=.55); p.add_argument('--min-ev',type=float,default=0.0)
a=p.parse_args(); rows=load_jsonl(a.input); trader=PaperTrader(min_probability=a.min_probability,min_expected_value=a.min_ev); report=trader.run(rows)
with open(a.output,'w',encoding='utf-8') as f: json.dump(report,f,indent=2,default=str)
trader.save(a.output+'.jsonl'); print(json.dumps(report,indent=2))
