"use client";
import { useAccess } from "./access";
import { JsonView } from "./evidence-common";
import { useExperiments, useInvariants, useRuns, useGraph } from "@/hooks/data";
import { api } from "@/lib/api";
import { asObject, asText, dateTime, shortId } from "@/lib/utils";
import {
  completeConfig,
  definitionSchema,
  faultKinds,
  type DefinitionValues,
} from "@/lib/validation";
import type { Experiment, Run } from "@/types/domain";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  ChevronDown,
  FlaskConical,
  Play,
  Plus,
  Save,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { useProject } from "./providers";
import { RunMonitor } from "./run-monitor";
import { Button } from "./ui/button";
import { Confirm } from "./ui/confirm";
import { EmptyState, ErrorState, Loading, Panel } from "./ui/states";
import { StatusBadge } from "./ui/status";

function FormField({
  label,
  error,
  children,
  hint,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <label className="form-field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
      {error && (
        <small className="field-error" role="alert">
          {error}
        </small>
      )}
    </label>
  );
}
function Builder({
  definition,
  onRun,
  onSaved,
}: {
  definition?: Experiment;
  onRun: (run: Run) => void;
  onSaved: (id: string) => void;
}) {
  const { projectId, projects } = useProject();
  const invariants = useInvariants(projectId);
  const graph = useGraph(projectId);
  const [step, setStep] = useState(0);
  const [furthest, setFurthest] = useState(0);
  const [accepted, setAccepted] = useState<Run | null>(null);
  const client = useQueryClient();
  const [review, setReview] = useState<DefinitionValues | null>(null);
  const key = useRef<string | null>(null);
  const persisted = useRef<{ fingerprint: string; id: string } | null>(null);
  const form = useForm<DefinitionValues>({
    resolver: zodResolver(definitionSchema),
    defaultValues: {
      name: definition?.name ?? "Controlled sandbox experiment",
      config: completeConfig(definition?.config),
    },
  });
  const {
    register,
    handleSubmit,
    formState: { errors, isDirty },
  } = form;
  const save = useMutation({
    mutationFn: (values: DefinitionValues) => api.createExperiment(projectId, values),
    onSuccess: (saved) => {
      client.setQueryData<Experiment[]>(["experiments", projectId], (old) => [
        ...(old ?? []).filter((item) => item.id !== saved.id),
        saved,
      ]);
      toast.success("Experiment definition persisted");
      void client.invalidateQueries({ queryKey: ["experiments", projectId] });
      void client.invalidateQueries({ queryKey: ["overview", projectId] });
      onSaved(saved.id);
    },
    onError: (error) => toast.error(error.message),
  });
  const start = useMutation({
    mutationFn: async (values: DefinitionValues) => {
      const fingerprint = JSON.stringify(values);
      let id = definition?.id;
      if (!id || isDirty) {
        if (persisted.current?.fingerprint === fingerprint) id = persisted.current.id;
        else {
          const created = await api.createExperiment(projectId, values);
          client.setQueryData<Experiment[]>(["experiments", projectId], (old) => [
            ...(old ?? []).filter((item) => item.id !== created.id),
            created,
          ]);
          id = created.id;
          persisted.current = { fingerprint, id };
        }
      }
      if (!key.current) key.current = `ui_${crypto.randomUUID().replaceAll("-", "")}`;
      return api.start(id, key.current);
    },
    onSuccess: (run) => {
      toast.success("Experiment accepted by backend");
      key.current = null;
      void client.invalidateQueries({ queryKey: ["experiments", projectId] });
      void client.invalidateQueries({ queryKey: ["runs", projectId] });
      void client.invalidateQueries({ queryKey: ["overview", projectId] });
      setAccepted(run);
      setStep(4);
      setFurthest(4);
      onRun(run);
    },
    onError: (error) => toast.error(error.message),
  });
  const steps = [
    "Select target",
    "Configure fault",
    "Select invariants",
    "Review experiment",
    "Execute & monitor",
  ];
  const revealInvalid = (issues: typeof errors) =>
    setStep(issues.name ? 0 : issues.config?.fault ? 1 : 2);
  async function nextStep() {
    const valid =
      step === 0
        ? await form.trigger("name")
        : step === 1
          ? await form.trigger([
              "config.fault.kind",
              "config.fault.phase",
              "config.fault.delay_seconds",
              "config.fault.duration_seconds",
            ])
          : await form.trigger();
    if (valid) {
      setStep(Math.min(step + 1, 3));
      setFurthest(Math.max(furthest, Math.min(step + 1, 3)));
    }
  }
  const values = form.getValues();
  const target = graph.data?.nodes.find((service) => service.name === "payment");
  return (
    <form
      onSubmit={handleSubmit((values) => setReview(values), revealInvalid)}
      noValidate
      className="experiment-form"
    >
      <ol className="wizard-steps" aria-label="Experiment setup steps">
        {steps.map((label, index) => (
          <li
            key={label}
            className={
              step === index ? "wizard-current" : index <= furthest ? "wizard-visited" : ""
            }
          >
            <button
              type="button"
              aria-current={step === index ? "step" : undefined}
              disabled={index > furthest}
              onClick={() => setStep(index)}
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{label}</strong>
            </button>
          </li>
        ))}
      </ol>
      <div className="wizard-stage-heading">
        <span className="eyebrow">STEP {step + 1} OF 5</span>
        <h3>{steps[step]}</h3>
        <p>
          {
            [
              "Give this experiment a name and choose an authorized service boundary.",
              "Define exactly how and for how long the boundary should fail.",
              "Choose the business guarantees this experiment must verify.",
              "Review the bounded scope before any fault is activated.",
              "The backend owns execution. Inspect its live lifecycle in the monitor.",
            ][step]
          }
        </p>
      </div>
      <fieldset className="wizard-section" hidden={step !== 0}>
        <legend className="sr-only">Target and definition</legend>
        <FormField label="Experiment name" error={errors.name?.message}>
          <input
            {...register("name")}
            aria-invalid={!!errors.name}
            placeholder="Name this experiment"
          />
        </FormField>
        <label className="wizard-target-card">
          <input type="radio" value="payment" {...register("config.fault.target")} />
          <span className="wizard-target-icon">
            <FlaskConical size={20} />
          </span>
          <span>
            <strong>Payment service</strong>
            <small>
              {target
                ? target.version
                : graph.isPending
                  ? "Checking registered services…"
                  : "Service registration unavailable"}
            </small>
          </span>
          <span className="subtle-chip">Allowlisted</span>
        </label>
        <p className="microcopy">
          The current engine supports the registered payment boundary. Other targets cannot be
          injected through this interface.
        </p>
      </fieldset>
      <fieldset className="wizard-section" hidden={step !== 1}>
        <legend className="sr-only">Fault parameters</legend>
        <div className="notice notice-neutral">
          <ShieldCheck size={16} />
          <div>
            <strong>Managed demo boundary</strong>
            <span>
              Only the registered payment service is an allowed fault target. Every run resets the
              demo under an exclusive sandbox lease.
            </span>
          </div>
        </div>
        <div className="form-grid">
          <FormField label="Fault type" error={errors.config?.fault?.kind?.message}>
            <select {...register("config.fault.kind")}>
              {faultKinds.map((kind) => (
                <option key={kind} value={kind}>
                  {kind.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Injection phase" error={errors.config?.fault?.phase?.message}>
            <select {...register("config.fault.phase")}>
              <option value="after">After upstream response</option>
              <option value="before">Before forwarding</option>
            </select>
          </FormField>
          <FormField
            label="HTTP delay (seconds)"
            error={errors.config?.fault?.delay_seconds?.message}
            hint="Applies to latency faults; maximum 10 seconds."
          >
            <input
              type="number"
              min="0"
              max="10"
              step="0.1"
              {...register("config.fault.delay_seconds", { valueAsNumber: true })}
            />
          </FormField>
          <FormField
            label="Fault lease TTL (seconds)"
            error={errors.config?.fault?.duration_seconds?.message}
            hint="Expires independently of the experiment worker."
          >
            <input
              type="number"
              min="1"
              max="30"
              step="0.5"
              {...register("config.fault.duration_seconds", { valueAsNumber: true })}
            />
          </FormField>
        </div>
      </fieldset>
      <fieldset className="wizard-section" hidden={step !== 2}>
        <legend className="sr-only">Invariant and workflow constraints</legend>
        {invariants.error ? (
          <p className="inline-error" role="alert">
            Cannot load registered invariants: {invariants.error.message}
          </p>
        ) : invariants.isPending ? (
          <p className="muted">Loading invariants…</p>
        ) : !invariants.data.length ? (
          <p className="muted">
            No registered invariants. Seed the demo or register a rule in settings before running.
          </p>
        ) : (
          <div className="invariant-options">
            {invariants.data.map((invariant) => (
              <label key={invariant.id}>
                <input type="checkbox" value={invariant.id} {...register("config.invariant_ids")} />
                <span>
                  <strong>{invariant.name}</strong>
                  <small>
                    {invariant.rule.kind} · {shortId(invariant.id)}
                  </small>
                </span>
                <ShieldCheck size={16} />
              </label>
            ))}
          </div>
        )}
        {errors.config?.invariant_ids && (
          <p className="field-error" role="alert">
            {errors.config.invariant_ids.message}
          </p>
        )}
        <details className="advanced-config">
          <summary>
            <SlidersHorizontal size={14} />
            Consistency window & workflow inputs
            <ChevronDown size={14} />
          </summary>
          <div className="form-grid">
            <FormField
              label="Maximum duration (seconds)"
              error={errors.config?.max_duration_seconds?.message}
            >
              <input
                type="number"
                min="10"
                max="90"
                {...register("config.max_duration_seconds", { valueAsNumber: true })}
              />
            </FormField>
            <FormField
              label="Consistency window (seconds)"
              error={errors.config?.consistency_seconds?.message}
            >
              <input
                type="number"
                min="0"
                max="15"
                step="0.1"
                {...register("config.consistency_seconds", { valueAsNumber: true })}
              />
            </FormField>
            <FormField
              label="Observation retry (seconds)"
              error={errors.config?.retry_seconds?.message}
            >
              <input
                type="number"
                min=".05"
                max="2"
                step=".05"
                {...register("config.retry_seconds", { valueAsNumber: true })}
              />
            </FormField>
            <FormField label="Random seed" error={errors.config?.seed?.message}>
              <input
                type="number"
                min="0"
                max="2147483647"
                {...register("config.seed", { valueAsNumber: true })}
              />
            </FormField>
            <FormField label="Fake payment amount" error={errors.config?.amount?.message}>
              <input
                type="number"
                min="1"
                max="10000"
                {...register("config.amount", { valueAsNumber: true })}
              />
            </FormField>
            <FormField label="Stock quantity" error={errors.config?.quantity?.message}>
              <input
                type="number"
                min="1"
                max="10"
                {...register("config.quantity", { valueAsNumber: true })}
              />
            </FormField>
          </div>
        </details>
        {errors.config?.max_duration_seconds && (
          <p className="field-error" role="alert">
            {errors.config.max_duration_seconds.message}
          </p>
        )}
      </fieldset>
      {step === 3 && (
        <div className="wizard-review" aria-label="Experiment scope review">
          <div className="notice notice-neutral">
            <ShieldCheck size={19} />
            <div>
              <strong>Bounded sandbox execution</strong>
              <span>
                The demo is reset under an exclusive lease. Fault cleanup is automatic; committed
                business effects remain evidence.
              </span>
            </div>
          </div>
          <dl>
            <div>
              <dt>Definition</dt>
              <dd>{values.name}</dd>
            </div>
            <div>
              <dt>Target boundary</dt>
              <dd>payment</dd>
            </div>
            <div>
              <dt>Fault / phase</dt>
              <dd>
                {values.config.fault.kind} / {values.config.fault.phase}
              </dd>
            </div>
            <div>
              <dt>Fault lease</dt>
              <dd>{values.config.fault.duration_seconds} seconds</dd>
            </div>
            <div>
              <dt>Latency</dt>
              <dd>{values.config.fault.delay_seconds} seconds</dd>
            </div>
            <div>
              <dt>Run deadline</dt>
              <dd>{values.config.max_duration_seconds} seconds</dd>
            </div>
            <div>
              <dt>Consistency window</dt>
              <dd>{values.config.consistency_seconds} seconds</dd>
            </div>
            <div>
              <dt>Selected invariants</dt>
              <dd>{values.config.invariant_ids.length}</dd>
            </div>
          </dl>
          <p className="microcopy">
            {invariants.data
              ?.filter((rule) => values.config.invariant_ids.includes(rule.id))
              .map((rule) => rule.name)
              .join(" · ")}
          </p>
        </div>
      )}
      {step === 4 && accepted && (
        <div className="wizard-accepted">
          <ShieldCheck size={31} />
          <h3>Execution accepted</h3>
          <p>
            The backend persisted this run. Its current status and invariant outcomes appear in the
            execution monitor.
          </p>
          <code>{accepted.id}</code>
          <Button type="button" variant="secondary" onClick={() => setStep(0)}>
            Configure another experiment
          </Button>
        </div>
      )}
      {step < 4 && (
        <div className="wizard-navigation">
          <span>Progress is configuration only. Faults start after confirmation.</span>
          {step > 0 && (
            <Button type="button" variant="secondary" onClick={() => setStep(step - 1)}>
              Back
            </Button>
          )}
          {step < 3 && (
            <Button
              type="button"
              onClick={() => {
                void nextStep();
              }}
              disabled={step === 0 && !target}
            >
              Continue <ArrowRight size={14} />
            </Button>
          )}
        </div>
      )}
      <div className="builder-actions" hidden={step !== 3}>
        <Button
          type="button"
          variant="secondary"
          disabled={save.isPending || start.isPending}
          control="execute"
          onClick={handleSubmit((values) => save.mutate(values), revealInvalid)}
        >
          <Save size={14} />
          {save.isPending ? "Saving…" : "Save new definition"}
        </Button>
        <Button
          control="execute"
          type="submit"
          disabled={start.isPending || save.isPending || !!invariants.error}
        >
          <Play size={14} />
          {start.isPending ? "Submitting…" : "Review & run"}
        </Button>
      </div>
      {(start.error || save.error) && (
        <div className="notice notice-warning" role="alert">
          {(start.error ?? save.error)?.message}
        </div>
      )}
      <Confirm
        open={!!review}
        onOpenChange={(open) => {
          if (!open) setReview(null);
        }}
        title="Inject a controlled sandbox fault?"
        description={`Project: ${projects.find((project) => project.id === projectId)?.name ?? projectId}. Target: payment. Fault: ${review?.config.fault.kind}. TTL: ${review?.config.fault.duration_seconds}s. Run deadline: ${review?.config.max_duration_seconds}s. This resets demo orders, payments and inventory. Previously committed business effects are not compensated. ${isDirty || !definition ? "Your configuration will be persisted as a new definition." : "The existing definition will be used."}`}
        action="Start sandbox experiment"
        pending={start.isPending}
        onConfirm={() => {
          if (review) start.mutate(review);
        }}
      />
    </form>
  );
}
export function ExperimentStudio() {
  const access = useAccess();
  const { projectId } = useProject();
  const params = useSearchParams();
  const router = useRouter();
  const definitions = useExperiments(projectId);
  const [chosen, setChosen] = useState("");
  const [newDefinition, setNewDefinition] = useState(false);
  const [offset, setOffset] = useState(0);
  const [status, setStatus] = useState("");
  const runs = useRuns(projectId, offset, status);
  const runId = params.get("run") ?? "";
  const selected =
    definitions.data?.find(
      (definition) => definition.id === (chosen || params.get("experiment")),
    ) ?? definitions.data?.[0];
  if (definitions.isPending) return <Loading />;
  if (definitions.error)
    return (
      <ErrorState
        error={definitions.error}
        retry={() => {
          void definitions.refetch();
        }}
      />
    );
  return (
    <div className="page-stack">
      <div className="studio-grid">
        <Panel
          title={access.recorded_demo ? "Recorded experiment definition" : "Experiment builder"}
          subtitle="Define the fault. Declare the constraint. Verify the outcome."
          action={
            <Button
              control="manage"
              variant="ghost"
              size="sm"
              onClick={() => setNewDefinition(true)}
            >
              <Plus size={14} />
              New
            </Button>
          }
        >
          <div className="definition-selector">
            <label htmlFor="definition-select">Registered definition</label>
            <select
              id="definition-select"
              value={newDefinition ? "" : (selected?.id ?? "")}
              onChange={(event) => {
                setChosen(event.target.value);
                setNewDefinition(!event.target.value);
              }}
            >
              {!access.recorded_demo && <option value="">Create a new definition</option>}
              {definitions.data.map((definition) => (
                <option key={definition.id} value={definition.id}>
                  {definition.name}
                </option>
              ))}
            </select>
          </div>
          {access.recorded_demo ? (
            <>
              <p className="microcopy">
                Inspection only. The recorded fault configuration cannot be executed or modified in
                this frontend demo.
              </p>
              <JsonView value={selected?.config ?? {}} label="Recorded experiment configuration" />
            </>
          ) : (
            <Builder
              key={`${projectId}:${newDefinition ? "new" : (selected?.id ?? "new")}`}
              definition={newDefinition ? undefined : selected}
              onSaved={(id) => {
                setChosen(id);
                setNewDefinition(false);
              }}
              onRun={(run) => router.push(`/experiments?run=${run.id}`)}
            />
          )}
        </Panel>
        <div className="studio-monitor">
          {runId ? (
            <RunMonitor key={runId} runId={runId} />
          ) : (
            <Panel
              title="Execution monitor"
              subtitle="A clear record of every controlled experiment"
            >
              <div className="monitor-empty">
                <div className="orbit-icon">
                  <FlaskConical size={30} />
                </div>
                <h3>
                  {access.recorded_demo ? "Live execution unavailable" : "Ready when you are"}
                </h3>
                <p>
                  {access.recorded_demo
                    ? "Choose a historical run below to inspect its recorded lifecycle, findings and evidence. This demo has no live experiment engine."
                    : "Choose a definition and review its fault scope. Live lifecycle events and invariant outcomes will appear here after the backend accepts the run."}
                </p>
                <div className="monitor-stages">
                  <span>INJECT</span>
                  <ArrowRight size={12} />
                  <span>OBSERVE</span>
                  <ArrowRight size={12} />
                  <span>VERIFY</span>
                </div>
              </div>
            </Panel>
          )}
          <div className="safety-card">
            <ShieldCheck size={18} />
            <div>
              <strong>Safety is part of the experiment</strong>
              <p>
                Fixed local targets. Bounded leases. Automatic fault expiry. A finding requires
                authoritative evidence, not an HTTP error alone.
              </p>
            </div>
          </div>
        </div>
      </div>
      <Panel
        title="Execution history"
        subtitle="Project-wide history · 25 executions per page"
        action={
          <select
            aria-label="Filter execution status"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setOffset(0);
            }}
          >
            <option value="">All statuses</option>
            {["CREATED", "QUEUED", "RUNNING", "VERIFYING", "COMPLETED", "FAILED", "CANCELLED"].map(
              (value) => (
                <option key={value}>{value}</option>
              ),
            )}
          </select>
        }
      >
        {runs.error ? (
          <ErrorState
            error={runs.error}
            retry={() => {
              void runs.refetch();
            }}
          />
        ) : runs.data?.items.length ? (
          <>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Run ID</th>
                    <th>Fault boundary</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>Open</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.data.items.map((run) => (
                    <tr key={run.id}>
                      <td>
                        <code>{shortId(run.id)}</code>
                      </td>
                      <td>
                        {asText(asObject(run.config.fault).target)}
                        <small className="cell-subtitle">
                          {asText(asObject(run.config.fault).kind)}
                        </small>
                      </td>
                      <td>
                        <StatusBadge status={run.status} small />
                      </td>
                      <td className="muted">{dateTime(run.created_at)}</td>
                      <td>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => router.push(`/experiments?run=${run.id}`)}
                        >
                          Monitor
                          <ArrowRight size={13} />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span>
                {offset + 1}–{Math.min(offset + 25, runs.data.total)} of {runs.data.total}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={!offset}
                onClick={() => setOffset(Math.max(0, offset - 25))}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={offset + 25 >= runs.data.total}
                onClick={() => setOffset(offset + 25)}
              >
                Next
              </Button>
            </div>
          </>
        ) : runs.isPending ? (
          <p className="panel-empty">Loading execution history…</p>
        ) : (
          <EmptyState
            title="No matching executions"
            description="Run an experiment or change the status filter."
          />
        )}
      </Panel>
    </div>
  );
}
