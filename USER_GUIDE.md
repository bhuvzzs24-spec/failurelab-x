# User guide

Select a real registered project in the top bar. Backend readiness and access role are live. A read-only banner and disabled controls reflect backend/session and server configuration; missing permission data disables execution. Project counts distinguish legacy runs from research jobs.

1. **Command center**: persisted service/run/finding/evidence counts, recent activity and graph preview. Research counts are separate; no synthetic live statistics.
2. **System graph**: registered dependencies with zoom/pan, automatic layout, filters and keyboard-selectable service details. Topology is registered knowledge; absence of a health/fault indicator is not evidence of health.
3. **Experiment studio**: inspect target/invariants, validate bounded fault parameters, review sandbox warning and confirm. Run monitoring polls real statuses; cancellation is cooperative.
4. **Failure investigator**: select a measured legacy finding; compare expected/observed state, events, provenance and reproduction metadata. Facts, hypotheses and missing evidence are distinct.
5. **Evidence explorer**: filter recorded artifacts; inspect escaped JSON and download permitted redacted payloads. Raw server paths and tokens are removed.
6. **Replay**: view original configuration and instructions. Automatic replay appears unavailable where the legacy backend has no replay endpoint.
7. **Adaptive explorer**: choose a finite seeded defect family, strategy, seed and trial budget. Run and inspect actual trial classifications/planner history.
8. **Minimal sequence**: select a measured original violation. Reduction shows only confirmed exact-signature reproductions; exhausted budgets may leave minimality unproved.
9. **AI investigator**: run paired interventions and review supported/refuted/inconclusive hypotheses with trial references. A supported mechanism is not proof of a unique source-level cause.
10. **Patch review**: generate a bounded literal policy candidate in a separate workspace and inspect its actual diff/static checks. This does not modify application code.
11. **Fix verification lab**: choose candidate; compare independently executed original/candidate cases. No agent means infrastructure error. Finite tested-scenario success is not universal correctness.
12. **Benchmark dashboard**: equal-budget strategy measurements, controls and recorded research report, without a superiority claim.
13. **Settings**: register projects/services and inspect actual environment/safety capabilities. Secrets cannot be edited or read here.

Research **Export record** gathers the latest job, all paginated trials, decisions/artifacts and the relevant candidate/source failure; the JSON states completeness and redaction limits. Downloads are client-side, bounded to 32 MiB. A partial or failed fetch cannot report a complete package. Legacy single-artifact downloads remain separate.
