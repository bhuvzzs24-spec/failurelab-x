# Security model and operational gates

This is a private correctness laboratory, not a public chaos endpoint. Do not attach it to production targets. No deployment or repository visibility change is performed by the delivery scripts.

## API and browser boundary

APP_MODE=local accepts the existing API_TOKEN as admin on loopback. Hosted/read_only modes ignore that legacy token and require independent >=32-character AUTH_VIEWER_TOKEN (plus optional distinct AUTH_OPERATOR_TOKEN/AUTH_ADMIN_TOKEN); reuse of legacy/control tokens is rejected. Viewer can read, operator can submit/cancel experiments/research, admin can manage registration and read audit records. read_only denies all mutations regardless of role. Static role tokens identify service/operator principals, not individual users or tenants. A private identity-aware ingress is required before multi-user hosted control access.

Hosted access has Redis-backed fixed-window peer limits (600/minute) and actor mutation limits (default 30/minute). Redis failure fails closed with 503; 429 carries Retry-After. Trust-proxy identity and perimeter abuse protection still require deployment configuration. Mutations persist audit intent before authorization completes; inability to persist blocks execution. Final status is recorded; a crash can leave status 0 (pending), which is evidence requiring investigation. Denied requests are best-effort audited. Audit identities are token hashes, never token values; route templates/resource IDs and request UUIDs avoid recording arbitrary bodies/secrets. Audit retention/export is an operator responsibility.

The Next bridge permits fixed path/method patterns, no redirects, bounded JSON requests/responses, server-only credentials, same-origin local mutations and explicit origin configuration. Public-host bridge access is read-only only. Read-only backend plus least-privilege snapshot database provides a second boundary. UI controls disable if session permissions cannot be verified. Authentication is enforced by API, not buttons.

## Execution and evidence

Targets are logical managed allowlists and operator-configured local HTTP origins; no submitted URL, command, arbitrary repository or image can execute. Demo/proxy/benchmark controls have independent secrets and no published Compose ports. Request bodies have 64-KiB, chunk and receive-time bounds. Artifact canonical JSON is size-limited (256 KiB), hash addressed in PostgreSQL; downloads escape text and redact secrets/paths. Redaction is defense in depth, not proof arbitrary imported evidence is safe to publish. Review a sanitized snapshot before public demonstration.

Fault TTLs, namespace scoping, exclusive sandbox leases, deadlines/fencing and scheduler recovery bound failures/cancellation/crashes. Containers are nonroot, cap-drop, no-new-privileges, read-only with bounded tmpfs/resources. Compose networks separate public-facing API/Next from databases, sandbox and trusted agent. Actual Docker isolation needs verification on a Docker host; native loopback testing does not demonstrate it.

The optional agent controls Docker and is therefore **host-equivalent trusted infrastructure** even though its own container is nonroot/cap-drop. Run only on an isolated disposable VM with no production secrets, private network and strong agent token. Never expose its API or socket publicly. Candidate containers use a fixed inspected image ID, no network, read-only filesystem/input, nonroot UID and bounded resources/deadlines; cleanup removes owned containers. General untrusted arbitrary Python repair is not supported. Do not weaken these rules to bypass missing Docker.

## Dependencies and CI

Python constraints capture the tested application/test closure; they are not a platform-independent hashed lock or signed SBOM. npm uses its lockfile. Rebuild/re-audit regularly and pin release images by reviewed digest. Base image tags and the Docker CLI build stage remain mutable. Secret scanner checks tracked/staged content heuristically; it cannot guarantee absence of every secret. Keep .env/evidence/logs/keys ignored.

Shared GitHub CI runs a curated non-fault test allowlist, dependency/secret checks and container builds. Fault and candidate execution require the separately approved single-use isolated runner workflow. Configure environment required reviewers and runner disposal before using it. These boundaries follow [GitHub's secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use). See BENCHMARK_RESULTS.md for actual dependency audit counts and LIMITATIONS.md for unverified infrastructure.
