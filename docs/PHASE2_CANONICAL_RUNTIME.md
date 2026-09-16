# SmartPip Trader — Phase 2 Canonical Runtime Policy

## Rule
Only the canonical Deriv execution adapter may place live orders. Research, backtest, strategy-marketplace and legacy executor modules are non-authoritative unless explicitly invoked by the canonical pipeline.

## Classification
- CANONICAL: `core/connection.py`, `trading/deriv_execution.py`, `risk_engine/`, active AI/research pipeline, API trade gate.
- SUPPORTING: feature engineering, analyzers, persistence, monitoring, risk controls.
- RESEARCH: `backtest/`, `validation/`, offline intelligence experiments.
- DEPRECATED: `trading/executor.py` raw WebSocket execution path. It remains for compatibility only and must not be called by live code.
- EXPERIMENTAL: cognitive/RL/self-improvement components until validated out-of-sample.

## Promotion rule
No strategy/model is promoted because of raw accuracy or in-sample profit. Promotion requires contract-specific, payout-aware expected value, calibration, temporal OOS validation, sufficient sample size and risk checks.

## Phase 2 artifacts
`validation/ai_calibration.py` provides: probability calibration (Brier/ECE/log loss), broker-payout-aware EV, contract/market/regime grouping, Wilson confidence intervals, walk-forward OOS windows and a deployment gate.

## Live trading remains disabled by default
`live_trading_enabled=False` remains the safe default. Validation artifacts are research/paper-trading tools and do not authorize live execution.
