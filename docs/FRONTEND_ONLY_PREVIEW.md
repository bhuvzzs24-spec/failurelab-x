# FailureLab X: protected frontend-only preview proposal

**Preparation only. Do not deploy before the owner approves the exact preview and evidence upload. No production publication or paid resource is authorized.** Render billing is unnecessary for this option.

The starting main commit `c199a6d8e711a3fe5e5bdb1c8a22c3443e8c8a9a` passed all four [Safe CI jobs](https://github.com/bhuvzzs24-spec/failurelab-x/actions/runs/41483513879) before this work began. Later preparation commits must pass their own CI before a preview is approved.

## Runtime

Browser → protected Vercel Next.js preview → bundled recorded evidence file.

There is **no separate public API, FastAPI process, Render service, database, Redis, worker, fault proxy, repair agent or connection to the Mac**. The existing same-origin `/api/backend` GET routes are compatibility read models inside Next.js. In recorded mode they read a fixed bounded file; they cannot forward a request to any backend. Every mutation returns a refusal, including when evidence is missing. The original local and connected read-only modes remain available for their existing deployments.

The recorded dataset is created from actual terminal synthetic sandbox runs and research jobs. Original private state is unchanged. `scripts/prepare_frontend_demo.py` reconstructs the original API read responses in-process over a disposable SQLite import; it does not call any live service. It redacts credentials, local paths and network endpoints, recalculates evidence digests with redaction provenance, and writes private files with an integrity sidecar. No measurements are generated to make the demo look successful.

The captured dataset contains real historical graph/configuration, findings, state snapshots, causal interventions, reductions, candidate diffs, benchmark reports and verification outcomes. All pages identify it as recorded evidence. Counts refer to that dataset and capture time. No service health or current traffic is inferred. Discovery, cancellation, fault injection, registration, live replay, new interventions, patch preparation and verification execution are unavailable. Administrative and execution controls are hidden; their underlying requests remain blocked. Evidence export, filtering, graph inspection and historical navigation work.

If the file is missing, modified, too large, invalid or contains active job records, the demo returns an explicit unavailable state. It never falls back to localhost or another backend. Missing record IDs return 404 rather than fabricated evidence. `/api/health` reports `recorded_demo_ready` with `live_backend:false`; that is frontend dataset readiness, not backend health.

## Exact deployment profile

Use a **separate empty Vercel project**, provisioned only after approval:

| Setting | Required value |
| --- | --- |
| Account/workspace | Existing `bhuvzzs24-spec` account, subject to owner confirmation |
| Project | Proposed `failurelab-x-demo`; confirm availability, do not invent its URL |
| Framework | Next.js |
| Repository Root Directory | `frontend` |
| Include source outside Root Directory | Enabled for `docs/openapi.json` |
| Node version | 24.x |
| Target | **Preview only**, never production |
| Deployment Protection | **Vercel Authentication → All Deployments**, before the first upload/deployment |
| Git automatic deployment | Disabled (`git.deploymentEnabled:false`) |
| Custom domains | None |
| Build configuration | `frontend/vercel.demo.json`, selected explicitly with CLI `--local-config` |
| Build command | `node scripts/check-demo.mjs && npm run build` |
| Install command | `npm ci` |
| Function region | `fra1` |
| Runtime/build variables | Exactly the three non-secret values below |
| Backend/execution credentials | **Absent** |

```dotenv
DATA_MODE=recorded_demo
DEPLOYMENT_ENV=frontend_demo
ACCESS_MODE=read_only
```

Vercel supplies `VERCEL=1` and `VERCEL_ENV=preview`. The application rejects this profile if the platform environment is production. There is no `BACKEND_URL`, `HOSTED_BACKEND_ORIGIN`, API/control/role token, database/Redis URI, repair connection, model connection or provider account token in the application environment. The prebuild guard verifies the profile, file bound, checksum and removed internal addresses. `next.config.ts` traces the private file into the server function; it is not placed in `public/` or the browser JavaScript. Responses have no-store and noindex headers. These headers do not replace access protection.

The project-level Authentication setting cannot be securely expressed by pretending it is an application `vercel.json` field. It must be configured and verified on the actual Vercel project **before** deployment. Unauthenticated access must be tested externally after the approved preview exists. Do not disable protection, create shareable bypass links, promote the preview, assign a production domain, start a Pro trial or upgrade a plan under this approval.

## Evidence custody and approval

`frontend/demo-data/` is ignored by Git and excluded from ordinary Docker contexts. Actual private evidence is **not committed to the public GitHub repository**. The prepared evidence file and its SHA256 sidecar are local review material; its presence does not authorize uploading it. Before approval, review the UI, export metadata and representative logs/snapshots/source diffs. Automated redaction cannot guarantee that every organization-specific sensitive string has been identified.

An approved prebuilt upload necessarily gives Vercel the bundled redacted evidence. The owner must approve that dataset SHA, source scope and recipient account together with the protected preview. A clean Git checkout deliberately has no private dataset; the preview prebuild fails until an explicitly reviewed dataset is supplied. Tests use clearly named unit fixtures and never publish them as measured results.

Operator-only preparation (local/private; no cloud actions):

```sh
PYTHONPATH=backend python scripts/prepare_frontend_demo.py \
  --snapshot <private-reviewed-synthetic-snapshot.json> \
  --output frontend/demo-data/recorded.json --reviewed
cd frontend
DATA_MODE=recorded_demo DEPLOYMENT_ENV=frontend_demo ACCESS_MODE=read_only \
  node scripts/check-demo.mjs
DATA_MODE=recorded_demo DEPLOYMENT_ENV=frontend_demo ACCESS_MODE=read_only npm run build
```

After explicit preview approval, authenticate the Vercel CLI as the intended account without sharing tokens in chat. Link the separate project and configure the settings above. Run Vercel CLI from the repository root, not `frontend`, because this is a monorepo. Use reviewed CLI version `65.9.0`. Pull **Preview** environment settings, build using `--local-config frontend/vercel.demo.json`, verify the output/protection/project, then deploy with `--prebuilt --local-config frontend/vercel.demo.json` and **without `--prod`**. Only the approved build/evidence may be uploaded. No deployment command has been run during this preparation.

## Expected costs

| Item | This proposal |
| --- | --- |
| Render / PostgreSQL / Redis / workers | **$0: none created or needed** |
| Vercel Hobby | **$0/month** if this is eligible personal, non-commercial use and stays inside included limits |
| Commercial/team use | Hobby is not eligible; Pro currently starts at **$20/month plus applicable usage/seat costs** and requires a separate cost approval |
| Deployment Authentication | Available on all plans; use the included Vercel Authentication option |
| Domain / paid add-ons | **$0: none requested** |

The repository's product ambition does not establish eligibility for Hobby. Confirm the intended use before approving a free-plan preview. If a paid plan, seat, protection add-on or upgrade is required, stop and obtain separate authorization. Do not activate a trial that can convert to billing. Vercel Hobby caps usage rather than offering purchasable overages; exceeding limits may make a demo unavailable. This is not a paid availability/SLA commitment.

Current primary references: [Vercel pricing](https://vercel.com/pricing), [Hobby eligibility and limits](https://vercel.com/docs/plans/hobby), [Vercel Authentication](https://vercel.com/docs/deployment-protection/methods-to-protect-deployments/vercel-authentication), [monorepo CLI/root requirements](https://vercel.com/docs/monorepos), [prebuilt deployment](https://vercel.com/docs/cli/deploy).

## Permissions required after review

1. Approval to create/link the separate project in the named existing Vercel account; no plan upgrade or billing change.
2. Approval to enable Vercel Authentication for all that project's deployments and keep access limited to the owner/explicitly authorized project members. No public bypass links.
3. Approval to upload the exact reviewed redacted evidence bundle and Next.js build to Vercel as **one protected Preview**.
4. Scoped CLI/account authentication supplied through the provider's own login/credential mechanism. No GitHub write grant, Render permission, backend credentials or production target permission is needed for a manual prebuilt preview.

The existing GitHub push authorization covers committing the code/configuration, not uploading private evidence or creating a preview. No preview/production URL can be claimed until the owner approves, deployment succeeds and both authorized access and unauthenticated denial are verified externally.

## Verification

`python scripts/test_frontend_demo.py` serves the production build in two owned local instances with **outgoing server sockets disabled**. Chrome checks all 13 pages, actual graph/evidence, exports, hidden controls, rejected mutations, accessibility, mobile layout and a second instance with missing evidence. Browser requests are also checked for external origins. Unit tests verify pagination, missing IDs, tampering, active-record rejection and no fetch fallback. Existing backend/frontend regressions remain required. These local tests do not establish that Vercel Authentication or a live protected URL has been configured; that verification remains pending approved deployment.
