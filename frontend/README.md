# FailureLab X frontend — Phase 2

Next.js App Router, strict TypeScript, Tailwind v4, locally adapted shadcn/ui components (Radix + CVA), React Flow/Dagre, TanStack Query, Recharts, Lucide, React Hook Form and Zod. The Python backend and experiment engine are preserved.

## Start with Docker Compose

From the repository root:

```sh
cp .env.example .env
# Set local API/control credentials and database passwords.
docker compose up --build -d
docker compose exec api python scripts/seed.py --register-only
```

Visit http://localhost:3000. Only loopback API/frontend ports are published. The frontend receives `API_TOKEN` server-side. No browser token entry or CORS configuration is needed: the same-origin Next.js bridge forwards only allowlisted existing operations to the configured local API.

## Start without Docker

Python 3.12+, Redis server and Node 24 LTS are required. A local development stack uses real processes and SQLite, not fake endpoint results:

```sh
# Terminal 1, repository root:
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
python scripts/dev_stack.py

# Terminal 2, frontend/:
npm ci
cp .env.example .env.local
# Set API_TOKEN to match the backend (local-development-token if using the
# development launcher's default). BACKEND_URL=http://127.0.0.1:8000.
npm run dev
```

The launcher registers the demo without executing an experiment. It owns only the processes it starts, and stops them on Ctrl+C. Logs/state are ignored under `work/local-stack/`. It never touches an existing Redis on port 6379. Default Redis port is 16379; demo ports are 18080–18085. Local worker uses Celery solo for development; Linux prefork hard-limit behavior must be verified with Compose. Shutdown retains evidence/state. No automatic destructive volume reset occurs.

## Actual routes

- `/`: project-wide command center from persisted aggregate counts, recent runs/findings, real graph, UTC run activity and recorded fault events.
- `/graph`: registered directional topology with automatic layout, dragging, fit/zoom/pan, service filter, configured experiment-boundary highlight and metadata drawer. Registration does not imply healthy status or causality.
- `/experiments`: existing/new definitions, backend-aligned constraints, invariant selection, confirmation, durable submission, lifecycle polling, cancellation and paginated project history. Editing immutable definitions creates a new persisted definition.
- `/findings?run=...&finding=...`: rule, observed state, timestamp/references, fault config, timeline, trace IDs, missing raw-log limitations and reproduction links. Causal explanation is explicitly distinguished from observed facts.
- `/evidence?run=...&artifact=...`: run/status/kind/finding/text filters, metadata, safe escaped JSON, redacted artifact and run-record downloads. Hashes refer to the original backend payload; redacted downloads need not hash identically.
- `/replay?run=...`: configuration, recorded versions/schedule/inputs/instructions and nondeterminism. Automatic replay is unavailable; a new scenario run is labeled separately.
- `/ai`, `/minimization`, `/verification`: Phase 3 availability views and typed components/contracts. No synthetic hypotheses, confidence, patches or minimization statistics. Original recorded event sequences can be inspected.
- `/settings`: project/service/dependency/invariant registration, connection readiness, actual capability limits, registered versions and local contrast preference. No unsafe secret editing or unsupported delete/update operations.

Raw logs/full spans are not exposed by the backend. The UI displays actual correlation references and explicitly marks the missing material. Graph health and active fault state are not inferred from configuration or old artifacts. All metrics distinguish experiment execution completion from invariant correctness.

## Contracts and safety

`npm run generate:api` derives types from `../docs/openapi.json`. Backend additions are read-only project overview, paginated project runs/findings and capability metadata. Existing Phase 1 routes remain valid; no migration is required.

The bridge forwards no incoming Authorization/cookie headers, injects the server token, validates local backend origins, rejects unrecognized paths/methods/query parameters, requires same-origin JSON mutations, bounds request/response sizes, disables caching/redirects, and redacts credentials/local paths from JSON. A reachable local frontend represents the local operator; it is not a multi-tenant authentication boundary. Do not publish it to the internet without proper identity/access control.

## Checks

```sh
npm run generate:api
npm run typecheck
npm run lint
npm test
npm run build
# With real backend/demo/worker and frontend running:
npm run test:e2e
```

Component tests use explicitly isolated fixtures and mocked adapters; production code imports none of them. The real Playwright workflow does not mock backend routes: it loads the registered demo, renders its graph, runs a confirmed experiment, opens the actual violation and downloads evidence. Another test covers narrow-screen navigation, the keyboard/command dialog and accessibility. Test artifacts/traces/downloads are ignored by Git.

Use `PLAYWRIGHT_BROWSERS_PATH` for a local browser cache or install Chromium with `npx playwright install chromium`. Check the Phase 2 delivery report for the exact checks that actually executed on the implementation host. Docker/PostgreSQL checks are not implied by local SQLite tests.

The final release record is in `../docs/PHASE2_DELIVERY.md`; the security/data boundaries are in `../docs/PHASE2_DESIGN.md`. Route types are regenerated by `npm run typecheck`, and `next-env.d.ts` is an ignored generated file. The live runtime dependency audit was clean; the delivery report records the remaining development-only generator advisories.
