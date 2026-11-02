# FailureLab X

A controlled distributed-systems correctness lab with executable system invariants, a Next.js investigation interface, adaptive exploration, repeated counterexample reduction, causal interventions and constrained repair verification. Payments are test-only. Findings come from authoritative service state, never an LLM verdict.

The demonstration loses the acknowledgement of a committed payment: the charge exists while its order remains pending. Six additional seeded benchmark defect families exercise retries, finalization, stock drift, concurrency and compensation. These are synthetic known defects, not novel discoveries.

## Permanent HTTPS hosting and redesigned interface

The premium interface retains all existing engines and recorded evidence. [Design system](docs/DESIGN_SYSTEM.md) describes the redesigned workspaces. [Cloud setup](docs/CLOUD_SETUP.md) provides a separate Vercel/Render read-only deployment, private persistent data, strict viewer permissions and CI-gated releases. **No public URL has been deployed yet:** provider resource creation, costs, snapshot publication and release require owner approval. After an approved release, the permanent HTTPS hostname works without this Mac.

For the no-backend, no-Render alternative, see [protected frontend-only preview preparation](docs/FRONTEND_ONLY_PREVIEW.md). It serves real recorded evidence, exposes no execution controls, and requires approval before any protected preview or evidence upload.

## Start on a Mac

Install Docker Desktop (Engine + Compose v2), start its daemon, and have Python 3.12+ available as `python`:

```sh
make start
make status
# Open http://127.0.0.1:3000
make logs
make stop
```

`make start` creates a private `.env` if absent, preserves existing configuration, builds services, waits for host HTTP readiness and seeds the project without injecting faults. It prints a working URL only after host probes pass. Localhost works only while the required services are running. `make restart` preserves volumes. Never use the destructive reset script for retained evidence.

Docker is unavailable in the delivery environment. A separately verified native Mac/SQLite/Redis fallback and exact prerequisites are documented in [LOCAL_SETUP.md](LOCAL_SETUP.md); it does not validate Compose/PostgreSQL or execute generated patches on the host.

## Use the application

Select **FailureLab demo**, open Experiment studio, review the payment fault and confirm execution. Open its finding and authoritative evidence. Adaptive explorer, Minimal sequence, AI investigator, Patch review and Fix verification lab use persisted research jobs. Verification requires the separately enabled restricted Docker agent (`make verifier`); otherwise it records an infrastructure error, not success.

Read [USER_GUIDE.md](USER_GUIDE.md), [EXPERIMENT_GUIDE.md](EXPERIMENT_GUIDE.md) and [AI_ENGINE.md](AI_ENGINE.md). Local API docs: http://127.0.0.1:8000/docs. Every `/api/v1` request requires the server-side bearer token. Never put it in a `NEXT_PUBLIC_*` variable.

## Validate

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -c constraints.txt -e '.[test]'
cd frontend && npm ci && cd ..
make test
make test-integration    # Docker + disposable PostgreSQL test database
python scripts/acceptance.py --benchmark --budget 12
python scripts/browser_acceptance.py  # running native/Compose app + Google Chrome
```

Node 24+, Redis and Python 3.12+ are needed for native tests; generated-patch verification needs Docker and the fixed verifier image. Tests explicitly skip unavailable Docker. PostgreSQL migration validation requires a dedicated `TEST_POSTGRES_URL`; SQLite does not establish PostgreSQL compatibility. Full fault/patch tests belong only on isolated machines.

[ARCHITECTURE.md](ARCHITECTURE.md) describes components and API boundaries. [BENCHMARK_RESULTS.md](BENCHMARK_RESULTS.md) records actual measurements. [SECURITY.md](SECURITY.md), [DEPLOYMENT.md](DEPLOYMENT.md) and [LIMITATIONS.md](LIMITATIONS.md) define deployment gates. No public deployment or production-readiness claim is made. Earlier phase reports remain under `docs/`.

Linux CI separately passed actual PostgreSQL migrations, Redis checks and all four container builds; see [verified CI results](docs/PHASE4_CI_RESULTS.md). Mac Compose execution and generated-candidate verification remain pending an isolated Docker host.
