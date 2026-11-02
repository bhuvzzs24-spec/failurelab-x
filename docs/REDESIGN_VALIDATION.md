# Redesign validation

Validated against real retained sandbox data on 2 November 2026. No public deployment has been authorized or created.

| Check | Actual outcome |
| --- | --- |
| Full backend `python -m pytest -q backend/tests` | 87 passed, 2 skipped in 76.76 s |
| Frontend lint | Passed |
| TypeScript / Next route types | Passed |
| Vitest | 68 passed in 8 files |
| Next production build | Passed, Next 16.4.3 |
| Chrome Playwright suite | 6 passed in 1.9 min |
| Desktop accessibility | Axe WCAG 2 A/AA and 2.1 AA: no violations on 13 workspace routes |
| Mobile layout | 390 px dashboard, investigator and evidence: no document overflow; existing keyboard/responsive checks passed |
| Real controlled experiment | Completed; actual charged payment/pending order finding and authoritative evidence |
| Real research workflow | Search, reduction, causal intervention, candidate preparation and verification-report/export tests passed |
| Read-only browser boundary | Inspected graph; execution control disabled; POST rejected 403 |
| Published OpenAPI | Unchanged; compared current `app.openapi()` to recorded contract |
| Cloud static safety / browser API boundary | Passed; same-origin API fetches, no direct public localhost fetch URL |
| Python advisory audit | No known vulnerabilities in the pinned dependency closure |
| Frontend production advisory audit | No known vulnerabilities |
| Frontend full advisory audit | Three moderate development-tool advisories; no high/critical; no forced incompatible downgrade applied |
| Secret scan | Zero candidates before staging; staged scan required before commit |
| Snapshot preparation | Actual 8,090,622-byte redacted demo export imported into a fresh local SQLite database; 14 table collections, histories intact; no upload/publication |

The two local backend skips are PostgreSQL reader privilege enforcement and restricted Docker candidate execution where unavailable. Alembic upgrade/check/downgrade tests passed against SQLite; PostgreSQL migrations were not run locally. GitHub CI supplies disposable PostgreSQL for migrations and SELECT-only role enforcement. Container build checks run there; they do not constitute executing candidate code. No local PostgreSQL or Docker success is claimed.

The browser workflow's verification job reports infrastructure availability accurately. Without the restricted Docker agent, it records `INFRASTRUCTURE_ERROR`; it does not establish a passing patch. Existing private experiment/research execution remains functional, and no public worker or production target is configured.

Failures encountered and fixed before the final successful suite: insufficient contrast in execution-stage labels, mobile scroll leakage from a visually hidden table label, and ambiguous selectors after adding richer sequence/read-only displays. One initial research wait exceeded the browser wait while its backend job subsequently completed; the final full run completed normally. Tests were not disabled or replaced with fixture results.

Screenshots are captured by `frontend/e2e/product-design.spec.ts` from the production build and real backend observations. Private raw evidence and browser traces remain ignored and are not committed.

Permanent-host health, external HTTPS browser checks, provider deployment, private release-runner connectivity and production backups remain unexecuted until account/resource/publication approval. See `CLOUD_SETUP.md` for exact setup and safety gates. GitHub CI and push results are recorded separately after the actual remote checks finish.
