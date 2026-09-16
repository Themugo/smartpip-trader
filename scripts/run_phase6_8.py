
"""Run offline Phase 6-8 checks. No broker orders are possible from this script."""
import argparse, json
from pathlib import Path
from phase6 import DatasetBuilder, DriftMonitor
from phase7 import ModelHealthMonitor
from phase8 import ConstrainedOptimizer

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data", nargs="*", default=[])
    ap.add_argument("--baseline", nargs="*", type=float, default=[])
    ap.add_argument("--recent", nargs="*", type=float, default=[])
    args=ap.parse_args()
    out={"phase6": {}, "phase7": {}, "phase8": {}}
    if args.data:
        b=DatasetBuilder(); rows=b.load(args.data); m=b.manifest(args.data, rows)
        out["phase6"]["manifest"]=m.to_dict()
    if args.baseline or args.recent:
        out["phase6"]["drift"]=DriftMonitor().compare(args.baseline,args.recent).to_dict()
    out["phase7"]["health_contract"]="ModelHealthMonitor.evaluate(probabilities, outcomes, evs)"
    out["phase8"]["promotion_contract"]="ConstrainedOptimizer.evaluate(...); promote(...)"
    print(json.dumps(out, indent=2))
if __name__=="__main__": main()
