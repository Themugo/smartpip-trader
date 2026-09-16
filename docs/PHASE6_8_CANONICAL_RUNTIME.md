
# SmartPip Trader — Phase 6-8 Canonical Runtime

## Phase 6 — Reproducible data laboratory
- Dataset ingestion accepts CSV, JSON and JSONL.
- Every source file receives a SHA-256 provenance record.
- Dataset manifests are content-derived and timestamped.
- Rows are deterministically ordered.
- Drift monitoring flags material distribution changes.

## Phase 7 — Live shadow / paper operations
- Decisions can be recorded against live observations without broker orders.
- Settlements are attached to the original decision ID.
- Model health requires settled observations and positive mean EV.
- Drift/unhealthy conditions are promotion blockers.

## Phase 8 — Controlled optimization
- Candidate changes require out-of-sample evidence.
- Promotion requires minimum OOS sample size, minimum EV improvement,
  drawdown within policy, and a model version.
- Promotion is recorded with a deterministic SHA-256 fingerprint.
- No optimizer module can place a broker order.

## Live-trading invariant
Phase 6-8 are research, shadow, paper and promotion controls. They never
call Deriv buy/sell. Only the canonical broker execution adapter may place
an order, and Phase 5 certification remains mandatory.
