#!/usr/bin/env python3
"""Fit Phase-2 probability calibration from settled opportunity JSONL."""
import argparse, json
from intelligence.probability_calibration import fit_artifact

p=argparse.ArgumentParser()
p.add_argument("input", help="JSONL opportunity journal")
p.add_argument("output", help="Calibration artifact JSON")
p.add_argument("--min-context-samples", type=int, default=200)
a=p.parse_args()
rows=[]
with open(a.input, encoding="utf-8") as f:
    for line in f:
        if line.strip(): rows.append(json.loads(line))
artifact=fit_artifact(rows, min_context_samples=a.min_context_samples)
with open(a.output,"w",encoding="utf-8") as f: json.dump(artifact,f,indent=2)
print(json.dumps({"rows":len(rows),"contexts":len(artifact["contexts"]),"output":a.output},indent=2))
