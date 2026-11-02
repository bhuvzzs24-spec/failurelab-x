# Permanent HTTPS hosting: reviewed read-only release

No public deployment has been created or authorized. Vercel integration is authenticated and returned no existing projects/teams; Render is not connected. The repository contains deployable configuration, not a claimed live URL. Your Mac is not part of the proposed production runtime.

## Architecture and safety boundary

One permanent Vercel production hostname serves Next.js and its same-origin `/api/backend` bridge. Server-side requests use a viewer credential to a persistent Render FastAPI service. Render PostgreSQL stores an explicitly reviewed copy of real synthetic demo histories, including bounded JSON evidence; dedicated private Key Value stores rate-limit counters. No worker, fault proxy, benchmark service, repair agent, Docker socket, production target or operator credential is included in `infrastructure/cloud/render.yaml`.

This is a **public read-only demonstration**. Visitors can inspect recorded experiments, causal interventions, repair diffs, verification outcomes, graphs and evidence. Starting/cancelling jobs, importing projects, injecting faults and executing patches are disabled in both frontend bridge and backend role policy. The backend also refuses startup unless its PostgreSQL role has SELECT-only privileges. Original private histories remain unchanged. Authentication uses existing service principals; this release does not claim to provide multi-user SSO or public authenticated execution. The private application retains its current viewer/operator/admin authorization, audit records and sandbox constraints.

Evidence remains in persistent PostgreSQL, with provider backups configured before publication. It does not depend on an ephemeral filesystem. Snapshot artifact digests are recomputed after redaction and retain source digests as provenance. Denied requests and HTTP responses appear in structured provider logs; the SELECT-only public database intentionally cannot append audit rows. Configure retention/log export in the provider account before relying on public logs for an audit retention requirement.

## Decisions requiring owner approval

1. Connect a Render account and approve publishing the reviewed demo and creating the three billable resources in the Blueprint. Reviewed base compute is approximately US$23/month (web $7, PostgreSQL $6, Key Value $10), plus storage, taxes and any private release-runner cost. Recheck the provider quote before approving. No service has been purchased.
2. Approve a Vercel project/plan and a permanent production hostname, or provide a domain you control. Custom-domain DNS changes require domain-owner authorization. The default provider HTTPS hostname is sufficient for one permanent URL; no domain purchase is necessary.
3. Approve exactly which synthetic evidence snapshot can be public. Inspect it for secrets, identifiers, logs, code and private paths; automated redaction does not replace this review.
4. Approve and provision an isolated ephemeral Linux release runner inside the database's private network. The Blueprint denies external database/Redis access. A shared GitHub runner cannot perform private migrations, and this implementation does not weaken that network boundary to make CI convenient.

Do not set the release approval variable until these decisions and setup are complete. Login/account linking does not itself authorize publication.

## Provider setup (browser-accessible dashboards)

1. In Render, review `infrastructure/cloud/render.yaml` from this repository. Keep Git auto-deploy **off**, private database/Key Value IP allowlists empty, and no worker services. Applying the Blueprint publishes a web service, so do this only after explicit owner approval. During initial setup the API will fail health checks until migrations and the restricted reader are configured; this is intentional fail-closed behavior.
2. Generate independent random secrets in a password manager/provider secret interface: viewer token (at least 32 characters) and URL-safe reader password (at least 32 characters). Never reuse the local development/control token. Keep the database-owner URL exclusively in the private release environment. The runtime API gets a TLS PostgreSQL URI for `failurelab_demo_reader` and database `failurelab_public`, with `sslmode=require` and `AUTH_VIEWER_TOKEN`; it receives no owner/admin/operator/control credential.
3. On the approved private runner, run `python scripts/cloud_database.py --approved` with `PUBLIC_SNAPSHOT_DATABASE=1`, `CLOUD_MIGRATION_DATABASE_URL` and `CLOUD_READER_PASSWORD` supplied through private environment secrets. This applies Alembic migrations and grants the unprivileged reader SELECT access. Migrations are never performed by the public web process.
4. Export a terminal, real `FailureLab demo` project using the operator-only `scripts/public_snapshot.py export --project <UUID> --output <private-file>`. Review it, then privately transfer and import it into the empty dedicated public database using `scripts/public_snapshot.py import --file <private-file> --reviewed` with the owner connection. Never commit the snapshot or expose the import operation as an HTTP endpoint. Active jobs, unexpected services, overwritten destinations and modified artifact digests are rejected. Future refreshes require a newly reviewed destination/snapshot; this is not a live link into private experiments.
5. In Vercel, create a Next.js project linked to this GitHub repository only after approval. Set Root Directory `frontend`, enable inclusion of source files outside that directory (the build/type generation uses `docs/openapi.json`), and use Node 24. Run all Vercel CLI commands from the repository root, as required for a monorepo (the workflow does this). Keep `frontend/vercel.json` Git deployment disabled; production deployment occurs through the checked release workflow. Do not authorize an initial automatic public preview until the read-only configuration is installed. If the import wizard cannot avoid initial publication, create the empty project through the authenticated provider API instead.
6. Copy `infrastructure/cloud/frontend.env.example` into Vercel's **server-only Production** environment using actual provisioned HTTPS origins. Set `PUBLIC_FRONTEND_ORIGIN` to the permanent Vercel/custom hostname; set both `BACKEND_URL` and `HOSTED_BACKEND_ORIGIN` to the exact Render HTTPS origin. Set `API_TOKEN` to the backend viewer token, `ACCESS_MODE=read_only`, `DEPLOYMENT_ENV=cloud`. No `NEXT_PUBLIC_` secret is supported. Temporary preview origins are intentionally not implicitly trusted.
7. The backend uses Render's actual `RENDER_EXTERNAL_URL` as its public origin and `RENDER_GIT_COMMIT` as its version. Keep `CORS_ORIGINS` empty: browsers use the same-origin Next bridge. For a separately approved direct client, allow only explicit HTTPS origins, never `*` or credentialed wildcard CORS.

## CI/CD setup and exact GitHub settings

Create a GitHub environment named `public-read-only`, with required reviewers and deployment restricted to `main`. Require `Safe CI` jobs through branch protection. Provision a **disposable, private-network, trusted-main-only** runner with labels `self-hosted`, `linux`, `x64`, `failurelab-cloud-release`, `ephemeral`. Never run pull-request code on it. It needs Python 3.12+, Node 24, GitHub CLI, outbound provider HTTPS access and private database connectivity. It is a release runner, not an experiment worker.

Set repository/environment variables:

| Variable | Value |
| --- | --- |
| `PUBLIC_FRONTEND_ORIGIN` | Actual permanent frontend HTTPS origin |
| `PUBLIC_BACKEND_ORIGIN` | Actual Render API HTTPS origin |
| `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` | IDs from the approved Vercel project |
| `FAILURELAB_PUBLIC_RELEASE_APPROVED` | `true` only after owner approval and all setup |

Set environment secrets through GitHub's UI (never paste them in chat/source): `CLOUD_MIGRATION_DATABASE_URL`, `CLOUD_READER_PASSWORD`, `RENDER_DEPLOY_HOOK`, `VERCEL_TOKEN`. The deploy-hook URL is itself a credential. Vercel production runtime variables must also be configured in its dashboard; they are pulled privately by the CLI. Use scoped provider credentials and rotate them under the account policy.

`.github/workflows/cloud-release.yml` runs only after successful **push** CI on `main`, checks the exact current SHA, requires the approval variable/environment/runner, applies additive migrations, deploys that SHA to Render, waits for exact-version readiness, builds/publishes the Vercel production frontend, then checks HTTPS pages, backend health/version, viewer role and rejected mutation. Render auto-deploy and Vercel Git deployment remain disabled, preventing a parallel unchecked release. GitHub's Actions job summary records the actual release result. Configure provider alerts and database backup/restore exercises before treating the service as production-operated.

An approved first release can be initiated by a reviewed push to `main` after setup. A failed check blocks the new release; it does not fabricate success or roll back database history. For rollback, approve a forward Git revert, let CI pass and redeploy that resulting revision. Review migration compatibility before any rollback.

## Verification and access

Run static configuration validation with `python scripts/validate_cloud.py`. The release itself runs `python scripts/cloud_release.py smoke --url <actual-frontend-origin> --revision <SHA>` externally. Browser acceptance must additionally check graph, evidence, authentication/error states and disabled execution at the real hostname. A production URL is considered delivered only after those external checks pass.

After an approved successful release, open the permanent frontend HTTPS hostname in any browser; no Codex, Docker, terminal or powered-on Mac is required. At present there is **no deployed/verified hostname to open**. Vercel connection is available; Render setup, billable-service approval, snapshot review, private runner and publication approval remain outstanding.

Hosted interactive fault experiments require a separately reviewed private execution network and authenticated operator ingress. They are deliberately not exposed by this release. The existing restricted Docker verifier remains required for actual candidate execution; native development without Docker reports infrastructure failure rather than a passing repair.

Provider references: [Render Blueprint specification](https://render.com/docs/blueprint-spec), [pricing](https://render.com/pricing), [deploy hooks](https://render.com/docs/deploy-hooks), [environment variables](https://render.com/docs/environment-variables), [Vercel monorepo settings](https://vercel.com/docs/monorepos/monorepo-faq), [Git deployment controls](https://vercel.com/docs/project-configuration/git-configuration), [prebuilt deployments](https://vercel.com/docs/cli/deploy).
