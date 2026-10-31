# Phase 2 frontend architecture

## Boundaries

The Phase 1 engine, persistence models, migrations, demo behavior, invariant semantics and existing routes remain intact. Additions are a Next.js application, a local development launcher, four authenticated read-model endpoints, and a configurable proxy bind address for loopback development. No migration is required.

`frontend/src/app` supplies App Router layout, ten dynamic workspace paths and the same-origin bridge route. `components` contains focused workspaces and shared data/graph/evidence views; `components/ui` contains locally adapted shadcn/ui primitives built on Radix/CVA. `hooks/data.ts` owns query keys and polling. `lib/api.ts` owns typed endpoint calls; `types/api.generated.ts` is generated from the actual FastAPI specification. `types/future.ts` defines future contracts without an analysis implementation.

Dependencies are pinned with a lockfile. Node 24 LTS is required. Next.js 16.4.3, React 19.3.1, TypeScript 5.9.3, Tailwind v4, React Flow, TanStack Query, Recharts, Lucide, React Hook Form, Zod, Vitest and Playwright are used. TypeScript 5.9 remains compatible with the OpenAPI generator's supported peer range. ESLint 10 uses current Next/TypeScript/React Hooks plugins directly, avoiding incompatible legacy plugins from the bundled preset.

## Data and mutations

The browser holds no API credential. TanStack Query calls `/api/backend/...`; that allowlisted server route injects the server's `API_TOKEN` and forwards to the operator-configured loopback/Compose API origin. The bridge permits only known methods, paths and query parameters, enforces validated local Host and same-origin JSON mutations, bounds bodies/responses, rejects redirects and disables caching. Comparing Origin with the validated original Host avoids Next's internal hostname normalization while preventing DNS-rebinding hosts. Backend URLs, secrets and arbitrary destinations are not browser inputs.

Project selection scopes query keys. Complete registration collections are paginated to completion with an incomplete-page guard. Run/finding history is paginated and status-filtered. Dashboard aggregates come from SQL across the entire selected project, rather than a truncated recent page. UTC activity is computed from persisted run creation timestamps. Recent timelines and fault activity are recorded evidence, not inferred current faults.

Project/definition mutation responses update their caches only after persistence succeeds. Immutable experiment changes create a new backend definition; runs use backend idempotency keys. Failed submissions retain a visible error and retry key. Definition creation and run submission are two persistent operations: if the second fails, the created definition remains real and is reused for retry. The UI does not pretend those operations are atomic.

Runs poll every 1.5 seconds until a terminal backend status. Cancellation is a durable request, never an immediate assertion of rollback. COMPLETED describes execution completion; FAIL/PASS/INCONCLUSIVE describe system correctness. Backend errors and missing evidence remain explicit states.

## Graph and investigation

React Flow nodes/edges come only from registered graph JSON. Dagre positions them automatically; dragging is browser view state, not a change to the backend dependency model. Filters, zoom, fit, service drawers and keyboard inspection work. Experiment highlighting identifies a configured payment boundary, not a proven causal path. Registration is never presented as healthy service telemetry.

The investigator displays persisted invariant rules, authoritative state, evidence IDs, workflow outcomes, trace identifiers, fault schedule and reproduction metadata. Observed facts, inferred explanation boundaries and missing evidence are labeled separately. Raw logs/full spans are unavailable in Phase 1; recorded references are shown without fabricated records.

Evidence is React-escaped JSON. The server redacts recognized credential fields, common token formats, password-bearing connection strings and local paths before display/download. Downloads are serialized allowed API data, not filesystem access. Original backend hashes identify the original payload; a redacted export is explicitly not claimed to have the same hash. This redaction is defense in depth, not a general-purpose DLP system.

Automatic replay is unavailable. A new scenario run is explicitly distinguished from replay of an original execution. AI, minimization and repair views contain typed components, real original records where available and honest unavailable states. No hypotheses, confidence scores, patches or reproduction statistics are invented.

## Deployment and limits

Compose adds a nonroot, read-only Node 24 standalone frontend on loopback port 3000. It receives only the API token and local backend origin. No CORS relaxation is needed. The API remains on loopback port 8000; the controlled demo/proxy stay on the internal network.

The frontend is a local single-operator interface. The bridge is not multi-tenant identity/RBAC. Public hosting requires a separate authenticated deployment design. Safety settings and secrets are read-only/unavailable in the UI. Existing backend registration is create-only; no fake delete/update controls are added.

The development launcher starts owned real API/demo/Redis/Celery processes with SQLite and seeds through public APIs. It uses a separate Redis port and retains local evidence. Local solo worker mode does not verify Linux prefork hard-time-limit behavior. Docker/PostgreSQL verification remains required on a Docker host.
