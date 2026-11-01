# Phase 4 integration and delivery plan

Baseline: a1aee111c1b3e405d59c315cd1e9e00c51abb5c5, clean main matching origin.

1. Preserve existing engines. Add role-based API authorization, fail-closed hosted configuration, distributed rate limits, persistent sanitized audit events and explicit read-only access.
2. Repair operational integration: current-schema readiness, controlled shutdown/restart, dependency health, persistent storage, host connectivity checks and make start/stop/restart/status/logs/test.
3. Prepare a public read-only frontend boundary; preserve local control UI, hide unsupported hosted mutations, keep credentials server-side and restrict upstream origins.
4. Add leakage-separated benchmark evaluation with fixed held-out scenarios, repeated seeds/equal budgets, real state outcomes, controls, measured cost and honest unmeasured fields.
5. Add safe CI: curated non-fault unit/API checks plus PostgreSQL migrations and Redis security checks; no fault or patch workloads on shared runners. Integration remains operator-owned and isolated.
6. Run backend/security/migration checks, frontend lint/types/unit/build, real local workers and Chrome end-to-end tests. Record precise unavailable Docker/PostgreSQL/model checks.
7. Add requested architecture, user, experiment, AI, benchmark, security, deployment, local setup and limitation documents. No public deployment or repository visibility changes.
8. Review/scan, commit the authorized message, push without force and verify remote/main and workspace state.

Docker and PostgreSQL executables are absent at inspection. Container verification and Compose host validation must remain unverified unless infrastructure becomes available. A running native Mac/SQLite/Redis stack can independently validate actual host localhost access; it does not substitute for Docker/PostgreSQL verification.
