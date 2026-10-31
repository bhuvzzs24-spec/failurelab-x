# Phase 1 API contract

Authoritative machine-readable contract: `/openapi.json`; a generated snapshot is in `docs/openapi.json`. Pydantic response schemas are the Phase 2 contract source. Extra input fields are rejected. IDs are opaque strings, timestamps are Unix UTC seconds. Pagination uses `offset` (≥0), `limit` (1–100, default 50), with `items`, `total`, `offset`, `limit`. Collection item types appear explicitly in OpenAPI.

All paths below are prefixed `/api/v1` and require `Authorization: Bearer <API_TOKEN>`.

| Method | Path | Response / behavior |
|---|---|---|
| POST, GET | `/projects` | Persist project / paginated ProjectOut |
| GET | `/projects/{project_id}` | ProjectOut |
| POST, GET | `/projects/{project_id}/services` | Register allowlisted identity / paginated ServiceOut |
| POST | `/projects/{project_id}/dependencies` | Persist project-scoped DependencyOut |
| GET | `/projects/{project_id}/graph` | Graph: typed nodes, directed edges, explicit provenance |
| POST, GET | `/projects/{project_id}/invariants` | Validate rule AST / paginated InvariantOut |
| POST, GET | `/projects/{project_id}/experiments` | Validate registered prerequisites/config / paginated ExperimentOut |
| GET | `/experiments/{experiment_id}` | ExperimentOut |
| POST | `/experiments/{experiment_id}/runs` | Durable RunOut, 202; idempotency key deduplicates |
| GET | `/experiments/{experiment_id}/runs` | Paginated RunOut, optional exact `status` filter |
| GET | `/runs/{run_id}` | RunOut lifecycle, config snapshot and result |
| POST | `/runs/{run_id}/cancel` | Durable cancellation request; 409 if terminal |
| GET | `/runs/{run_id}/artifacts` | Paginated ArtifactOut; optional `kind` filter |
| GET | `/artifacts/{artifact_id}` | ArtifactOut with payload and canonical JSON SHA-256 |
| GET | `/runs/{run_id}/findings` | Paginated FindingOut |
| GET | `/runs/{run_id}/timeline` | Timeline with chronological evidence events |
| GET | `/runs/{run_id}/summary` | RunSummary with run, findings and all artifacts |

Unversioned: GET `/health` (process liveness), GET `/ready` (migrated database and Redis connection), GET `/docs`, GET `/redoc`, GET `/openapi.json`. Readiness does not certify worker availability or target correctness.

Errors use `{"error":{"code":"validation_error","message":"..."}}`. Validation 422, missing resource 404, authorization 401, conflict 409, excessive body 413, unready 503. Unexpected exceptions use an opaque structured 500. Maximum public request body is 64 KiB; evidence payload is capped at 256 KiB per artifact. No file path input or artifact filesystem writes are exposed.

## Core examples

```json
{"name":"Charged implies finalized","rule":{"kind":"implies","antecedent":{"kind":"compare","left":{"path":"payment.status"},"op":"eq","right":{"value":"charged"}},"consequent":{"kind":"compare","left":{"path":"order.status"},"op":"eq","right":{"value":"finalized"}}}}
```

```json
{"name":"Lost payment acknowledgement","config":{"fault":{"target":"payment","kind":"latency","phase":"after","delay_seconds":1.5,"duration_seconds":10},"invariant_ids":["INVARIANT_ID"],"seed":42,"max_duration_seconds":45,"consistency_seconds":2,"retry_seconds":0.2,"amount":100,"quantity":1}}
```

```sh
curl -X POST -H 'Authorization: Bearer TOKEN' -H 'Content-Type: application/json' \
  -d '{"idempotency_key":"reproduction_001"}' \
  http://localhost:8000/api/v1/experiments/EXPERIMENT_ID/runs
```

Run schemas separate lifecycle status from invariant status. Evaluation contains `status` PASS/FAIL/INCONCLUSIVE, `observed`, `expected`, `evidence_refs`, `evaluated_at`, nullable `reason`. FindingOut points at the invariant and full evaluation evidence. Fault configurations live in immutable experiment configuration and run snapshots rather than a separately editable catalog. The static `Fault` schema in OpenAPI defines the supported catalog.

Graph service nodes expose HTTP method/path operations and shared resource labels; edges expose `http`, `shared_resource`, or `workflow` kind and workflow label. A graph asserts only explicit registration. Future span import must add source/provenance and confidence without treating a trace edge as proof of complete dependencies.
