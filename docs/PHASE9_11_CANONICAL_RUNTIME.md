# SmartPip Trader — Phase 9–11 Canonical Runtime

## Phase 9 — Research lineage and reproducibility
- Research runs bind strategy, model, dataset, parameters and code revision.
- Every run receives a deterministic SHA-256 fingerprint.
- An append-only JSONL research ledger preserves experiment lineage.

## Phase 10 — API and security hardening
- Bearer sessions are validated against active, unexpired sessions.
- Endpoint permissions are enforced through the canonical RBAC module.
- API keys are persisted as hashes, not plaintext credentials.
- Inactive/locked users cannot authenticate via API keys.
- API errors do not expose internal exception strings.

## Phase 11 — Release, recovery and audit integrity
- Release gates aggregate deterministic checks and fail closed.
- Backup snapshots include SHA-256 manifests and verification.
- Sensitive events can be persisted in a tamper-evident chained audit log.

## Live-trading invariant
Phases 9–11 add research, API, security, release and recovery controls. They do
not add a broker execution path. Live execution remains behind the Phase 5
certificate gate and the canonical execution adapter.
