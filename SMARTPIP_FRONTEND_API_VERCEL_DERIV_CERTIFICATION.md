# SmartPip Trader — Frontend / API / Vercel / Deriv Certification Pass

## Foundation

This pass starts from the `SmartPip-Trader-FULL-STABILIZED-CONTINUATION` package and preserves the prior backend stabilization work.

## Frontend + API contract corrections

1. Canonical trade execution is `/api/trade`.
2. The frontend previously called `/api/v2/trade`, but no `/api/v2/trade` route exists. This was corrected.
3. Frontend API calls now honor `VITE_API_URL`, allowing the Vite frontend to run on Vercel while the FastAPI trading service runs separately.
4. Review and journal calls now use the same configurable backend origin instead of assuming same-origin API hosting.
5. Production frontend environment diagnostics require `VITE_API_URL` to be present at build/runtime configuration time.
6. Deriv API tokens remain server-side; no `VITE_DERIV_API_TOKEN` path is used.

## Backend trade-contract corrections

1. Manual trade requests now apply the equity stake cap before requesting a broker proposal.
2. Browser-supplied prediction is informational only; approval probability is sourced from backend AI state.
3. Manual live execution now passes through probability calibration and the final `TradeApprover` gate.
4. Manual contracts are registered in the canonical trade store before monitoring starts.
5. Manual contracts are connected to intelligence outcome recording.
6. Automated and manual canonical trades now include `entry_time`.
7. Database persistence falls back from `entry_time` to `created_at` and from `exit_time` to `completed_at`, preventing silent settlement persistence loss.

## Deriv execution lifecycle

The canonical lifecycle is:

`authenticated session -> proposal -> probability/calibration -> TradeApprover -> buy -> proposal_open_contract subscription -> terminal settlement -> database/intelligence persistence`

The Deriv adapter was hardened so handlers are registered before buy/monitoring, quoted buy price cannot exceed the proposal price, and terminal initial contract responses clean up open-contract state.

### Current Deriv API compatibility

The current Deriv documentation describes authenticated trading through the REST OTP endpoint followed by an authenticated demo/real WebSocket URL. The implementation now supports this path using:

- `DERIV_API_TOKEN`
- `DERIV_APP_ID`
- `DERIV_ACCOUNT_ID`
- `DERIV_API_URL` (default `https://api.derivws.com`)
- `DERIV_DEMO_ONLY=true` for controlled demo certification

Legacy direct WebSocket authorization remains only as an explicit compatibility path when `DERIV_WS_URL` is supplied without `DERIV_ACCOUNT_ID`; it is not the preferred certification path.

## Test results

Full Python suite:

`941 passed, 4 skipped`

Skipped tests require external conditions (real Deriv credentials / long-running observability conditions). No test failures or collection errors remain.

Additional lifecycle regression coverage verifies:

- proposal response parsing
- buy response parsing
- contract subscription
- terminal settlement event handling
- open-contract cleanup
- database settlement persistence
- frontend/backend route alignment
- current Deriv OTP demo URL enforcement
- rejection of a real-account WebSocket URL when `DERIV_DEMO_ONLY=true`

Python compile check: PASS.

FastAPI OpenAPI contract check:

- `/api/trade`: PRESENT
- `/api/v2/trade`: ABSENT (expected)
- `/api/health`: PRESENT
- total OpenAPI paths observed: 84

## Frontend build status

A real Vite build/typecheck could not be certified in this execution environment because the package's `node_modules` tree is not installed and outbound npm registry access is unavailable. A global TypeScript binary was able to run, but its output is dominated by missing installed React/Vite dependencies and therefore cannot be treated as source-level build failures.

Required local certification commands:

```text
npm ci
npm run typecheck
npm run lint
npm run build
```

## Vercel status

The connected Vercel scope currently returns HTTP 403 for the SmartPip project/deployment, so deployment logs and project configuration could not be inspected or a deployment could not be certified from this environment.

The previous GitHub status for commit `3e633e1b53695082744b75c0c95f8e06afd809aa` reports the Vercel check as `failure`. That status belongs to the prior GitHub commit and does not certify this continuation package because these changes have not been pushed to GitHub in this pass.

The frontend architecture is now explicitly compatible with separate Vercel frontend + FastAPI backend hosting through `VITE_API_URL`.

## Real Deriv demo execution status

A real demo buy was **not executed in this environment** because no `DERIV_API_TOKEN` / `DERIV_ACCOUNT_ID` credentials were available and outbound network/DNS access to Deriv was unavailable. No fabricated trade, contract ID, or settlement result is reported.

The complete lifecycle is covered by deterministic mock integration tests. To certify a real demo trade, the next run must use a dedicated Deriv demo account with `DERIV_DEMO_ONLY=true`, current Deriv application credentials, a valid calibration artifact, and `LIVE_TRADING_ENABLED=true`.

## Certification conclusion

### Certified

- Backend regression suite
- Frontend/backend API route contract
- Manual execution gate hardening
- Canonical persistence lifecycle
- Mock proposal → approval → buy → monitoring → settlement → persistence lifecycle
- Current Deriv OTP authentication contract at unit-test level
- Demo-only account URL enforcement

### Not yet externally certified

- Vite typecheck/lint/build in a fully installed Node environment
- Vercel deployment/build/runtime
- Real Deriv demo WebSocket connection
- Real demo proposal/buy/settlement

No production-readiness or 100% certification claim is made until those external gates are exercised.
