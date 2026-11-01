# Phase 3 implementation plan

Preserve the existing experiment engine and frontend. Add an independently typed research layer using the same database, invariant evaluator, authentication, Celery outbox and evidence conventions.

1. Add durable research jobs/trials/decisions/deduplicated findings/candidates/evidence with an additive Alembic migration and fenced cancellation/recovery.
2. Extend the demo suite with a managed four-process HTTP benchmark runtime. Six actual workflow/idempotency/compensation defects and shipped reference policies execute against authoritative persistent state. Bounded per-request fault plans record application receipts; missing evidence, unobserved injections and infrastructure errors remain distinct.
3. Implement seeded random and coverage baselines, cost-aware contextual UCB selection, budget enforcement and recorded decisions. Compare strategies using equal candidate spaces/budgets/seeds; report measured outcomes without assuming superiority.
4. Implement repeated-trial ddmin and timing/input reduction, preserving the same invariant signature and reporting only the tested local neighborhood.
5. Implement deterministic competing hypotheses and paired fault/input interventions; optional validated local LLM proposals cannot assert observations or invariant truth.
6. Generate constrained source policy patches into isolated workspaces. Execute candidates only through a restricted Docker sandbox agent with no network, mounted credentials or arbitrary command API. Docker unavailability must return infrastructure error, never a verification pass.
7. Implement independent matched original/candidate verification with related and held-out cases, regression controls, actual wall/gateway CPU measurements and complete evidence. Trusted shipped reference comparisons are explicitly separate from candidate verification.
8. Integrate real research API data into adaptive exploration, AI investigation, minimization, patch review, verification and benchmark workspaces using the existing design system.
9. Run migrations, algorithm/security/API/HTTP integration tests, frontend checks/build and browser workflows; preserve exact results and unavailable infrastructure limits.
10. Review and scan staged changes; commit and push without force, then verify remote ancestry/hash.

The contribution is an integrated experimental pipeline with bounded claims, not a claim of global novelty, global minimality, formal causality or bug-free repair. General arbitrary repository repair is outside the supported benchmark patch space; unsupported proposals are rejected rather than executed on the host.
