Repository copy: local workspace path redacted; raw test evidence stays in ignored outputs/.

# FailureLab X Phase 1 delivery

Implemented in `<local-workspace>`. All source files are new because the workspace was empty. No frontend or AI planner was built.

## Architecture implemented

FastAPI/Pydantic v2 authenticated API contracts; SQLAlchemy persistence and explicit Alembic migration; Redis/Celery database-outbox dispatch; atomic sandbox exclusion; bounded execution/cancellation/recovery; expiring raw TCP fault proxy; four independent demo service processes; persistent fake payment job processing and finite inventory; deterministic declarative rules and authorized observation adapters; findings and canonical-hash JSON evidence; JSON logs and OpenTelemetry span correlation. Docker Compose defines 13 services including the test profile.

One shared Docker image runs separate gateway, order, payment and inventory processes. The demo tables reside in a separate PostgreSQL instance from the platform tables. Application containers are nonroot/read-only, have no Docker socket, and drop capabilities. Proxy/demo services receive only their relevant credentials.

## Launch and discover

```sh
cp .env.example .env
# Set the local credentials in .env.
docker compose up --build -d
docker compose exec api python scripts/seed.py
```

The script registers the graph, three invariants and the experiment, enqueues a run, polls it, and prints its summary. Repeated seed invocations reuse registration and create new runs. Inspect `http://localhost:8000/docs`. Versioned routes require `Authorization: Bearer <API_TOKEN>`.

For a clean Python environment, install `.[test]` and run `pytest -q`. The README has local database migration and API startup commands. Docker verification commands are in `docs/VERIFICATION.md` in the source archive.

## Actual discovered failure

Run `a80c643c-f8e3-4087-a059-11f89f0a2f30` completed in the local real-HTTP integration test and persisted 1 genuine finding with 18 artifacts. Observed states:

```json
{
  "order": {
    "status": "pending",
    "amount": 100,
    "quantity": 1
  },
  "payment": {
    "status": "charged",
    "amount": 100,
    "quantity": 1
  },
  "inventory": {
    "status": "reserved",
    "amount": 100,
    "quantity": 1
  }
}
```

The payment commits before the proxy delays its acknowledgement; gateway times out after 0.5 s and leaves the order pending. The adapter observes payment charged, order pending and inventory reserved through the consistency window. This violates the paid-implies-finalized invariant. Separate tests verify a healthy workflow and a workflow that converges during the window produce no finding. Missing observations produce INCONCLUSIVE, never a finding.

`sample-failure-evidence.json` contains the actual persisted run, finding and artifacts exported from this test. Its test build identifiers describe local processes, not Docker image digests. No live Docker run is implied by this evidence.

## Actual verification

- Python 3.13.15 on the local host.
- Final pytest result: 27 tests, 0 failures, 0 errors, 0 skips; JUnit suite time 15.278 s.
- Exact output: `test-output.txt`; machine-readable results: `test-results.xml`.
- API validation/persistence/graph, rules and three-valued outcomes, strict type handling, all six real TCP fault modes/restoration/TTL/scope, real business inconsistency, no false finding for healthy/converging systems, missing observations, failed baseline, cancellation/deadline, exclusion/duplicate delivery, evidence hashes/size, concurrent finite inventory, real Redis dispatch and actual Celery worker SIGKILL/restart recovery are covered.
- SQLite migration upgrade/downgrade/re-upgrade and Alembic drift check passed. PostgreSQL SQL was generated offline. Python compilation passed. Compose YAML parsed with 13 services. An offline local Python wheel build succeeded.
- Additional API check with a custom API token: 3 tests passed.
- One repeat was interrupted during import collection before running any tests; output is retained as `interrupted-collection.txt`. Another run had 26 passes and one Celery test startup timeout during slow installed-package reads; its output/XML are retained as `import-stall-test-output.txt` and `import-stall-test-results.xml`. The test now waits for genuine worker readiness before creating its bounded experiment. The final successful run used a fresh temporary runtime outside Documents, explicitly loading pytest-asyncio. No test is disabled.

Final command:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 FAILURELAB_EVIDENCE_PATH=outputs/sample-failure-evidence.json \
  /private/tmp/failurelab-clean-runtime/bin/python -m pytest -p pytest_asyncio.plugin -o faulthandler_timeout=30 \
  -q --junitxml=outputs/test-results.xml
```

## Precise blockers and known limitations

`docker --version` returned command not found; `postgres` was not in PATH. Docker builds, Compose startup, PostgreSQL connection/migration execution, Linux Celery-prefork hard limits and exact Python 3.12 container execution could not be verified here. The runnable commands to check them are supplied. SQLite tests and offline SQL generation do not establish PostgreSQL runtime correctness.

One local managed sandbox, one payment fault boundary, one SKU; no arbitrary application onboarding, tenant RBAC, production targeting, automatic trace-to-graph inference or repair. Transition checks compare observed endpoints and do not prove unobserved intermediate transitions. Eventual verification samples a bounded window rather than observing continuous state.

Crash safety uses target-side fault TTL and a conservative 165-second sandbox hold (130-second Celery hard limit + 30-second maximum TTL + 5-second margin). Watchdog cleanup alone does not release a potentially live stale owner's lease. The production worker must use prefork; queued runs can expire while the sandbox is retained and should be resubmitted afterward.

Raw logs/full spans stay in stdout; references persist in evidence, with commands supplied for archival. Build identifiers are operator-supplied; images and dependencies are version-constrained rather than digest/lock pinned. Network/OS/database timing and image drift remain sources of nondeterminism. Seeds do not imply exact replay. Development PostgreSQL bootstrap users remain broad-privilege accounts; runtime/migration role separation, TLS, external secrets and evidence retention policy remain deployment work.

## Ready for Phase 2

Typed graph, project/service, invariant, fault config, experiment/run/status, finding, timeline, artifact and summary schemas are implemented and exported in `docs/openapi.json`. Phase 2 can build against those contracts. Adapter, rule, fault and orchestration boundaries provide explicit extension points. No future AI component is simulated.

## Actual API endpoints

- `POST /api/v1/projects`
- `GET /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `POST /api/v1/projects/{project_id}/services`
- `GET /api/v1/projects/{project_id}/services`
- `POST /api/v1/projects/{project_id}/dependencies`
- `GET /api/v1/projects/{project_id}/graph`
- `POST /api/v1/projects/{project_id}/invariants`
- `GET /api/v1/projects/{project_id}/invariants`
- `POST /api/v1/projects/{project_id}/experiments`
- `GET /api/v1/projects/{project_id}/experiments`
- `GET /api/v1/experiments/{experiment_id}`
- `POST /api/v1/experiments/{experiment_id}/runs`
- `GET /api/v1/experiments/{experiment_id}/runs`
- `GET /api/v1/runs/{run_id}`
- `POST /api/v1/runs/{run_id}/cancel`
- `GET /api/v1/runs/{run_id}/artifacts`
- `GET /api/v1/artifacts/{artifact_id}`
- `GET /api/v1/runs/{run_id}/findings`
- `GET /api/v1/runs/{run_id}/timeline`
- `GET /api/v1/runs/{run_id}/summary`
- `GET /health`
- `GET /ready`

Errors are structured; pagination is offset/limit with bounded page size. Runs filter by status and artifacts by kind. Health/readiness and OpenAPI routes are public on loopback; all versioned routes authenticate. The docs contain exact payload examples.

## Files created

- `.dockerignore`
- `.env.example`
- `.gitignore`
- `Dockerfile`
- `Makefile`
- `README.md`
- `alembic.ini`
- `backend/app/__init__.py`
- `backend/app/api/__init__.py`
- `backend/app/api/routes.py`
- `backend/app/core/__init__.py`
- `backend/app/core/config.py`
- `backend/app/core/db.py`
- `backend/app/core/limits.py`
- `backend/app/experiments/__init__.py`
- `backend/app/experiments/runner.py`
- `backend/app/faults/__init__.py`
- `backend/app/faults/proxy.py`
- `backend/app/invariants/__init__.py`
- `backend/app/invariants/engine.py`
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/app/models/entities.py`
- `backend/app/repositories/__init__.py`
- `backend/app/repositories/evidence.py`
- `backend/app/schemas/__init__.py`
- `backend/app/schemas/contracts.py`
- `backend/app/services/__init__.py`
- `backend/app/services/demo.py`
- `backend/app/telemetry/__init__.py`
- `backend/app/telemetry/logging.py`
- `backend/app/verification/__init__.py`
- `backend/app/verification/observer.py`
- `backend/app/workers/__init__.py`
- `backend/app/workers/tasks.py`
- `backend/tests/conftest.py`
- `backend/tests/test_api.py`
- `backend/tests/test_celery_integration.py`
- `backend/tests/test_experiments.py`
- `backend/tests/test_invariants.py`
- `backend/tests/test_migrations.py`
- `backend/tests/test_proxy_demo.py`
- `compose.yaml`
- `demo-system/README.md`
- `demo-system/init.sql`
- `docs/API.md`
- `docs/DEMO_BUG.md`
- `docs/DESIGN.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/VERIFICATION.md`
- `docs/openapi.json`
- `infrastructure/migrations/env.py`
- `infrastructure/migrations/script.py.mako`
- `infrastructure/migrations/versions/0001_initial.py`
- `infrastructure/postgres-init.sql`
- `pyproject.toml`
- `scripts/reset.sh`
- `scripts/seed.py`
