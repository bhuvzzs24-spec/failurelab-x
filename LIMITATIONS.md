# Limitations and verification boundary

* Local tests used Python 3.13.15 and Node 24.22.2 on macOS. Python 3.12/Linux validation is configured in CI but is not established by the Mac results.
* Docker CLI/daemon and PostgreSQL server are unavailable in the delivery environment. Compose startup, Linux images/network isolation, PostgreSQL-specific migrations and the generated-candidate container workflow are not locally verified. SQLite/native/Redis results do not replace them.
* The candidate generator and independent container verifier are functional bounded implementations, but a recorded INFRASTRUCTURE_ERROR is not a successful repair. General repository/code repair, automatic merge/deploy, unrestricted model execution and production target onboarding are not supported.
* Optional Ollama was not available for measured runs. Deterministic adaptive selection, interventions and invariant evaluation do not require it.
* Benchmarks measure six deliberately seeded synthetic defect families with small repeated seeds. Held-outs change inputs/timing within the same families. No novel bug discovery, universal correctness, general false-positive rate, calibrated causal confidence or statistical superiority is claimed. See BENCHMARK_RESULTS.md for observed values and unmeasured fields.
* Seeds do not fix OS/HTTP/database scheduling. Version/hash capture supports scenario replay, not bit-for-bit determinism. Full-system CPU/memory overhead and long-run load/soak behavior are not measured.
* Static role tokens are not per-user SSO, tenant isolation or an enterprise account system. Public mode is read-only. Production control requires an identity-aware ingress, secret rotation, private workers and infrastructure security review. Hosted control frontend is deliberately blocked.
* Evidence is stored in PostgreSQL/SQLite JSON rows. Backup/restore, retention, encrypted managed storage, monitoring/SLOs and disaster-recovery drills require operator setup. Redaction needs human review before sharing unknown evidence.
* Base image tags are mutable; constraints are not hash-locked releases/SBOMs. Dependency audit and secret scans reflect their execution time and known advisory data only. Development-only generator advisories are documented in the results.
* The repair agent holds Docker daemon access and must be isolated on a trusted disposable VM. Shared hosted CI only builds images; it must not execute faults or patches.
* No public deployment, hosting account provisioning, DNS/TLS issuance, repo visibility change or production-readiness certification was performed.
