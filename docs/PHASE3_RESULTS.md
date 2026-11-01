# Phase 3 measured delivery results

This report records executed checks, not expected outcomes. The detailed bounded
architecture and exact startup/agent commands are in [PHASE3.md](PHASE3.md).

## Implemented

Preserved Phase 1/2 and added durable research APIs/jobs, seeded random and coverage
baselines, contextual cost-aware linear UCB, repeated ddmin/parameter reductions,
six competing mechanisms with paired interventions, optional validated local model
proposals, isolated literal-policy patch preparation, restricted Docker verification
agent, independent matched/held-out/regression comparison, six real HTTP benchmark
defects/reference variants, and six connected frontend research workspaces.

Repair is deliberately limited to the packaged benchmark recovery-policy surface.
No arbitrary repository program repair, automatic merge or deployment is claimed.

## Actual checks

* Backend: **57 passed, 1 skipped** in 71.26 seconds on the final algorithm code.
  The skip is generated-candidate execution inside Docker because `docker` is absent.
  Includes SQLite Alembic upgrade/check/downgrade, real HTTP defects/fixed controls,
  true two-fault reduction, missing evidence handling, cancellation/timeouts/fencing,
  real Redis/Celery worker kill/restart recovery, persistence, agent command isolation,
  model proposal validation and regression detection.
* Frontend: **48 unit/component/API tests passed**; ESLint, strict TypeScript and
  production build passed. Browser results: **4 Chrome scenarios passed** (55.5s),
  including the complete discovery/reduction/investigation/patch/availability flow,
  legacy experiment evidence, 13-page navigation, mobile and axe accessibility checks.
  The final browser run verifies the prominent infrastructure outcome and evidence
  refresh when jobs complete.
* Compose YAML parsed: **18 services**. PostgreSQL DDL compiled offline. Actual
  PostgreSQL/Compose deployment, Linux prefork time limits and generated candidate
  containers were **not tested**, since Docker/PostgreSQL are unavailable here.
* Live Ollama inference was not tested; no model is required. Structured proposal
  validation and rejecting fabricated evidence IDs were tested with transport fixtures.
* Staged secret scan: **zero candidates**. Remote commit/push verification is
  recorded in the final delivery artifact after publication.

Atomic conditional database updates fence cancellation, ownership and evidence
publication; the check-to-write ownership race is covered by a regression test.

Earlier checks exposed and fixed an invalid `max_hits=0` minimizer candidate, a
research test's Redis teardown order, and ambiguous verification outcome display.
A development-server cold-loading stall was resolved in the reproducible browser
check by serving the successful production build. No failing tests were disabled.

## Equal-budget benchmark

Benchmark job: `f480d31b-bbbe-4c32-bdc1-e0383193f10c`. Each strategy received six trials for each of
seeds 17, 42, 93, from the same finite candidate space and with empty history.
There were **54 search trials plus 24 documented witness/reference/baseline trials**.
Every execution, including missing injections, consumed budget.

| Strategy | Seed | Trials | Defect families found | First finding at trial | Trial wall cost (s) |
|---|---:|---:|---:|---:|---:|
| random | 17 | 6 | 3 | 2 | 4.772 |
| coverage | 17 | 6 | 3 | 1 | 4.719 |
| adaptive | 17 | 6 | 2 | 1 | 4.661 |
| random | 42 | 6 | 2 | 1 | 3.163 |
| coverage | 42 | 6 | 1 | 4 | 4.650 |
| adaptive | 42 | 6 | 2 | 1 | 4.657 |
| random | 93 | 6 | 2 | 2 | 4.677 |
| coverage | 93 | 6 | 4 | 1 | 4.609 |
| adaptive | 93 | 6 | 2 | 1 | 5.281 |

Mean defect families: random **2.33**, coverage
**2.67**, adaptive
**2.00**. **Adaptive did not improve discovery**
at this small budget. This is not a statistical superiority/generalization claim.
Raw aggregate values, classifications, trial references and runtime/policy hashes
are in [phase3-benchmark-summary.json](phase3-benchmark-summary.json).

All six witness failures reproduced twice with matching signatures. All six clean
baselines and six shipped fixed controls produced NO_VIOLATION. Unexpected control
violations: **0**. This controlled result does
not establish a global false-positive rate. Generated patch verification success
is **unmeasured**, not zero and not a successful reference comparison.

## Observed pipeline

The browser started a real 12-trial payment acknowledgement search, selected an
original violation, and submitted persisted reduction, investigation, repair and
verification jobs. All job lifecycles completed.

Reduction: 1 fault action(s) → 1;
amount 100 → 1; final confirmation
**2/2**. Local finite-neighborhood
minimality audited: **True**. A fixed timeout is not
misreported as reduced latency. Separately, the real two-fault automated test
removes an unnecessary reservation delay, preserving the same violation signature.
No global minimality or deterministic scheduling claim is made.

Causal statuses: acknowledgement=SUPPORTED, retry=INCONCLUSIVE, concurrency=INCONCLUSIVE, finalization=INCONCLUSIVE, compensation=INCONCLUSIVE, reservation=INCONCLUSIVE.
These are controlled benchmark effects, not unique/proven source-level root causes.

A candidate patch was prepared in an isolated copy and passed syntax/literal-policy
static checks. Candidate execution tests: **NOT_RUN**. Final verification outcome:
**INFRASTRUCTURE_ERROR**, because the restricted agent is not
configured. Thus discovery through candidate creation works end to end; generated
patch execution and successful independent container verification remain unvalidated.

## Remaining limitations

Finite controlled benchmark, one global research execution lease, fixed verification
hold-outs, bounded policy-only repair, no full-system CPU/memory profiler, empirical
reproduction rather than formal correctness, and remaining OS/HTTP/database timing
nondeterminism. This is not production deployment, arbitrary service onboarding,
multi-tenant security hardening, or Phase 4.
