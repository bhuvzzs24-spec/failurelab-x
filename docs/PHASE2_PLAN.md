# Phase 2 implementation plan

1. Preserve Phase 1 in an independently scanned commit, compare remote history, push and verify.
2. Build a strict TypeScript Next.js App Router application with generated OpenAPI types, a token-protecting same-origin server bridge, and TanStack Query.
3. Add only project-wide read aggregation endpoints needed for efficient, complete dashboard/history views, with backend tests. Keep existing routes/contracts intact.
4. Implement the dark application shell and ten workspaces: command center, registered dependency graph, experiment studio, investigator, evidence, replay, AI availability, minimization availability, verification availability, and settings.
5. Implement real project/service registration, experiment definition configuration, confirmed run submission, polling and cancellation. Render backend facts and evidence; never invent health, active faults, traces or future analysis.
6. Integrate Compose and server-only environment configuration. Preserve local sandbox boundaries.
7. Run backend regression tests; lint, strict TypeScript, component tests, production build and real Playwright workflow where available. Record infrastructure limits explicitly.
8. Scan staged Phase 2 changes, commit, fetch, push without force, and verify commit IDs against the remote.

Phase 3 workspaces contain typed contracts and accurate unavailable states only. Replay displays recorded instructions; a fresh scenario run is labeled separately from exact replay.
