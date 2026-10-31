# Phase 1 implementation plan
1. Establish typed contracts, persistent SQLAlchemy entities and explicit Alembic migration.
2. Add project-scoped registration, graph, experiment, history and evidence APIs.
3. Implement safe declarative observations/rules with three-valued evaluation and bounded polling.
4. Implement authenticated allowlisted HTTP proxy with expiring fault leases and worker control.
5. Build PostgreSQL-backed demo services with idempotent state writes and a documented coordinator timeout bug.
6. Orchestrate baseline and faulted workflows using Celery, DB leases, cancellation, watchdog recovery and evidence.
7. Exercise migration, API, proxy, invariant and real HTTP workflow tests; document unavailable infrastructure checks.

Safety boundary: fixed local service origins come from operator environment, never user-provided URLs. A single sandbox is serialized using a database lease. Faults expire independently of the experiment worker. No Docker socket or shell API.
