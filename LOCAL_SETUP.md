# Local setup and recovery

## Docker Desktop path

From the repository root, with Python 3.12+ as `python` and Docker Desktop running:

```sh
make start
make status
make logs       # Ctrl-C stops log following only
make restart
make stop
```

Frontend: http://127.0.0.1:3000. API: http://127.0.0.1:8000. Docs: http://127.0.0.1:8000/docs. `/health` is process liveness; `/ready` requires Redis and schema revision 0003. The launcher checks both host API readiness and frontend bridge readiness, then registers the demo. Services use container DNS (`api`, `postgres`, etc.); browser requests stay same-origin through Next. No browser-side container hostname is required. The frontend binds 0.0.0.0 inside Docker, while published host ports bind 127.0.0.1.

An existing `.env` is never replaced. A missing file is created mode 0600 with independent random local secrets. Set explicit credentials when copying `.env.example` manually. Do not publish API/control/database tokens. Health checks and successful migration gate startup; restart policies restore long-lived containers; `down` preserves named database/Redis volumes. Compose project name defaults to `failurelab-x`: if an older launch used another name, set `COMPOSE_PROJECT_NAME` to that original name before starting to reuse its volumes. Never delete volumes to resolve an unexplained missing-project problem.

## Native Mac fallback (no Docker)

Install Node 24+, Python 3.12+ and Redis (for example through your existing package manager). Ensure normal Node and `redis-server` are on PATH. Create a venv and install tested constraints:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -c constraints.txt -e '.[test]'
cd frontend
npm ci
npm run build
cd ..
make local-start
make local-status
make local-stop
```

The owned supervisor starts actual API, demo, benchmark HTTP services, Redis and Celery; migrates local SQLite; seeds the graph; starts the standalone Next build; and checks host readiness. It refuses occupied ports and never kills unrelated processes. Logs/database/evidence are under ignored `work/native-services/`. Stop waits for the owned supervisor to exit; a bounded shutdown timeout is an explicit failure. Check status before restarting. A PID plus unpredictable instance marker prevents stale ownership records stopping unrelated processes. `FRONTEND_BUILD_DIR` may point to an operator-built standalone frontend directory. No generated patch executes natively.

`make start` intentionally fails if Docker is missing; it does not silently substitute this fallback. SQLite/native results are separate from Docker/PostgreSQL validation.

## Optional restricted verifier

On an isolated Docker-capable local test machine, run `make verifier`, then `make start`. This builds the fixed image and configures an authenticated private agent with a host input directory and Docker socket access. Ordinary workers remain unprivileged. No agent port is published. Its health check verifies Docker/image availability. Review SECURITY.md before enabling it. Native workers may instead reach a loopback agent configured as described in `docs/PHASE3.md`.

## Troubleshooting

* Docker missing/daemon stopped: start Docker Desktop; no Compose host validation is possible without it.
* 3000/8000 occupied: inspect the owning application; do not kill unknown processes. Stop the owned stack using its matching launcher.
* Readiness 503: inspect API/migration/Redis logs. Apply migrations, never manually change `alembic_version`.
* 401/disabled controls: align server-side frontend API_TOKEN with local API_TOKEN (or the viewer role token in hosted read-only mode), then restart Next. Tokens are loaded at process startup.
* Verification INFRASTRUCTURE_ERROR: inspect private agent health and fixed image. This is not a patch pass.
* Reuse old PostgreSQL volume: the disposable `lab_test` database may need creation by its operator before migration tests. Never point TEST_POSTGRES_URL at application data.
* Localhost disappears after shutdown: expected; these are local running services, not hosted links.
