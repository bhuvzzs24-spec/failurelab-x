# Verified Linux CI supplement

The [Safe CI run](https://github.com/bhuvzzs24-spec/failurelab-x/actions/runs/41306738900) for runtime/build revision `bd7677311d5985f5c441d5b8ef895d493827851c` completed successfully on 2026-11-01. All four jobs passed:

* Backend on Ubuntu/Python 3.12 with PostgreSQL 16 and Redis 7: 29 safe module tests and 9 selected research unit tests passed, including actual PostgreSQL upgrade/check/downgrade/re-upgrade and shared Redis rate limits. These are a subset of the 74-test Mac full suite; no fault workload ran on the shared runner.
* Frontend on Node 24: npm ci, lint, TypeScript, 57 component tests, production build and high/critical dependency gate passed. Three moderate development-tool advisories remain documented.
* Python tested-closure dependency audit passed.
* Compose configuration validation and API, verifier, trusted agent and frontend Docker image builds passed. Images were built only, never used to run faults/candidates on shared infrastructure.

The initial delivery run failed its frontend image build because a frontend-only context omitted the shared docs/openapi.json imported by contract tests. The root-context fix preserves tests/type checking and excludes local evidence/credentials. No test was disabled.

Mac Docker Desktop startup/published ports, complete Compose sandbox runtime, Linux prefork fault execution and original/generated-candidate container verification remain unverified. The local complete candidate attempt correctly records INFRASTRUCTURE_ERROR. Container build success does not establish isolation behavior or a verified repair.

No public deployment occurred. The separate approved isolated-runner workflow still requires operator-owned infrastructure and required reviewers. Native Mac localhost and real Chrome checks are documented independently in BENCHMARK_RESULTS.md.
