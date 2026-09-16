from intelligence.probability_calibration import fit_artifact, ProbabilityCalibrator
import json

def rows():
    return [{"market":"R_100","contract_type":"CALL","duration":5,"regime":"TREND","probability":i/100,"won":i>=55} for i in range(1,100)]

def test_fit_and_transform(tmp_path):
    art=fit_artifact(rows(), min_context_samples=20)
    path=tmp_path/"calibration.json"; path.write_text(json.dumps(art))
    c=ProbabilityCalibrator(str(path), min_context_samples=20)
    r=c.transform(.8,market="R_100",contract_type="CALL",duration=5,regime="TREND")
    assert r.calibrated
    assert 0 <= r.probability <= 1

def test_missing_artifact_is_uncalibrated(tmp_path):
    c=ProbabilityCalibrator(str(tmp_path/"missing.json"))
    r=c.transform(.8,market="R_100",contract_type="CALL",duration=5,regime="TREND")
    assert not r.calibrated
