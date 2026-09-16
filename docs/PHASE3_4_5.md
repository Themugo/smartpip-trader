# SmartPip Trader — Phases 3, 4 and 5

## Phase 3 — Historical Opportunity Laboratory
`research/historical_opportunity_engine.py` replays ordered ticks, asks a supplied predictor for a probability, requires a broker quote, calculates the realized contract outcome, and produces grouped + walk-forward OOS reports.

Supported input: JSONL, JSON array, CSV. No payout is invented: a quote must be supplied.

## Phase 4 — Paper Trading
`phase4/paper_trader.py` uses the same `TradeApprover` contract as live execution but never calls Deriv `buy`/`sell`. It records approved and rejected opportunities, P&L, and drawdown.

Paper trading is intended to run against live market data and recorded Deriv proposals when available. It is not a substitute for real proposal economics.

## Phase 5 — Production Certification
`phase5/certification.py` requires:
- minimum OOS sample size
- positive OOS EV
- sufficient positive-EV rate
- acceptable OOS calibration error
- minimum paper observations and approved trades
- acceptable paper drawdown
- calibration artifact readiness

`phase5/live_gate.py` adds the final fail-closed runtime requirement. Even a certified model does not activate live trading automatically. Live execution additionally requires `LIVE_TRADING_ENABLED=true` and `LIVE_TRADING_CONFIRMATION=I_UNDERSTAND_LIVE_RISK`.

## Promotion policy
Certification is evidence-based and contract-specific. It is not a claim of guaranteed profit. A certificate must be regenerated whenever the model version, calibration artifact, strategy parameters, contract economics, or validation dataset materially changes.
