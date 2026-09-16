# SmartPip Trader — Canonical Runtime

## Live trading authority

The only supported live execution flow is:

`Deriv ticks -> AnalysisManager -> ResearchOrchestrator/IntelligenceOrchestrator -> TradeApprover -> DerivExecutionAdapter -> proposal -> buy -> proposal_open_contract -> outcome -> learning/persistence`

The browser may consume public ticks for visualization, but it must not own a broker trading token or open a second trade socket.

## Deprecated compatibility stacks

The repository contains older/experimental modules retained for research and compatibility. They are not live execution authorities:

- `trading/executor.py` — legacy raw WebSocket executor.
- `trading/monitor.py` — legacy time-based portfolio polling monitor.
- `core/deriv_api.py` — legacy Deriv socket implementation.
- `execution/engine.py` — generic/simulation execution abstraction; not the Deriv broker adapter.
- `api/hardened_routes.py` — historical validation layer with a static market list.
- `WorkspaceContainer` / `TradingWorkspace` and related demo workspace components — presentation/research paths only.

Do not route new live-order functionality through these modules.

## Safety invariants

1. Live trading is disabled unless `LIVE_TRADING_ENABLED=true`.
2. A current tick is required; stale AI decisions are rejected.
3. The AI must nominate an executable Deriv contract family.
4. A fresh Deriv proposal is required before every order.
5. Expected value is computed from the broker's current payout and ask price.
6. Probability and EV must pass the final `TradeApprover` gate.
7. Account-equity stake caps, cooldown, and open-contract limits apply before buy.
8. Contract settlement is observed through `proposal_open_contract`, not a fixed sleep.
9. Execution and socket response correlation belongs to `DerivConnection`; no other live path may call `recv()`.
10. Any AI/broker uncertainty fails closed.

## Profitability claim boundary

The system is designed to seek positive expected value under changing market conditions and to learn from settled outcomes. It cannot guarantee a win on every trade or profit every day. Validation must therefore rely on out-of-sample walk-forward results, live paper/demo observations, drawdown, and calibrated probability/EV metrics before real-money enablement.
