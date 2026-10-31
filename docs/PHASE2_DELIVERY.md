# FailureLab X Phase 2 delivery

Phase 1 was preserved, committed and pushed before frontend implementation. Its verified commit is `1545873bf87207a45fa25bde00305ca2e01612f2`. The repository is https://github.com/bhuvzzs24-spec/failurelab-x and the branch is `main`. The Phase 2 commit is the commit introducing this report; the final remote-verified hash is recorded in the delivery response and ignored local output report.

## Implemented

A strict TypeScript Next.js App Router frontend with a premium dark application shell, collapsible/mobile navigation, global project selection, connection indicators, command palette, shared cards, loading/empty/error states, Radix dialogs, confirmations and real mutation notifications.

| Workspace | Actual behavior |
|---|---|
| Command center | Whole-project SQL counts; UTC activity; recent executions/findings; registered graph preview; recorded timeline/fault/evidence summaries |
| System graph | React Flow/Dagre; actual directional registrations; filtering, drag/zoom/pan/fit; keyboard inspection; metadata drawer and investigation links; no inferred health |
| Experiment studio | Existing/new definitions, supported fault parameters, invariant selection, backend-aligned validation, confirmation, idempotent submission, polling, cancellation and filtered/paginated history |
| Failure investigator | Actual FAIL findings; expected/observed states; configuration/timeline; trace/log references; evidence and reproduction links; explicit inference/missing-data boundaries |
| Evidence explorer | Run/status/kind/finding/text filtering, artifact IDs/timestamps/hashes, escaped JSON and redacted allowed downloads |
| Failure replay | Original configuration, versions, schedule, inputs, instructions and nondeterminism; automatic replay accurately unavailable |
| AI investigator | Typed hypothesis/intervention structures and accurate Phase 3 empty state; no invented analysis |
| Minimal sequence | Actual original timeline plus typed reduction components/contracts; no invented reduction or replay statistics |
| Fix verification lab | Original execution context and typed comparison components; candidate repair/retest unavailable |
| Settings | Real project/service/dependency/invariant creation, registry details, connection readiness, backend capabilities and local contrast preference; no secret editing |

## Backend integration

All existing endpoints remain valid. Four authenticated additions require no migration:

- `GET /api/v1/capabilities`
- `GET /api/v1/projects/{project_id}/overview`
- `GET /api/v1/projects/{project_id}/runs`
- `GET /api/v1/projects/{project_id}/findings`

Generated types come from `docs/openapi.json`. The same-origin Next bridge keeps the backend credential server-side, constrains local origins and operations, rejects cross-origin mutations, and redacts sensitive display fields. Project-wide counts include the whole project, not only recent lists. No UI results or graphs are sourced from test fixtures.

## Start

```sh
cp .env.example .env
# Set the local credentials in .env.
docker compose up --build -d
docker compose exec api python scripts/seed.py --register-only
```

Visit http://localhost:3000. The frontend service is included in Compose and uses the same configured API token.

Without Docker, install Python dependencies and Redis, run `python scripts/dev_stack.py`, then use Node 24 LTS in `frontend/`, configure its ignored `.env.local`, run `npm ci` and `npm run dev`. See `frontend/README.md` for exact commands, ports and environment setup.

## Actual verification

- **31 backend tests passed**, including all preserved Phase 1 tests, project read-model scoping, capability safety and Git-index secret scanning.
- **39 frontend tests passed**: validation against real OpenAPI limits, API/error/pagination behavior, credential redaction and origin/host controls, loading/errors/counts, graph layout, immutable definition submission, cancellation, finding/evidence views and feature availability.
- **3 Playwright scenarios passed against a clean standalone production server** with real API, SQLite, demo services, Redis and Celery. No backend routes were mocked. The main scenario rendered the registered graph, inspected a node by keyboard, started a confirmed experiment, waited for the genuine backend result, opened the invariant finding and downloaded evidence. Additional scenarios tested narrow-screen navigation/command controls/accessibility and all ten workspaces.
- TypeScript including generated route types, ESLint and Prettier checks passed.
- A clean `npm ci` from the final lockfile and optimized standalone production build passed. No out-of-root tracing omissions remained in that build.
- Live npm audit: **0 runtime advisories**. **3 moderate development-only advisories remain** in the legacy minimatch/OpenAPI-generator chain. Modern lint consumers use a targeted patched override; the legacy generator was not given an incompatible major override. The generator reads the repository's first-party FastAPI spec, not arbitrary remote schemas.
- Raw JUnit, logs, browser traces and screenshots are retained locally under ignored output/test directories, never committed as sensitive evidence.

Initial checks exposed and fixed stale API types, optional contract fields, a Next internal-hostname mismatch in same-origin validation, and submission/cache handling. Browser development-cache failures were not counted as passes. The final browser results above are from the clean production build. The host's app-bundled Node rejected native compiler libraries, so checks used an ordinary temporary Node 24.22.2 runtime without weakening its protections. Temporary dependency/build mirrors avoided very slow package reads under Documents; final source was synchronized back to the repository and root-source type/lint/unit/format checks passed.

## Infrastructure not verified

Docker is not installed and a PostgreSQL runtime is unavailable on this host. Consequently Docker image builds, full Compose startup and PostgreSQL execution were not run in Phase 2. Local SQLite integration does not prove PostgreSQL behavior. Linux Celery prefork hard limits remain part of the Docker verification path. Compose configuration was parsed as YAML, which does not replace running `docker compose config` and the containers.

## Manual UI verification

1. Start the complete stack and register the demo with the commands above.
2. Open the frontend and select **FailureLab demo** in the project selector.
3. Open **System graph**; verify gateway/order/payment/inventory and registered directional edges. Drag/zoom/fit; focus a node and press Enter for details.
4. Open **Experiment studio**, select **Payment acknowledgement loss**, inspect the selected invariants and the after-response latency configuration.
5. Click **Review & run**, inspect the reset/target/TTL warning, then **Start sandbox experiment**.
6. Watch actual lifecycle states. Completion alone does not assert correctness. Open the resulting cross-service correctness finding.
7. Verify observed payment `charged`, order `pending`, inventory `reserved`, and the failed paid-implies-finalized constraint. Inspect timeline, trace identifiers and supporting snapshots.
8. Open **Evidence explorer**, select snapshot/evaluation kinds, inspect JSON and download an artifact or the redacted run record.
9. Open **Failure replay**; inspect versions/inputs/instructions. Confirm automatic replay is unavailable and a new scenario run is labeled separately.
10. Visit the three Phase 3 workspaces; confirm no fabricated results or enabled repair/minimization controls. Inspect settings, connection readiness and safety limits. Use a narrow viewport and Ctrl/Command+K navigation.

Stop after Phase 2. No AI planner, root-cause engine, minimizer or repair implementation was added.
