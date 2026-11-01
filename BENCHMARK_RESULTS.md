# Measured benchmark and acceptance results

Measured 2026-11-01 on native macOS with Python 3.13.15, Node 24.22.2, SQLite and actual Redis/Celery/HTTP services. No LLM or Docker was available. Full synthetic aggregates, trial references, scenarios, implementation hashes and runtime policy hashes: [docs/phase4-benchmark-summary.json](docs/phase4-benchmark-summary.json). Raw local observations remain in the private platform database and ignored work/ records.

## Protocol and results

Protocol `failurelab-synthetic-v2`: six known deliberately seeded defect families; same 36-candidate training catalogue, 12 discovery trials per strategy per seed, seeds 17/42/93, fresh planner with no history for each cohort. Strategy order rotates by seed. Fixed held-outs use amount 37, quantity 3 and latency 275 ms; they do not overlap training scenarios and never update planners. They share the same program families, so this does not evaluate unseen applications. Alpha=1.4; all code/data hashes are in the JSON. No tuning was performed after seeing these results.

| Strategy | Families at seeds 17,42,93 | Mean families ± sample SD | Mean distinct invariant signatures | Mean trials to first finding | Mean summed trial seconds per cohort |
|---|---|---|---|---|---|
| random | 4, 3, 6 | 4.33 ± 1.53 | 5.00 | 1.67 | 9.059 |
| coverage | 4, 4, 6 | 4.67 ± 1.15 | 5.33 | 2.00 | 9.610 |
| adaptive | 3, 3, 3 | 3.00 ± 0.00 | 3.00 | 1.00 | 9.023 |

Adaptive search did **not** improve mean defect-family coverage: 3.00 versus random 4.33 and coverage 4.67. Its mean first finding was earlier in this small study; that is not statistical superiority or a general efficiency claim. Mean family discoveries per allocated trial were random 0.361, coverage 0.389, adaptive 0.250. Multiple invariant signatures can arise from one seeded defect family and must not be counted as novel bugs.

Actual job `7640d88d-32c1-40c4-a281-7ffae11b7f97` completed with **201** HTTP trials: 108 discovery, 24 witness/baseline/reference controls, 24 held-out trials, 24 comparator controls and 21 minimization-control trials. Summed measured trial elapsed cost: **153.949 seconds**. Classifications: 114 APPLICATION_VIOLATION, 71 NO_VIOLATION, 16 INJECTION_NOT_OBSERVED. There were no INCONCLUSIVE/INFRASTRUCTURE_ERROR trial classifications in this completed study. Undelivered faults were never treated as findings.

* All six witness pairs reproduced the same signature (6/6). This is one repeat per family, not an estimated population reliability.
* Held-outs produced 12/12 original violations and 12/12 reference NO_VIOLATION outcomes across six families and two repetitions.
* Zero unexpected invariant violations occurred in shipped-reference/baseline controls. An adjudicated global false-positive rate was **not measured** and remains null.
* The independent comparator returned PATCH_PASSES_TESTED_SCENARIOS for shipped reference recovery and PATCH_FAILS_VERIFICATION for an unmodified vulnerable control (2/2 expected outcomes, six matched cases each). This is calibration on two known controls, not general verification accuracy or generated-candidate verification.
* The two-event concurrent-retry minimization control removed the 10-ms nuisance reservation event (2 → 1 events), reduced charge latency 180 → 90 ms and amount 100 → 1. Each accepted reduction had repeated signature matches. The 20-replay budget exhausted before final confirmations: reproductions=0, confirmation_trials=0 and local_minimality_tested=false. No minimality or final reproduction claim is made for this control.
* The separate acceptance pipeline used budget 40 on payment acknowledgement loss: latency 180 → 90 ms, amount 100 → 1, two final confirmations, local finite-neighborhood minimality tested=true. This is not global minimality.
* Reference-control mean gateway process CPU delta was +0.001565 s; mean wall delta −0.007212 s across its six matched cases. These tiny noisy measurements include controlled waits and do not establish a speedup. Full-system CPU, RSS, load/soak overhead and production resource cost were **not measured**.

## Complete workflow boundary

Normal baseline, controlled payment fault, authoritative invariant failure, adaptive search, reduction, paired causal intervention, isolated candidate preparation, report persistence and browser evidence export all executed. The acknowledgement hypothesis was SUPPORTED by paired trials; five competing mechanisms were INCONCLUSIVE. Candidate verification returned **INFRASTRUCTURE_ERROR** because the restricted Docker agent was unavailable. Candidate code was never executed on the host. The full original/generated-patch counterfactual workflow is therefore **not completely verified**. Shipped reference controls do not close this gap.

Two earlier acceptance attempts expired during large host-time pauses: one benchmark retained 134 trials without a complete report, and a second attempt expired during reduction. They remain in local history and are excluded from completed-cohort statistics. A fresh continuously awaited run completed under the unchanged 600-second job deadlines. Host suspension/time discontinuities can invalidate a run; do not disable deadline fencing to make a benchmark pass.

## Automated validation

| Check | Actual final result |
|---|---|
| Complete backend pytest | 74 passed, 1 skipped, 0 failed (71.98 s) |
| Skipped test | Generated-candidate Docker container integration; Docker unavailable |
| SQLite migrations | Upgrade → metadata drift check → downgrade → re-upgrade passed, including audit schema |
| PostgreSQL migrations | Offline SQL compiled locally; actual PostgreSQL 16 migration round-trip passed in Linux CI |
| Safe shared-CI selection (local) | 29 module tests + 9 selected research tests passed; subset of full suite |
| Frontend lint / TypeScript | Passed |
| Vitest / React Testing Library | 57 passed across 6 files |
| Next production build | Passed |
| Native Mac Google Chrome Playwright | 5 passed, 0 skipped, 0 failed (55.9 s) |
| Host connectivity | Frontend root, API /ready and frontend bridge /ready returned 200 |
| Python tested dependency closure audit | 46 packages, no known vulnerabilities after certifi update |
| Frontend production dependency audit | 0 known vulnerabilities |
| Frontend full dependency audit | 3 moderate, 0 high, 0 critical; development-only generator chain |
| Secret scan | 0 candidates before staging; final staged result recorded in delivery report |
| Docker/Compose builds and host topology | Mac runtime not executed; all four image builds and Compose config passed in Linux CI |

The safe-CI selection was rerun after adding the final operations test. PostgreSQL service and Python 3.12 checks are configured in GitHub Actions, not inferred from local SQLite/Python 3.13 results. Browser verification covers the actual unavailable-agent report, not a passing candidate. Its accessibility scan covers the exercised evidence workspace and responsive navigation, not certification of every UI state.

The first full backend run exposed a clean-checkout child package-resolution error (60 passed, 1 skipped, 13 setup errors); fixed and final full suite passed. The first browser run found a stale completed-job polling race (4 passed, 1 failed); fixed and regression-tested. One later browser retry ran during an incomplete shutdown (5 connection failures); shutdown now waits for its owner and the final run passed. No failing test was disabled.

Residual dependency advisory: openapi-typescript 7.13.0 → @redocly/openapi-core 1.34.22 → minimatch 5.1.9 (GHSA-g3hv-75wg-m249). All three affected npm nodes are development tools. A compatible upstream generator dependency update is still required; no forced breaking major replacement was made. CI blocks high/critical advisories, while these moderate findings remain visible. Audits are advisory-snapshot checks, not proof of absence of vulnerabilities.

## Reproduce

```sh
make start
# Or build/install and make local-start as in LOCAL_SETUP.md.
python scripts/acceptance.py --benchmark --budget 12
python scripts/browser_acceptance.py
# On a Mac prone to sleeping during tests, optionally:
caffeinate -is python scripts/acceptance.py --benchmark --budget 12
```

Each run uses fresh transaction namespaces and idempotency keys; small-sample scheduling outcomes/costs can change. Never overwrite recorded reports to imply exact replay. Docker-capable isolated execution and a disposable PostgreSQL database remain required release gates.

Post-push verification: the [corrected Safe CI run](https://github.com/bhuvzzs24-spec/failurelab-x/actions/runs/41306738900) passed all four jobs on runtime revision bd76773. See [the CI supplement](docs/PHASE4_CI_RESULTS.md) for the initial build failure, correction and precise remote validation boundary.
