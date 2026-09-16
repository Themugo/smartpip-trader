# Phase 3–5 Runbook

1. Collect ordered Deriv tick records and, ideally, the contemporaneous proposal quotes.
2. Run Phase 3 to generate opportunities and OOS metrics.
3. Fit/re-fit calibration from settled opportunities with `scripts/fit_calibration.py`.
4. Run Phase 4 paper execution using the same calibrated probabilities and approval thresholds.
5. Run `scripts/certify_phase5.py` only after the OOS and paper reports satisfy policy.
6. Store the resulting certificate outside source control if it authorizes a real account.
7. The runtime remains blocked unless the explicit live flags are set.

Do not use synthetic simulator profitability as evidence of a real Deriv edge. Synthetic data is for pipeline testing only.
