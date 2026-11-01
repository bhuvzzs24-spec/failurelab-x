"use client";
import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Background, Controls, ReactFlow, type Node, type Edge } from "@xyflow/react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import { z } from "zod";
import { toast } from "sonner";
import { Play, Download, StopCircle, ShieldCheck, GitBranch } from "lucide-react";
import {
  research,
  evidenceBundle,
  type ResearchCreate,
  type ResearchJob,
  type Trial,
} from "@/lib/research";
import { dateTime, shortId, asObject, asText } from "@/lib/utils";
import { useProject } from "./providers";
import { Button } from "./ui/button";
import { Panel, Loading, ErrorState } from "./ui/states";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
import { JsonView, downloadJson } from "./evidence-common";
import type { Section } from "@/types/domain";
const defects = [
  "payment_ack_loss",
  "unsafe_retry",
  "lost_finalization",
  "inventory_drift",
  "concurrent_retry",
  "failed_compensation",
] as const;
const active = (s: string) => ["CREATED", "QUEUED", "RUNNING"].includes(s);
const kindFor = {
  explorer: "SEARCH",
  ai: "INVESTIGATE",
  minimization: "MINIMIZE",
  patches: "REPAIR",
  verification: "VERIFY",
  benchmarks: "BENCHMARK",
} as const;
const labels = {
  SEARCH: "Start discovery",
  INVESTIGATE: "Test hypotheses",
  MINIMIZE: "Reduce sequence",
  REPAIR: "Prepare candidate",
  VERIFY: "Verify candidate",
  BENCHMARK: "Compare strategies",
};
const budgetSchema = z.coerce.number().int().min(2).max(60);
const hypothesisSchema = z.object({
  id: z.string(),
  description: z.string(),
  status: z.string(),
  services: z.array(z.string()),
  assumptions: z.array(z.string()),
  supporting_observations: z.array(z.string()),
  contradicting_observations: z.array(z.string()),
  intervention: z.string(),
  outcomes: z.array(z.record(z.string(), z.unknown())),
});
export function HypothesisGraph({
  hypotheses,
}: {
  hypotheses: z.infer<typeof hypothesisSchema>[];
}) {
  const nodes: Node[] = hypotheses.map((h, i) => ({
    id: h.id,
    position: { x: (i % 3) * 280, y: Math.floor(i / 3) * 130 },
    data: { label: `${h.description} · ${h.status}` },
    style: {
      background: "#181b32",
      color: "#f1f2ff",
      border: `1px solid ${h.status === "SUPPORTED" ? "#34d399" : "#747fa4"}`,
      width: 240,
    },
  }));
  const edges: Edge[] = hypotheses.slice(1).map((h) => ({
    id: `competing-${h.id}`,
    source: hypotheses[0].id,
    target: h.id,
    label: "competing explanation",
    style: { stroke: "#747fa4" },
  }));
  return (
    <div className="research-graph" aria-label="Competing causal hypotheses">
      <ReactFlow nodes={nodes} edges={edges} fitView colorMode="dark">
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
export function PatchDiff({ patch }: { patch: string }) {
  return (
    <pre className="patch-diff" tabIndex={0} aria-label="Candidate source diff">
      {patch.split("\n").map((line, i) => (
        <span
          key={i}
          className={line.startsWith("+") ? "addition" : line.startsWith("-") ? "deletion" : ""}
        >
          {line}
          {"\n"}
        </span>
      ))}
    </pre>
  );
}
function ResultView({ job }: { job: ResearchJob }) {
  const result = job.result;
  const hypotheses = z.array(hypothesisSchema).safeParse(result.hypotheses);
  const comparisons = z
    .array(
      z.object({
        strategy: z.string(),
        seed: z.number(),
        unique_bugs: z.number(),
        executed: z.number(),
        execution_cost_seconds: z.number(),
      }),
    )
    .safeParse(result.comparisons);
  const matrix = z
    .array(
      z.object({
        name: z.string(),
        original: z.object({ classification: z.string() }),
        candidate: z.object({ classification: z.string() }),
        wall_overhead_seconds: z.number(),
      }),
    )
    .safeParse(result.cases);
  return (
    <>
      {job.kind === "VERIFY" && (
        <div
          className="verification-outcome"
          role="status"
          aria-label="Verification outcome"
          data-outcome={asText(result.outcome)}
        >
          <strong>{asText(result.outcome)}</strong>
          <p>{asText(result.reason)}</p>
          <p className="microcopy">
            Job completion records the verification attempt. Only a passing verification outcome
            establishes that the candidate passed the tested cases.
          </p>
        </div>
      )}
      {hypotheses.success && (
        <>
          <HypothesisGraph hypotheses={hypotheses.data} />
          <div className="research-hypotheses">
            {hypotheses.data.map((h) => (
              <article key={h.id}>
                <span className="eyebrow">{h.status}</span>
                <h3>{h.description}</h3>
                <p>{h.intervention}</p>
                <details>
                  <summary>Assumptions & experimental evidence</summary>
                  <JsonView value={h} />
                </details>
              </article>
            ))}
          </div>
        </>
      )}
      {job.kind === "MINIMIZE" && result.original && result.reduced ? (
        <>
          <div className="research-comparison">
            <div>
              <h3>Original sequence</h3>
              <JsonView label="Original failure sequence" value={result.original} />
            </div>
            <div>
              <h3>Reduced sequence</h3>
              <JsonView label="Reduced failure sequence" value={result.reduced} />
            </div>
          </div>
          <p className="microcopy">
            Reproductions: {asText(result.reproductions)} / {asText(result.confirmation_trials)} ·
            Local neighborhood audited:{" "}
            {result.local_minimality_tested === true ? "yes" : "not established"}. This is not
            global minimality.
          </p>
        </>
      ) : null}
      {matrix.success && matrix.data.length > 0 && (
        <div className="table-wrap">
          <table>
            <caption>Matched original and candidate verification</caption>
            <thead>
              <tr>
                <th>Case</th>
                <th>Original</th>
                <th>Candidate</th>
                <th>Wall delta (s)</th>
              </tr>
            </thead>
            <tbody>
              {matrix.data.map((r) => (
                <tr key={r.name}>
                  <td>{r.name}</td>
                  <td>{r.original.classification}</td>
                  <td>{r.candidate.classification}</td>
                  <td>{r.wall_overhead_seconds.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {comparisons.success && (
        <>
          <div
            className="research-chart"
            aria-label="Measured defect families by strategy and seed"
          >
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={comparisons.data.map((r) => ({ ...r, label: `${r.strategy} / ${r.seed}` }))}
              >
                <CartesianGrid stroke="#2a304a" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: "#b8bfd6", fontSize: 10 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Bar dataKey="unique_bugs" name="Defect families" fill="#9981ff" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="microcopy">
            Equal budgets and seed set. Adaptive improvement in this run:{" "}
            {result.adaptive_improved_observed_mean === true ? "observed" : "not observed"}. No
            general superiority claim.
          </p>
        </>
      )}
      <details
        open={
          !hypotheses.success &&
          !comparisons.success &&
          (!matrix.success || matrix.data.length === 0)
        }
      >
        <summary>Complete recorded report</summary>
        <JsonView value={result} label="Research job report" />
      </details>
    </>
  );
}
export function ResearchWorkspace({
  section,
}: {
  section: Extract<
    Section,
    "explorer" | "ai" | "minimization" | "patches" | "verification" | "benchmarks"
  >;
}) {
  const { projectId } = useProject();
  const cache = useQueryClient();
  const kind = kindFor[section];
  const [budget, setBudget] = useState("12");
  const [seed, setSeed] = useState("42");
  const [strategy, setStrategy] = useState<"adaptive" | "random" | "coverage">("adaptive");
  const [defect, setDefect] = useState<(typeof defects)[number] | "all">("all");
  const [trialId, setTrialId] = useState("");
  const [candidateId, setCandidateId] = useState("");
  const [jobId, setJobId] = useState("");
  const [pending, setPending] = useState<ResearchCreate | null>(null);
  const [validation, setValidation] = useState("");
  const jobs = useQuery({
    queryKey: ["research-jobs", projectId],
    queryFn: () => research.jobs(projectId),
    refetchInterval: 2000,
  });
  const trials = useQuery({
    queryKey: ["research-trials", projectId],
    queryFn: () => research.trials(projectId),
    refetchInterval: 5000,
  });
  const candidates = useQuery({
    queryKey: [
      "research-candidates",
      projectId,
      jobs.data
        ?.filter((j) => j.kind === "REPAIR" || j.kind === "VERIFY")
        .map((j) => [j.id, j.status, j.updated_at]),
    ],
    queryFn: () => research.candidates(projectId),
    refetchInterval: 5000,
  });
  const capabilities = useQuery({
    queryKey: ["research-capabilities"],
    queryFn: research.capabilities,
  });
  const selected =
    jobId
      ? jobs.data?.find((j) => j.id === jobId)
      : jobs.data?.filter((j) => j.kind === kind).sort((a, b) => b.created_at - a.created_at)[0];
  const decisions = useQuery({
    queryKey: ["research-decisions", selected?.id, selected?.status],
    queryFn: () => research.decisions(selected!.id),
    enabled: !!selected,
    refetchInterval: selected && active(selected.status) ? 2000 : false,
  });
  const artifacts = useQuery({
    queryKey: ["research-artifacts", selected?.id, selected?.status],
    queryFn: () => research.artifacts(selected!.id),
    enabled: !!selected,
    refetchInterval: selected && active(selected.status) ? 3000 : false,
  });
  const violations =
    trials.data
      ?.filter((t) => t.classification === "APPLICATION_VIOLATION" && t.variant === "original")
      .sort((a, b) => a.created_at - b.created_at) ?? [];
  const source = violations.find((t) => t.id === trialId) ?? violations.at(-1);
  const recordedSource = selected?.input.source_trial_id
    ? trials.data?.find((t) => t.id === selected.input.source_trial_id)
    : source;
  const candidate = candidates.data?.find((c) => c.id === candidateId) ?? candidates.data?.[0];
  const reviewedId =
    kind === "REPAIR"
      ? selected?.result.candidate_id
      : kind === "VERIFY"
        ? selected?.input.candidate_id
        : null;
  const reviewedCandidate =
    typeof reviewedId === "string" ? candidates.data?.find((c) => c.id === reviewedId) : candidate;
  const start = useMutation({
    mutationFn: (body: ResearchCreate) => research.create(projectId, body),
    onSuccess: (j) => {
      cache.setQueryData<ResearchJob[]>(["research-jobs", projectId], (previous = []) => [
        j, ...previous.filter((row) => row.id !== j.id),
      ]);
      setJobId(j.id);
      setPending(null);
      void cache.invalidateQueries({ queryKey: ["research-jobs", projectId] });
      toast.success("Research job queued");
    },
    onError: (e) => toast.error(e.message),
  });
  const exportRecord = useMutation({
    mutationFn: evidenceBundle,
    onSuccess: (bundle) => downloadJson(bundle, `failurelab-evidence-${bundle.job.id}.json`),
    onError: (e) => toast.error(e.message),
  });
  const cancel = useMutation({
    mutationFn: research.cancel,
    onSuccess: () => {
      void cache.invalidateQueries({ queryKey: ["research-jobs", projectId] });
      toast.success("Cancellation requested");
    },
    onError: (e) => toast.error(e.message),
  });
  const history = useMemo(() => {
    return (decisions.data ?? [])
      .sort((a, b) => a.step - b.step)
      .map((d, i, rows) => ({
        step: i + 1,
        utility: d.score,
        novelty: rows.slice(0, i + 1).reduce((total, row) => total + row.reward, 0),
        cost: d.cost_seconds,
      }));
  }, [decisions.data]);
  if (jobs.isPending || trials.isPending || candidates.isPending) return <Loading />;
  if (jobs.error || trials.error || candidates.error)
    return (
      <ErrorState
        error={jobs.error ?? trials.error ?? candidates.error}
        retry={() => {
          void jobs.refetch();
          void trials.refetch();
          void candidates.refetch();
        }}
      />
    );
  function prepareJob() {
    const parsed = budgetSchema.safeParse(budget);
    const seedNumber = Number(seed);
    if (
      !parsed.success ||
      !Number.isInteger(seedNumber) ||
      seedNumber < 0 ||
      seedNumber > 2147483647
    ) {
      setValidation("Budget must be 2–60 and seed must be a bounded nonnegative integer.");
      return;
    }
    if (["MINIMIZE", "INVESTIGATE", "REPAIR"].includes(kind) && !source) {
      setValidation("Discover an original invariant violation before starting this action.");
      return;
    }
    if (kind === "VERIFY" && !candidate) {
      setValidation("Prepare a candidate patch first.");
      return;
    }
    setValidation("");
    setPending({
      kind,
      idempotency_key: crypto.randomUUID(),
      budget: parsed.data,
      repeats: 2,
      seeds: [17, 42, 93],
      source_trial_id: source?.id,
      candidate_id: candidate?.id,
      search: {
        strategy,
        budget: parsed.data,
        seed: seedNumber,
        defects: defect === "all" ? [...defects] : [defect],
      },
    });
  }
  return (
    <div className="workspace-stack research-workspace">
      <Panel
        title="Bounded research controls"
        subtitle="Managed local benchmark only · authoritative invariants · persistent evidence"
      >
        <div className="research-controls">
          {(kind === "SEARCH" || kind === "BENCHMARK") && (
            <>
              {kind === "SEARCH" && (
                <label>
                  Selection strategy
                  <select
                    aria-label="Selection strategy"
                    value={strategy}
                    onChange={(e) => setStrategy(e.target.value as typeof strategy)}
                  >
                    {["adaptive", "random", "coverage"].map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                </label>
              )}
              <label>
                Benchmark defect
                <select
                  aria-label="Benchmark defect"
                  value={defect}
                  onChange={(e) => setDefect(e.target.value as typeof defect)}
                >
                  <option value="all">All six defects</option>
                  {defects.map((d) => (
                    <option key={d} value={d}>
                      {d.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </label>
              {kind === "SEARCH" && (
                <label>
                  Selection seed
                  <input
                    aria-label="Selection seed"
                    type="number"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                  />
                </label>
              )}
            </>
          )}
          {!["REPAIR", "VERIFY"].includes(kind) && (
            <label>
              {kind === "BENCHMARK" ? "Trials per strategy / seed" : "Trial budget"}
              <input
                aria-label="Trial budget"
                type="number"
                min={2}
                max={60}
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
              />
            </label>
          )}
          {["MINIMIZE", "INVESTIGATE", "REPAIR"].includes(kind) && (
            <label>
              Observed failure
              <select
                aria-label="Observed failure"
                value={source?.id ?? ""}
                onChange={(e) => setTrialId(e.target.value)}
              >
                <option value="" disabled>
                  Select original violation
                </option>
                {violations.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.scenario.defect} · {shortId(t.id)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {kind === "VERIFY" && (
            <label>
              Candidate patch
              <select
                aria-label="Candidate patch"
                value={candidate?.id ?? ""}
                onChange={(e) => setCandidateId(e.target.value)}
              >
                <option value="" disabled>
                  Select prepared candidate
                </option>
                {candidates.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {shortId(c.id)} · {c.status}
                  </option>
                ))}
              </select>
            </label>
          )}
          <Button control="execute" onClick={prepareJob} disabled={start.isPending}>
            <Play size={14} />
            {labels[kind]}
          </Button>
        </div>
        {validation && <p role="alert">{validation}</p>}
        {kind === "VERIFY" && capabilities.data?.repair_agent_configured === false && (
          <p className="microcopy">
            Docker verification agent is not configured. A verification request will persist an
            infrastructure error; candidate code will not execute on this host.
          </p>
        )}
        {kind === "BENCHMARK" && (
          <p className="microcopy">
            Runs random, coverage, and adaptive search using seeds 17, 42, 93 and the same budget
            per pair, then separate held-out, witness, comparator and minimization controls.
            Evaluation outcomes never train the planners. Every real HTTP trial consumes budget.
          </p>
        )}
      </Panel>
      <Dialog
        open={!!pending}
        onOpenChange={(v) => {
          if (!v && !start.isPending) setPending(null);
        }}
      >
        <DialogContent>
          <DialogTitle>Run {kind.toLowerCase()} in the local sandbox?</DialogTitle>
          <DialogDescription>
            Executes bounded HTTP faults against the managed benchmark, using fresh transaction
            namespaces. No production target or arbitrary command is accepted. Cancellation stops
            between bounded trials. Candidate execution requires the restricted Docker agent.
          </DialogDescription>
          <div className="dialog-actions">
            <Button variant="secondary" onClick={() => setPending(null)} disabled={start.isPending}>
              Back
            </Button>
            <Button
              control="execute"
              disabled={start.isPending}
              onClick={() => pending && start.mutate(pending)}
            >
              Confirm sandbox execution
            </Button>
          </div>
          {start.error && <p role="alert">{start.error.message}</p>}
        </DialogContent>
      </Dialog>
      <Panel title="Execution record" subtitle="Results below are read from persisted backend jobs">
        <div className="research-controls">
          <label>
            Research job
            <select
              aria-label="Research job"
              value={selected?.id ?? ""}
              onChange={(e) => setJobId(e.target.value)}
            >
              <option value="" disabled>
                Select a job
              </option>
              {jobs.data
                ?.filter((j) => j.kind === kind)
                .sort((a, b) => b.created_at - a.created_at)
                .map((j) => (
                  <option key={j.id} value={j.id}>
                    {dateTime(j.created_at)} · {j.status} · {shortId(j.id)}
                  </option>
                ))}
            </select>
          </label>
          {selected && (
            <>
              <span className="eyebrow" role="status">
                {selected.status}
              </span>
              <Button
                variant="secondary"
                disabled={exportRecord.isPending}
                onClick={() => exportRecord.mutate(selected.id)}
              >
                <Download size={14} />
                Export record
              </Button>
              {active(selected.status) && (
                <Button
                  variant="secondary"
                  control="execute"
                  onClick={() => cancel.mutate(selected.id)}
                  disabled={cancel.isPending || selected.cancel_requested}
                >
                  <StopCircle size={14} />
                  {selected.cancel_requested ? "Cancellation pending" : "Cancel job"}
                </Button>
              )}
            </>
          )}
        </div>
        {!selected ? (
          <p className="microcopy">
            No {kind.toLowerCase()} job exists yet. Start a sandbox job to collect evidence.
          </p>
        ) : (
          <>
            <p className="microcopy mono">
              Execution {selected.id} · Deadline {dateTime(selected.deadline)}
            </p>
            {selected.error && <p role="alert">{selected.error}</p>}
            {selected.status === "COMPLETED" ? (
              <ResultView job={selected} />
            ) : (
              <p className="microcopy">
                {active(selected.status)
                  ? "Waiting for bounded experiments and evidence collection."
                  : "No completed result. Partial evidence remains available."}
              </p>
            )}
          </>
        )}
      </Panel>
      {kind === "SEARCH" && history.length > 0 && (
        <Panel
          title="Measured discovery history"
          subtitle="Cumulative novelty reward; utility is not a probability"
        >
          <div className="research-chart" aria-label="Measured discovery history">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={history}>
                <CartesianGrid stroke="#2a304a" />
                <XAxis dataKey="step" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Line dataKey="novelty" stroke="#a38aff" name="Novel signatures" />
                <Line dataKey="cost" stroke="#41d7e8" name="Trial wall seconds" />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <details>
            <summary>Planner contexts, utilities and rewards</summary>
            <JsonView value={decisions.data} />
          </details>
        </Panel>
      )}
      {(kind === "REPAIR" || kind === "VERIFY") && reviewedCandidate && (
        <Panel
          title="Candidate source change"
          subtitle="Literal policy patch · isolated workspace · never merged"
        >
          <p className="microcopy">
            <GitBranch size={14} /> {shortId(reviewedCandidate.id)} · {reviewedCandidate.status}
          </p>
          <PatchDiff patch={reviewedCandidate.patch} />
          <details>
            <summary>Validation and provenance</summary>
            <JsonView value={reviewedCandidate.metadata} />
          </details>
        </Panel>
      )}
      {recordedSource && ["MINIMIZE", "INVESTIGATE", "REPAIR"].includes(kind) && (
        <TrialEvidence trial={recordedSource} />
      )}
      {selected && (
        <Panel
          title="Evidence artifacts"
          subtitle="Checksummed backend records; display and downloads are redacted"
        >
          <details>
            <summary>{artifacts.data?.length ?? 0} recorded artifacts</summary>
            <JsonView value={artifacts.data} />
          </details>
          {artifacts.error && <p role="alert">{artifacts.error.message}</p>}
        </Panel>
      )}
    </div>
  );
}
function TrialEvidence({ trial }: { trial: Trial }) {
  const evidence = asObject(trial.evidence);
  return (
    <Panel
      title="Observed fact: authoritative invariant violation"
      subtitle={`${trial.scenario.defect} · ${trial.classification}`}
    >
      <p className="microcopy">
        <ShieldCheck size={14} /> Signature {trial.signature} · Trial {trial.id}
      </p>
      <details>
        <summary>Workflow timeline and fault receipts</summary>
        <JsonView
          value={{ timeline: evidence.workflow, fault_receipts: evidence.fault_receipts }}
        />
      </details>
      <details>
        <summary>Expected versus observed authoritative state</summary>
        <JsonView value={evidence.snapshots} />
      </details>
      <p className="microcopy">
        Causal explanations remain hypotheses until controlled interventions support them. Missing
        adapters never establish a finding.
      </p>
    </Panel>
  );
}
