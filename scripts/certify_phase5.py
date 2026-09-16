#!/usr/bin/env python3
"""Create a Phase-5 production certificate from OOS and paper reports."""
import argparse, json
from phase5.certification import ProductionCertification, CertificationPolicy, write_certificate
p=argparse.ArgumentParser(); p.add_argument('oos'); p.add_argument('paper'); p.add_argument('--calibration-ready',action='store_true'); p.add_argument('--model-version',default='unknown'); p.add_argument('--output',default='intelligence_data/production_certificate.json'); a=p.parse_args()
with open(a.oos,encoding='utf-8') as f: oos=json.load(f)
with open(a.paper,encoding='utf-8') as f: paper=json.load(f)
result=ProductionCertification(CertificationPolicy()).evaluate(oos_report=oos,paper_report=paper,calibration_ready=a.calibration_ready,model_version=a.model_version)
write_certificate(result,a.output); print(json.dumps(result.to_dict(),indent=2))
