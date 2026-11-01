# Experiment and acceptance guide

Use only the disposable seeded sandbox. Experiments reset its demonstration business state under an exclusive lease. Do not use it for other transactions during a run.

```sh
make start
# UI: Experiment studio → Review & run → Start sandbox experiment
# CLI, same private .env as running services:
python scripts/acceptance.py --benchmark --budget 12
python scripts/browser_acceptance.py
```

The acceptance script registers/reuses the demo, verifies graph nodes/edges, runs a normal transaction followed by the payment acknowledgement fault, asserts a finalized/charged baseline, checks actual findings, then submits SEARCH → MINIMIZE → INVESTIGATE → REPAIR → VERIFY. `--benchmark` adds the repeated-seed study. It saves actual job/outcome/artifact references in private `work/phase4/acceptance.json`. Budget is finite: if no violation is found, it fails rather than inventing a source. A verification infrastructure outcome is recorded explicitly; script completion alone does not establish the entire repair workflow.

Expected deliberate failure: payment commits using its idempotency key; proxy latency exceeds the coordinator deadline; order remains pending. Adapters read authoritative payment/order/inventory rows. The implication “charged payment implies finalized order” fails after its bounded window. An HTTP error alone cannot create the finding. Faults are removed in finally blocks; leases also expire after abnormal worker termination.

Research CLI individual steps and exact source/candidate IDs are described in `docs/PHASE3.md` and `python scripts/research.py --help`. Legacy run statuses and research statuses differ; inspect outcome separately from COMPLETED. Cancelling a run/job requests cooperative termination; already committed business effects are not undone. Reproduction records contain seed, inputs, fault receipts, versions and hashes. OS scheduling, HTTP timing and database contention prevent bit-for-bit replay guarantees.

Generated patch validation needs an enabled Docker agent. Matched comparisons include original/repeated failure, no-fault regression, held-out amount/quantity, held-out timing and related concurrency. Missing evidence/injection is inconclusive, missing infrastructure is an error, and any candidate violation fails verification. The benchmark's shipped reference controls are not generated-candidate results.
