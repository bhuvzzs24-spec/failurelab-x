# Phase 1 technical design

## Separation of concerns

`api` handles contracts/authentication; `models` and Alembic define durable state; `repositories/evidence` canonicalizes and hashes bounded artifacts. `experiments` owns orchestration, `faults` owns the restricted proxy, `verification` observes authoritative state, and `invariants` evaluates pure rules. `services/demo` contains role-specific applications; `workers` supplies Celery delivery/recovery. OpenTelemetry request middleware and JSON logs live in `telemetry`.

The orchestration order is prerequisite health checks → manifest → reset → baseline workflow/verification → initial fault-key snapshot → fault lease → workflow → fault removal → bounded observations/evaluations → findings → final cleanup. Failure/cancellation uses the same final cleanup path. Each run snapshots experiment config; invariant records have no mutation API.

## Rule semantics

The safe tagged AST supports `compare` (eq, ne, gte, lte), `implies`, and `transition`. Operands are typed literals or fixed state paths: order/payment/inventory × status/amount/quantity. No arbitrary URL, import, expression evaluator or code deserialization exists.

The pure evaluator returns INCONCLUSIVE for unavailable values, incompatible ordered types, or missing initial state. Implication uses normal short circuit logic. The runner additionally requires all three adapters to be observed, preventing vacuous truth from hiding a failed telemetry/observation adapter.

Transition rules compare initial and observed endpoint states using explicit allowed pairs. They do not prove absence of an unobserved intermediate transition. Compare/implication rules express workflow postconditions and authoritative value equalities. Each postcondition is sampled at configured retry intervals through a bounded consistency window after fault removal. Final PASS is convergence; continuous FAIL across the complete sampled window creates a finding. A final FAIL following a PASS or missing sample is conservatively INCONCLUSIVE. This is sampled evidence, not a proof of behavior between samples. Consistency windows can be zero for immediate postconditions.

Every evaluation stores actual state, rule, evidence IDs, timestamp and an inconclusive reason when applicable. Only FAIL generates a Finding. Business correctness depends on the operator choosing authoritative adapters and appropriate windows.

## Observation authorization

Only operator-defined Compose/loopback origins are allowed at settings construction; public registration accepts logical service identities, never destinations. Observer calls a fixed `/state/{safe-workflow-key}` endpoint with the control token. HTTP errors and malformed state are missing observations. A successful explicit `status: absent` response proves absence at that source. Snapshots from different databases are sequential, not atomically consistent; the verification window reduces transient-read sensitivity.

## Fault safety

The proxy only accepts bounded POST `/charge` traffic to the fixed payment origin. It implements before/after latency, withheld-response timeout, 503, TCP reset (SO_LINGER), and boundary unavailability. The last two timeout/unavailability modes both suppress forwarding before-phase and withhold response after-phase; they do not modify routing or kernel firewall rules. `worker_interrupt` pauses the real payment processing loop through an authenticated TTL control while queued requests remain durable.

Only one fault lease is active; its execution ID must match the request. Lease expiry is monotonic and capped at 30 s; active delays wake when a lease is removed/replaced. A restarted proxy starts clean. Payment pause has its own monotonic TTL and also clears on restart. Rollback removes fault behavior; it does not roll back business side effects or cancel a committed payment. Existing HTTP requests can still finish after cleanup. Workflow keys isolate those effects from later experiments.

A sandbox row is atomically acquired before reset. It remains held for 165 s from claim (130 s Celery hard limit + 30 s maximum fault TTL + 5 s margin) unless the owning worker has stopped its work and confirmed cleanup. A duplicate/late worker cannot claim an active run. Every status write is fenced by run owner and rejects terminal rows. One Celery scheduler is required; dispatcher publication is at least once and consumers claim via database CAS. Redis AOF and Celery late acknowledgements/rejection-on-worker-loss help delivery. Database outbox redispatch covers broker publication gaps.

A watchdog runs every five seconds via Celery beat. Recovery retains the sandbox lease even after successful cleanup because a stale owner may still be running; only the cooperative owner or the safety-bound expiry releases it. The production worker must use Celery prefork (Compose default) so its hard time limit is enforced. Queue waits count against a run deadline; new runs queued during a crash hold may expire and should be resubmitted after the hold. It terminalizes expired runs and attempts cleanup; it cannot make progress while all workers/broker are unavailable, so independent target-side TTL is the primary crash safety boundary. No automatic transaction replay occurs after worker loss. Operator starts a fresh run with new keys. Runtime maximum is 90 s; queue waiting counts against the deadline.

## Evidence and extension points

Artifacts contain config/seed, engine/Python versions, service-reported build revisions, fault schedule, exact workflow input/outcome, initial/baseline/verification states, baseline and final evaluations, lifecycle/recovery/cleanup events, and reproduction instructions. The summary API forms a retrievable evidence package. SHA-256 covers canonical sorted compact JSON, not database transport encoding. Arbitrary artifact paths are absent.

Request logs and spans are emitted to bounded container stdout logs with execution/trace correlation. Workflow artifacts persist trace IDs and log source references; raw stdout and full span bodies are not copied into the database. Export/archive logs separately for durable trace retention. There is no OTLP collector or trace-to-graph importer in this phase.

Seed is metadata for future randomized plans; current workflow uses no random decisions. Execution IDs/idempotency keys differ each run. Exact replay is not promised: scheduler timing, network/database latency, mutable image tags and dependencies can differ. Image identifiers come from BUILD_VERSION; an immutable digest is only known if the operator supplies it. Findings never claim a seed proves determinism.

Phase 2 can consume the typed graph/run/timeline/evidence schemas, add OTel import with provenance, alternate observer adapters and experiment workflows, and build an interactive frontend. A later planner should produce these same validated experiment/rule contracts. No planner or LLM was added.

## Explicit limits

One destructive demo sandbox; payment is the only injectable boundary. No arbitrary workflows, user code, production onboarding or multi-tenant authorization. Demo has one SKU with stock 100 and fake payment processing, not a complete commerce system. Operator can set before-phase faults to prevent side effects; after-phase faults model lost acknowledgements.

Deployment remains local: shared development database bootstrap accounts, bearer tokens, no TLS, no tenant RBAC, no external secret store, no dependency lock/digest signing, and no automated evidence retention/export service. Container controls and fixed destinations are implemented, but this is a foundation for production engineering rather than a claim of production certification.
