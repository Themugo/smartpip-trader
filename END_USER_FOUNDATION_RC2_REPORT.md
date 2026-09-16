# SmartPip Trader — End-User Foundation RC2

## Purpose
This revision starts from the complete End-User Foundation package and hardens the customer-facing path before any admin/operations console is built.

## Implemented in RC2

### Authentication
- Fixed TypeScript authentication integration.
- Added password-reset flow through Supabase Auth.
- Normalized customer email input before authentication.
- Preserved a neutral reset response so account existence is not disclosed.

### Onboarding
- Fixed the skip path so it completes with the current profile instead of calling the completion callback without its required argument.
- Removed avoidable `any` casts from onboarding selections.
- Reworded onboarding claims toward evidence, risk awareness and optional automation rather than guaranteed outcomes.
- Profile completion remains persisted to the authenticated user's `profiles` row.

### End-user data isolation foundation
- Added `user_trading_settings` with per-user RLS.
- Added `broker_connections` with per-user RLS.
- Broker connection records deliberately contain account metadata only; no Deriv PAT/JWT secret is stored in the browser or these tables.
- Added `contract_id` to `trade_journal` for future settlement reconciliation.
- End-user performance/trade data now reads from the authenticated user's `trade_journal` rather than the legacy shared trading tables.
- End-user settings now read/write `user_trading_settings`.
- Existing legacy API data remains available only to the intentionally offline/legacy shell path.

### Trading UX and safety
- Manual Rise/Fall execution now requires the requested direction to match the backend AI's current Rise/Fall direction.
- Manual trade API calls disable automatic retries to avoid duplicate broker orders after ambiguous network failures.
- UI validates market connectivity, stake minimum and integer tick duration before submission.
- CALL/PUT controls are disabled unless the AI confidence gate is currently qualified and the selected side matches the AI direction.
- Successful broker acceptance creates a user-owned journal execution record with contract ID for later settlement reconciliation.
- Auto execution state is only changed after the user-scoped settings update succeeds.
- Auto execution and manual execution continue to depend on the existing server-side risk/approval gates.

### Deriv market feed
- Confirmed against current Deriv documentation that the public Options WebSocket endpoint is supported for unauthenticated market data.
- Tick subscription switching now uses the returned subscription ID with `forget` instead of attempting to unsubscribe by sending `subscribe: 0`.
- Reconnect and manual reconnect states are surfaced to the user.

### AI experience
- AI polling is limited to the Trade, AI Analysis and Auto Execution views.
- Stale AI results are cleared when the backend is unavailable instead of being presented as current.
- The UI distinguishes a qualified setup from WAIT/temporarily unavailable states.

## Backend boundary
The canonical FastAPI trading service remains a server-side single-process execution service. RC2 does **not** claim that one process can safely execute independent Deriv sessions for arbitrary customers.

Before enabling production customer auto-trading at scale, the next backend pass must implement:

1. authenticated Supabase JWT verification at customer trading routes;
2. a per-user Deriv connection/session manager;
3. server-side storage of broker secrets outside browser storage;
4. user-scoped execution, open-contract monitoring and settlement persistence;
5. user-scoped risk limits and kill switches;
6. settlement reconciliation into `trade_journal` by `contract_id`;
7. authenticated audit trails;
8. an end-to-end demo-account lifecycle test with a real authenticated customer session.

Until those are complete, the customer UI is a foundation and not a claim of production multi-tenant live trading readiness.

## Verification performed in this environment
- Python regression suite: **945 passed, 4 skipped**.
- Python compile check for application/test packages: **PASS**.
- Changed frontend-file parse check: **PASS**; no TypeScript syntax diagnostics were emitted. Full frontend type/build certification requires the dependency tree to be installed.
- Current Deriv public Options WebSocket endpoint was checked against official Deriv documentation.

## Local verification still required
The repository package does not include `node_modules` and this build environment could not complete a fresh npm dependency download. Run locally:

```bat
npm install --package-lock-only
npm ci
npm run typecheck
npm run lint
npm run build
```

The local lock file may already have been regenerated during the previous verification pass. Preserve that synchronized `package-lock.json` when replacing the source package if necessary.

## Security note
Do not place Deriv PAT/JWT credentials in `VITE_*` variables, localStorage, browser code, or source control. The browser-side market feed is public read-only data; account-scoped trading credentials belong on the server-side connection layer.
