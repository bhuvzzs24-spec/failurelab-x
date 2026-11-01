# Phase 3: bounded evidence-driven research

Phase 1 and Phase 2 remain available. Research jobs are a separate additive layer
under `/api/v1/research`. They execute only the packaged four-service benchmark.
No request accepts a target URL, shell command, image, filesystem path, or arbitrary
repository code. This is an integrated experimental pipeline with a deliberately
bounded repair space, not general-purpose autonomous program repair.

## Launch

Python 3.12+, Node 24+, Docker Compose:

```sh
cp .env.example .env
# Set local API/CONTROL/database credentials in .env; do not commit it.
docker compose up --build -d
# Seed the four registered services and dependency graph.
docker compose exec worker python scripts/seed.py --register-only
```

Open http://127.0.0.1:3000. Backend OpenAPI is at http://127.0.0.1:8000/docs.
Compose adds `bench-order`, `bench-payment`, `bench-inventory`, and `bench-gateway`.
Each uses its own `bench_<role>` PostgreSQL schema in the test-only demo database.
It has no public port. The ordinary worker has no Docker socket. Migration 0002
adds research persistence without altering Phase 1 tables.

Without Docker, install the existing Python package and Redis, then:

```sh
python -m pip install -e '.[test]'
API_TOKEN=change-local-api-token CONTROL_TOKEN=change-local-control-token python scripts/dev_stack.py
# Separate terminal, using the same API_TOKEN:
cd frontend
npm ci
API_TOKEN=change-local-api-token BACKEND_URL=http://127.0.0.1:8000 npm run dev
```

The local launcher owns all processes, binds loopback, migrates a SQLite database,
starts real Redis/Celery, and seeds the demo. Ctrl-C stops its owned processes.
SQLite tests do not validate PostgreSQL-specific behavior or Linux prefork kills.

## Complete workflow

Use the project UUID returned by seed, or GET `/api/v1/projects`:

```sh
export API_TOKEN='your-local-api-token'
python scripts/research.py PIPELINE --project PROJECT_UUID --budget 40
# Individual steps:
python scripts/research.py SEARCH --project PROJECT_UUID --budget 12 --strategy adaptive
python scripts/research.py MINIMIZE --project PROJECT_UUID --trial TRIAL_UUID --budget 40
python scripts/research.py INVESTIGATE --project PROJECT_UUID --trial TRIAL_UUID --budget 20
python scripts/research.py REPAIR --project PROJECT_UUID --trial TRIAL_UUID
python scripts/research.py VERIFY --project PROJECT_UUID --candidate CANDIDATE_UUID
python scripts/research.py BENCHMARK --project PROJECT_UUID --budget 12
```

Search may legitimately find nothing in a small budget. All subsequent actions
require an original, measured violation from the same project. The pipeline
reports this condition rather than inventing a source failure. Verification
without the restricted agent persists `INFRASTRUCTURE_ERROR` and does not execute
the patch. This is a completed job with an unsuccessful verification outcome.

## Benchmark defects and real fixed behavior

| Defect | Actual failure mechanism | Reference recovery |
|---|---|---|
| payment_ack_loss | Charge commits; delayed response exceeds coordinator timeout; order remains pending | Retry the same payment business key and finalize |
| unsafe_retry | Lost acknowledgement triggers a new payment key and a second ledger charge | Reuse original business key |
| lost_finalization | Finalize returns 503 before commit after successful payment | Bounded finalize retry |
| inventory_drift | Reservation commits before lost acknowledgement; retry creates another reservation | Atomic unique business-key reservation |
| concurrent_retry | Check/await/write uses separate row keys, allowing concurrent charges | Atomic business-key uniqueness |
| failed_compensation | Finalize fails, order cancels, refund fails before execution | Bounded refund retry and reservation release |

`benchmarks/policies.py` selects the vulnerable or recovery algorithm in the real
HTTP services. No flag changes invariant results. The evaluator reads actual
ledger/reservation/order rows. Reference policies are shipped trusted code;
generated policy candidates execute only inside the verification container.

Actions are scoped to UUID transaction namespaces, have at most two entries,
and are bounded to 500ms delays and two deliveries. The injector writes receipts
before acting. After-phase faults commit state first. Before-phase faults affect
execution. `at_ms` is a minimum elapsed activation time, not a guarantee that a
boundary will be visited. An unvisited action yields `INJECTION_NOT_OBSERVED`.
`delay_ms` controls latency actions; timeout actions hold for a fixed 500ms and HTTP 503 has no delay. Receipts record `effective_delay_ms`, and minimization does not reduce unused delay fields.
In-flight requests drain for 550ms before the bounded observation window.
Cleanup deletes only that trial namespace; no global database reset is exposed.
An abrupt process loss may leave bounded test rows until maintenance/reset;
fault state cannot affect other namespaces.

## Algorithms and evidence

* Seeded random search, coverage-guided selection, and cost-normalized ridge
  linear UCB share the exact same finite candidate space and budgets. Features
  include defect family, fault kind/timing, concurrency, registered dependency
  degrees, and relevance to registered invariant paths. Historical measured
  outcomes initialize regular search; benchmark comparisons start fresh.
* Novel signatures produce reward 1; repeats produce 0. Utility/uncertainty is
  an acquisition heuristic, never a probability or causal confidence. Distinct
  defect families and invariant signatures are reported separately. The finite
  reference catalogue is explicit; there is no claim of arbitrary service discovery.
* Repeated-trial ddmin removes fault subsets, then reduces timing, amount,
  quantity and concurrency on a finite lattice. Only repeated exact-signature
  matches are accepted. Inconclusive trials cannot justify local minimality.
  A final single-deletion/parameter audit and fresh confirmations are required;
  exhausted budgets return `local_minimality_tested=false`. No global minimum claim.
* Six deterministic competing mechanisms are compared through paired introduced
  and removed interventions in fresh namespaces. Status is SUPPORTED, REFUTED,
  INCONCLUSIVE or UNTESTED. Joint removals can support a mechanism class; they do
  not uniquely identify a source-level cause. Assumptions and trial IDs accompany
  every result. Graph edges show competing explanations, not proven causal edges.
* Invariant truth uses the existing deterministic typed rule evaluator. Built-in
  benchmark postconditions check paid/finalized, finalized payment/stock agreement,
  and cancelled compensation/release. Registered project rules influence planning
  context only; they are not silently treated as benchmark business semantics.
* Missing adapters yield INCONCLUSIVE, unavailable prerequisites yield
  INFRASTRUCTURE_ERROR, undelivered actions yield INJECTION_NOT_OBSERVED. Stable
  failures across the consistency window establish APPLICATION_VIOLATION.

Research jobs have CREATED → QUEUED → RUNNING → COMPLETED/FAILED/CANCELLED states,
a 600-second deadline, idempotency keys, a global benchmark lease, fenced trial
publication, late-ack Celery delivery, and a durable database outbox. Worker loss
is recovered at deadline; partial evidence is retained. The 650-second lease
exceeds the 620-second worker hard limit and bounded request drain. Cancellation
stops between trials; it is not an instantaneous kill of remote HTTP work.

Tables: research_jobs, research_trials, research_findings (unique project/signature),
research_decisions, repair_candidates, research_artifacts. Artifacts carry canonical
SHA-256 and a 256-KiB payload cap. Trial records include authoritative snapshots,
expected conditions, fault receipts, workflow events, actual elapsed costs,
service/runtime/policy hashes, and a request correlation ID. Research does not
claim an exported OpenTelemetry trace for that correlation ID. Existing Phase 1
tracing is preserved. Seeds control selection, not OS/database/HTTP scheduling.

## Restricted repair and independent verification

A deterministic repair enables the relevant recovery policy in an isolated copy.
AST syntax and static validation permit only one literal `POLICIES` boolean map
with exactly six known keys. Imports, calls, executable statements, additional
paths, commands and arbitrary source edits are rejected. Candidate source hashes,
unified diff, static check results and workspace logical ID are persisted.
The application source is never edited by a repair job. Workspaces live beneath
operator-configured `REPAIR_WORKSPACE_ROOT`, not a request-provided directory.

Build and operate the optional agent on a Docker-capable **local test host**:

```sh
docker build -f infrastructure/Dockerfile.verifier -t failurelab-verifier:phase3 .
export REPAIR_AGENT_TOKEN='a-local-agent-secret'
python -m uvicorn app.repair.agent:app --host 127.0.0.1 --port 8110
# In the local worker environment BEFORE launching dev_stack.py:
export REPAIR_AGENT_URL=http://127.0.0.1:8110
# The same REPAIR_AGENT_TOKEN must reach the worker.
```

Compose workers cannot use host loopback for the agent. The default Compose setup
therefore leaves verification unconfigured. An operator must arrange an isolated
reachable local agent and allowlisted `repair-agent` hostname, or run the provided
local launcher and loopback agent. No Docker socket is mounted in API/worker.

The agent accepts only a bounded policy source, scenario and candidate UUID,
checks authentication, and runs a fixed image/entrypoint with no network,
read-only root, no capabilities, non-root UID, no inherited credentials,
CPU/memory/PID/tmpfs limits, 90-second host deadline, and independent 80-second
container alarm. Only an agent-owned input file is mounted read-only. A `finally`
block removes the owned container. The agent is a trusted operator component
with Docker access; it must remain loopback/private and must not be exposed publicly.

The container starts independent original and candidate four-process clusters.
It validates the literal patch again, uses a candidate-specific working directory
and PYTHONPATH, and compares six matched cases: original, repeated original,
no-fault regression, held-out inputs, held-out timing, and related concurrency.
It records every state/evaluation, versions, wall time and gateway CPU time.
Unexpected candidate violations fail verification. Missing injections/observations
are inconclusive. Missing Docker/image/agent is infrastructure error.
Passing these finite cases does not establish general correctness. General
repository repair, language-wide static analysis, unrestricted LLM code generation,
and production deployment are outside this bounded implementation.

Optional local-only Ollama (`OLLAMA_URL=http://127.0.0.1:11434`, `OLLAMA_MODEL`)
returns JSON-schema constrained hypothesis/policy suggestions. IDs must reference
provided evidence; unknown IDs and unsupported policies are rejected. Suggestions
cannot set experimental statuses, introduce code or determine invariant truth.
No model is required and no remote model service receives evidence by default.

## API additions and frontend

All are authenticated with the existing bearer token:

* GET `/api/v1/research/capabilities`
* GET/POST `/api/v1/research/projects/{project_id}/jobs`
* GET `/api/v1/research/jobs/{job_id}`; POST `.../cancel`
* GET `.../decisions`; GET `.../artifacts`
* GET `/api/v1/research/projects/{project_id}/trials`; GET `/trials/{trial_id}`
* GET `/api/v1/research/projects/{project_id}/findings`
* GET `/api/v1/research/projects/{project_id}/candidates`; GET `/candidates/{candidate_id}`

Collections use existing offset/limit pagination. OpenAPI and generated TypeScript
are checked in. The existing Phase 1 capabilities endpoint describes the legacy
engine; research capabilities are separate and explicit about scope.

Frontend: `/explorer`, `/ai`, `/minimization`, `/patches`, `/verification`,
`/benchmarks`. Controls create real jobs, require sandbox confirmation, poll
persisted status, support cancellation, export redacted records, and display
real planner histories, competing-hypothesis graphs, sequence comparisons,
source diffs, verification matrices, benchmark charts, and raw evidence. Empty,
loading, error and unavailable states never contain invented results.

Manual test: select FailureLab demo, open Adaptive explorer, select payment
ack loss, set budget 12+, start and confirm. Select a measured original violation
in Minimal sequence, AI investigator, then Patch review. Prepare a candidate,
open Fix verification lab, and run verification. Without an agent, expect the
explicit infrastructure report. Benchmarks runs all three strategies over the
same three seeds. Old experiment studio and its original discovery remain usable.

## Algorithm references

Implementation adapts [ddmin (Zeller/Hildebrandt)](https://www.st.cs.uni-saarland.de/publications/files/zeller-tse-2002.pdf)
and [linear UCB](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/p661.pdf),
with explicit novelty reward and observed-cost normalization, without inheriting
their theoretical guarantees for this nonstationary novelty objective. Optional
model output follows [Ollama structured outputs](https://registry.ollama.com/blog/structured-outputs).
