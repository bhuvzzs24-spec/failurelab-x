# FailureLab X — Phase 1

A runnable local failure experimentation backend with executable cross-service invariants. The demo uses fake payments only. No frontend, AI planner, scanning, shell execution API, or production targets.

The discovery scenario loses the acknowledgement of a committed payment. The coordinator times out and leaves an order pending; authoritative state proves the inconsistency even though all four services remain healthy.

## Launch

Requires Docker Engine with Compose v2. Python containers use Python 3.12. Only the platform API is published, on loopback.

```sh
cp .env.example .env
# Set the local tokens/passwords in .env before starting.
docker compose up --build -d
docker compose ps
docker compose exec api python scripts/seed.py
```

The seed command registers four services, dependencies, three executable invariants and a latency experiment. It submits a run, polls it and prints its evidence summary. Repeating it reuses the project and starts a new uniquely keyed run. Partial seed failures are reported explicitly.

Open API documentation at [localhost:8000/docs](http://localhost:8000/docs). Use `Authorization: Bearer <API_TOKEN>` for `/api/v1` requests. In Swagger's header parameter enter the full `Bearer ...` value. `/health`, `/ready` and OpenAPI documentation are public on loopback.

```sh
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl -H 'Authorization: Bearer change-local-api-token' http://localhost:8000/api/v1/projects
# Substitute the ID printed by seed.py:
curl -H 'Authorization: Bearer change-local-api-token' http://localhost:8000/api/v1/runs/RUN_ID/summary
```

## Architecture

- FastAPI/Pydantic v2 contracts and authenticated versioned APIs.
- SQLAlchemy 2 persistence; immutable initial Alembic migration; separate platform/demo PostgreSQL instances.
- Redis/Celery worker and scheduler; database outbox handles broker publication failures.
- Atomic database sandbox lease prevents concurrent resets/injections. Run IDs scope faults and evidence.
- Restricted fault proxy has a raw TCP data plane for real resets and an authenticated control plane. Fixed payment upstream, bounded request size, no generic forwarding.
- Demo gateway calls order, inventory, proxied payment, then order finalization. Payment uses a persistent job table and an independently pausable processing loop. Inventory decrements finite stock atomically and enforces idempotency.
- Authorized state adapters gather snapshots; pure deterministic rules evaluate comparisons, implications and endpoint transitions. The runner provides bounded consistency windows and evidence provenance.
- JSON request logs, OpenTelemetry spans, correlated execution IDs, hash-addressed JSON evidence stored in PostgreSQL.

See [technical design](docs/DESIGN.md), [API contracts](docs/API.md), [bug reproduction](docs/DEMO_BUG.md), [verification](docs/VERIFICATION.md), and [implementation plan](docs/IMPLEMENTATION_PLAN.md).

## Tests and development

Local Python 3.12+, Redis server binary (or an isolated `TEST_REDIS_URL`) are required for the complete non-Docker suite. Local tests run five real HTTP processes, a Redis process and real Celery workers using temporary SQLite databases. No Docker is required for that suite.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest -q
# Separate platform DB for local development:
mkdir -p work
export DATABASE_URL=sqlite:///./work/development.db
alembic upgrade head
alembic check
uvicorn app.main:app --reload
```

For Docker verification, including migrations on a dedicated PostgreSQL test database:

```sh
docker compose --profile test run --rm tests
# Existing volumes created before lab_test was provisioned need this once:
docker compose exec postgres psql -U lab -d lab -c 'CREATE DATABASE lab_test OWNER lab'
```

The migration test performs upgrade, metadata drift check, downgrade and re-upgrade. `TEST_POSTGRES_URL` must identify a **dedicated disposable database**. It must never point at platform data. The main API/runner tests use isolated SQLite; PostgreSQL-specific migration behavior is covered when the test URL is set.

The Redis integration test uses a unique queue and dedicated local Redis process by default. If no Redis binary or explicit test URL is available it reports a visible skip; it never substitutes an eager/mock broker.

## Lifecycle and recovery

`CREATED → QUEUED → RUNNING → VERIFYING → COMPLETED | FAILED | CANCELLED`. A COMPLETED experiment can have FAIL invariant outcomes: completion means the experiment executed, not that the target was correct. Missing observations produce INCONCLUSIVE and never a finding.

Every five seconds the scheduler dispatches durable CREATED records, republishes old QUEUED records and recovers expired nonterminal runs. Duplicate queue deliveries cannot claim an active run. A killed worker's run is failed after its deadline and cleanup is attempted. It is not automatically replayed because business effects may already exist. The proxy and payment pause leases expire independently within 30 seconds. Failed cleanup retains the sandbox lease through worker hard limit plus maximum fault TTL and margin (165 seconds from claim). The watchdog retains that lease even when cleanup succeeds because an unresponsive worker may still be alive. A cooperative owner releases it after stopping its work.

Cancel through `POST /api/v1/runs/{id}/cancel`. Running jobs poll cancellation/deadline every 100 ms between asynchronous operations. Queued cancellation is honored on claim; the scheduler also terminalizes overdue records. Force-killing a worker is covered by the real Redis/Celery integration test.

## Reset and shutdown

Each experiment resets the single managed demo under the sandbox lease. Demo data is disposable; evidence remains in the platform database. Do not use the demo for unrelated workloads during experiments.

```sh
docker compose down                       # keep persistent state/evidence
sh scripts/reset.sh                       # DELETE this Compose project's volumes and rebuild
```

## Boundaries

Phase 1 supports one configured demo sandbox and one payment boundary, not arbitrary application onboarding. All operator origins must be an expected Compose hostname or loopback HTTP origin; registration cannot contain a URL. No privileged containers, Docker socket or host process control are used. Application containers are nonroot, read-only and drop capabilities. PostgreSQL containers use development bootstrap accounts on an internal network; separate migration/runtime DB roles, TLS, tenant isolation and external secret management remain deployment work.

Replay is reproducible at the scenario level. A seed alone does not eliminate network/OS scheduling, database latency or image drift. Set `BUILD_VERSION` to a meaningful immutable image revision, archive container logs with the run's execution/trace IDs, and pin dependency/image digests before long-term research use. The bundled images are version tags rather than digest-pinned release artifacts.
