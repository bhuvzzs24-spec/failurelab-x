# Verification and remaining infrastructure checks

The final execution summary, exact pytest output, JUnit XML and a real failure evidence package are delivered in `outputs/`. The implementation report records actual counts and timings. Results are not seeded into the API/database.

## Executed locally

- SQLAlchemy/Alembic upgrade against SQLite, metadata drift check, downgrade and re-upgrade.
- API authentication, validation, conflict behavior, pagination, persistent registration, graph and run contracts.
- Rule PASS/FAIL/INCONCLUSIVE, equality, implication, endpoint transitions and strict type handling.
- Real TCP proxy latency, timeout, 503, reset, unavailability and payment worker pause; restoration, TTL expiry, execution scope, authentication and restricted routes.
- Real HTTP commerce workflow with database persistence; genuine charge/order mismatch and persisted finding, healthy control without findings, convergence within the consistency window without a finding, and missing authoritative observations without a finding.
- Active and queued cancellation, deadlines, sandbox exclusion, duplicate delivery, stale-worker recovery and evidence hashes/size cap.
- Isolated Redis transport and Celery worker processes, durable dispatch, an actual worker process SIGKILL and recovery by a replacement worker.
- Real inventory capacity under concurrent reservations and idempotent retries.
- OpenAPI export, Python compilation, YAML parsing of all 13 Compose services, PostgreSQL migration SQL generation in offline mode, and a successful offline Python wheel build.

The host runs Python 3.13.15. The provided image targets Python 3.12; tests on that exact runtime remain part of the Docker check. Local integration tests use SQLite; they do not prove PostgreSQL runtime semantics.

## Exact blocker

`docker --version` returned command not found. `postgres` was absent from PATH. Therefore no Docker image build, `docker compose up`, PostgreSQL connection/migration execution, Linux-prefork hard time limit, or full container health/dependency sequence was verified on this host. YAML parsing and generated PostgreSQL SQL are not substituted for those checks.

Initial sandboxed dependency downloads failed DNS resolution, and loopback socket binding was denied. Approved runs installed dependencies and allowed the local HTTP/Redis/Celery tests. No dependency or test was silently replaced with a mock. One final repeat was interrupted during import collection before tests ran; its output is retained. A subsequent run had 26 passes and one Celery startup timeout while installed package reads stalled. The test now waits for genuine worker readiness before creating its bounded run. A fresh temporary runtime outside Documents completed the final suite with all 27 tests passing. The final command loads only the project's required pytest plugin. Both unsuccessful attempts remain recorded in outputs; no failing test was disabled.

## Verify on a Docker host

```sh
cp .env.example .env
# Set local credentials in .env.
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
docker compose --profile test run --rm tests
docker compose exec api python scripts/seed.py
mkdir -p work
docker compose logs --no-color api worker scheduler gateway order payment inventory fault-proxy > work/compose.log
```

The PostgreSQL migration test uses the dedicated disposable `lab_test` database provisioned on first PostgreSQL initialization. To test another PostgreSQL instance set `TEST_POSTGRES_URL` to a disposable database owned by the test user. The migration test downgrades that database; do not point it at platform or research evidence data.

For a clean local Python environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest -q
```

For a shared environment with unrelated pytest plugins:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -p pytest_asyncio.plugin -q
```

The Celery integration test requires `redis-server` or `TEST_REDIS_URL`. A missing Redis runtime is a visible skip, not a fake/eager execution path. The supplied Compose tests set a separate Redis test database and unique task queue.

## Known limits

One sandbox and fixed payment boundary; one SKU; safe declarative rules with endpoint transitions and sampled bounded verification. No automatic integration discovery, OTel graph import, tenant RBAC, production execution, repair engine, frontend or AI planner. Raw logs/spans stay in stdout and require external archival; their correlation references persist with runs. Images/dependencies are not digest/lock pinned. Crash holds can delay subsequent runs for up to 165 seconds; production execution relies on Celery prefork hard limits. Exact deterministic replay is not claimed.

Final result: **27 tests, 0 failures, 0 errors, 0 skips**; JUnit time 15.278 seconds.
