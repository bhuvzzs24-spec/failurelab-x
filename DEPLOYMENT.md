# Deployment preparation (no deployment performed)

## Three independent trust zones

A. Public demonstration: Next on Vercel/equivalent, ACCESS_MODE=read_only, exact HTTPS PUBLIC_FRONTEND_ORIGIN/HOSTED_BACKEND_ORIGIN/BACKEND_URL, and server-only API_TOKEN containing only the backend viewer credential. Use a sanitized immutable database snapshot; no worker, fault-control secret or agent credentials in this zone.

B. Application API: long-running container service, managed PostgreSQL with TLS and separate migration/runtime/reader roles, dedicated private Redis, identity-aware ingress for authenticated control use, audit retention and tested database backups. Keep the public snapshot API APP_MODE=read_only with its read-only database role. Public ingress permits GET/HEAD only. Local Swagger is disabled in hosted modes. `infrastructure/production/compose.read-only.yaml`, `read-only.env.example`, `roles.sql` and `ingress.conf.example` are operator-reviewed templates, not provisioned infrastructure.

C. Execution: private isolated worker VMs/network, private managed sandbox services and separate broker credentials. No production targets/secrets. A trusted Docker repair agent lives on a disposable VM and is never public. Broker TLS/auth, firewall egress deny rules, tenant scheduling, image signing and workload isolation require actual infrastructure configuration. Do not run arbitrary candidate patches in a general API container.

Vercel request functions are suitable for the bounded frontend bridge (maxDuration=15), not durable Celery workers, Docker daemon control or long experiments. Jobs run asynchronously on private worker hosts. Verify plan-specific limits against [Vercel function limitations](https://vercel.com/docs/functions/limitations) and [runtime documentation](https://vercel.com/docs/functions/runtimes); no worker lifetime depends on a browser request. Public frontend controls remain unavailable; authenticated hosted control UI is intentionally not enabled by the current bridge.

## Operator sequence

1. Obtain hosting accounts/DNS/TLS, managed database/Redis, private VM/subnets, secrets management and identity-provider configuration. Obtain explicit approval for any public deployment.
2. Build/review/pin immutable application/frontend/verifier images on an isolated Docker host; scan them. Run PostgreSQL migrations on a disposable clone and validate restore before production-like data.
3. Apply reviewed least-privilege roles (template contains no passwords). Migrate with an owner credential; serve the sanitized snapshot with SELECT-only role. Set independent random tokens via the hosting secret manager. Verify no secrets enter browser bundles.
4. Start read-only API privately, verify /health and /ready, then TLS ingress. Configure exact HTTPS frontend/backend origins. Publish a sanitized snapshot only after evidence review. Smoke-test GET and verify all POST/PUT/DELETE paths remain denied at ingress/API/bridge.
5. Configure backups/restores, audit/log retention, rate limiting/perimeter abuse controls, alerts for readiness/queue age/stale leases and incident shutdown. Do not advertise a public worker control endpoint.
6. Separately approve/configure a single-use isolated integration runner and its GitHub environment reviewers, then run the manual workflow. Never run destructive fault workloads on shared runners.

The supplied Compose health ordering follows [Docker startup-order semantics](https://docs.docker.com/compose/how-tos/startup-order); restart/resource/network settings require validation on the deployment host, per the [Compose service specification](https://docs.docker.com/reference/compose-file/services/). Health readiness is not an availability SLO. No hosting account, cloud resource, public endpoint or DNS record has been created. This preparation does not establish production readiness.
