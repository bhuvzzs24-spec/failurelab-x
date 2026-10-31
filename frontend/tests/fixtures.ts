/** Unit-test fixtures only. Production code never imports this module. */
import { completeConfig } from "@/lib/validation";
import type {
  Artifact,
  Experiment,
  Finding,
  Graph,
  Overview,
  Project,
  Run,
  Schema,
  Summary,
} from "@/types/domain";
export const project: Project = { id: "project-test", name: "Test sandbox", created_at: 1 };
export const invariant: Schema["InvariantOut"] = {
  id: "inv-test",
  project_id: project.id,
  name: "Paid implies finalized",
  rule: {
    kind: "implies",
    antecedent: {
      kind: "compare",
      left: { path: "payment.status" },
      op: "eq",
      right: { value: "charged" },
    },
    consequent: {
      kind: "compare",
      left: { path: "order.status" },
      op: "eq",
      right: { value: "finalized" },
    },
  },
};
export const experiment: Experiment = {
  id: "experiment-test",
  project_id: project.id,
  name: "Test acknowledgement delay",
  config: { ...completeConfig(), invariant_ids: [invariant.id] },
};
export const run: Run = {
  id: "run-test",
  experiment_id: experiment.id,
  idempotency_key: "test",
  status: "COMPLETED",
  created_at: 1,
  updated_at: 2,
  deadline: 60,
  cancel_requested: 0,
  config: experiment.config,
  result: { evaluations: { [invariant.id]: { status: "FAIL" } } },
};
export const finding: Finding = {
  id: "finding-test",
  run_id: run.id,
  invariant_id: invariant.id,
  summary: "Cross-service correctness invariant violated",
  evidence: {
    status: "FAIL",
    observed: {
      payment: { status: "charged", amount: 100, quantity: 1 },
      order: { status: "pending", amount: 100, quantity: 1 },
      inventory: { status: "reserved", amount: 100, quantity: 1 },
    },
    expected: invariant.rule,
    evaluated_at: 2,
    evidence_refs: ["artifact-test"],
  },
};
export const artifact: Artifact = {
  id: "artifact-test",
  run_id: run.id,
  kind: "snapshot",
  created_at: 2,
  sha256: "a".repeat(64),
  payload: { stage: "verification", state: finding.evidence.observed },
};
export const summary: Summary = { run, findings: [finding], artifacts: [artifact] };
export const graph: Graph = {
  provenance: "explicit_registration",
  nodes: ["gateway", "order", "payment", "inventory"].map((name) => ({
    id: `service-${name}`,
    name: name as Schema["ServiceOut"]["name"],
    project_id: project.id,
    version: "test-version",
    operations: [{ method: "POST", path: "/test" }],
    resources: [],
  })),
  edges: ["order", "payment", "inventory"].map((name) => ({
    id: `edge-${name}`,
    project_id: project.id,
    source_id: "service-gateway",
    target_id: `service-${name}`,
    kind: "http",
    operation: "/test",
    workflow: "test",
  })),
};
export const overview: Overview = {
  service_count: 4,
  experiment_count: 1,
  run_count: 7,
  active_run_count: 2,
  violation_count: 3,
  artifact_count: 18,
  status_counts: { COMPLETED: 5, RUNNING: 2 },
  activity: [{ day: "2026-10-31", runs: 7 }],
  latest_runs: [run],
  latest_findings: [finding],
};
