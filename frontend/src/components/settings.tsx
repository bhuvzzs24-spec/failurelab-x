"use client";
import { useAccess } from "./access";
import { RecordedDemoSettings } from "./recorded-demo-settings";
import { useGraph, useInvariants } from "@/hooks/data";
import { api, registration, request } from "@/lib/api";
import { shortId } from "@/lib/utils";
import type { Schema } from "@/types/domain";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Database, GitBranch, Globe, KeyRound, Plus, Server } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { JsonView } from "./evidence-common";
import { useProject } from "./providers";
import { Button } from "./ui/button";
import { ErrorState, Panel } from "./ui/states";
const projectSchema = z.object({ name: z.string().trim().min(1).max(120) });
const serviceSchema = z.object({
  name: z.enum(["gateway", "order", "payment", "inventory"]),
  version: z.string().trim().min(1).max(128),
  method: z.enum(["GET", "POST", "PUT", "DELETE"]),
  path: z.string().regex(/^\/[a-zA-Z0-9_/{}/-]{0,150}$/),
  resource: z.string().max(128),
});
export function Settings() {
  const access = useAccess();
  return access.recorded_demo ? <RecordedDemoSettings /> : <ConnectedSettings />;
}
function ConnectedSettings() {
  const { projects, projectId, setProjectId } = useProject();
  const client = useQueryClient();
  const graph = useGraph(projectId);
  const invariants = useInvariants(projectId);
  const capabilities = useQuery({ queryKey: ["capabilities"], queryFn: api.capabilities });
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => request<{ status: string; version: string }>("health"),
  });
  const ready = useQuery({
    queryKey: ["readiness"],
    queryFn: () => request<{ status: string }>("ready"),
    retry: false,
  });
  const [contrast, setContrast] = useState(() =>
    typeof window !== "undefined"
      ? (localStorage.getItem("failurelab.contrast") ?? "standard")
      : "standard",
  );
  useEffect(() => {
    document.documentElement.dataset.contrast = contrast;
    localStorage.setItem("failurelab.contrast", contrast);
  }, [contrast]);
  const projectForm = useForm<z.infer<typeof projectSchema>>({
    resolver: zodResolver(projectSchema),
    defaultValues: { name: "" },
  });
  const serviceForm = useForm<z.infer<typeof serviceSchema>>({
    resolver: zodResolver(serviceSchema),
    defaultValues: {
      name: "gateway",
      version: "",
      method: "POST",
      path: "/checkout",
      resource: "",
    },
  });
  const create = useMutation({
    mutationFn: api.createProject,
    onSuccess: (project) => {
      client.setQueryData<Schema["ProjectOut"][]>(["projects"], (old) => [
        ...(old ?? []).filter((item) => item.id !== project.id),
        project,
      ]);
      toast.success("Project registered");
      setProjectId(project.id);
      void client.invalidateQueries({ queryKey: ["projects"] });
      projectForm.reset();
    },
    onError: (error) => toast.error(error.message),
  });
  const service = useMutation({
    mutationFn: (values: z.infer<typeof serviceSchema>) =>
      api.createService(projectId, {
        name: values.name,
        version: values.version,
        operations: [{ method: values.method, path: values.path }],
        resources: values.resource ? [values.resource] : [],
      }),
    onSuccess: () => {
      toast.success("Service registered");
      void client.invalidateQueries({ queryKey: ["graph", projectId] });
      void client.invalidateQueries({ queryKey: ["overview", projectId] });
    },
    onError: (error) => toast.error(error.message),
  });
  const [ruleName, setRuleName] = useState("");
  const [ruleText, setRuleText] = useState(
    '{"kind":"compare","left":{"path":"payment.amount"},"op":"eq","right":{"path":"order.amount"}}',
  );
  const [ruleError, setRuleError] = useState("");
  const invariant = useMutation({
    mutationFn: (rule: Schema["InvariantCreate"]["rule"]) =>
      registration.invariant(projectId, { name: ruleName, rule }),
    onSuccess: () => {
      toast.success("Invariant persisted");
      setRuleName("");
      void client.invalidateQueries({ queryKey: ["invariants", projectId] });
    },
    onError: (error) => toast.error(error.message),
  });
  const [dependency, setDependency] = useState({
    source_id: "",
    target_id: "",
    kind: "http" as "http" | "shared_resource" | "workflow",
    operation: "",
    workflow: "checkout",
  });
  const edge = useMutation({
    mutationFn: () => registration.dependency(projectId, dependency),
    onSuccess: () => {
      toast.success("Dependency registered");
      void client.invalidateQueries({ queryKey: ["graph", projectId] });
    },
    onError: (error) => toast.error(error.message),
  });
  return (
    <div className="page-stack">
      <div className="two-columns">
        <Panel title="Project registry" subtitle="Create projects; existing records are preserved">
          <div className="project-registry">
            {projects.map((project) => (
              <button
                key={project.id}
                onClick={() => setProjectId(project.id)}
                className={project.id === projectId ? "project-active" : ""}
              >
                <span className="workspace-avatar">
                  <GitBranch size={16} />
                </span>
                <span>
                  <strong>{project.name}</strong>
                  <small>{shortId(project.id)}</small>
                </span>
                {project.id === projectId && <Check size={16} />}
              </button>
            ))}
          </div>
          <form
            className="inline-form"
            onSubmit={projectForm.handleSubmit((values) => create.mutate(values))}
          >
            <label className="form-field">
              <span>New project name</span>
              <input placeholder="Name your system" {...projectForm.register("name")} />
              {projectForm.formState.errors.name && (
                <small role="alert" className="field-error">
                  {projectForm.formState.errors.name.message}
                </small>
              )}
            </label>
            <Button control="manage" disabled={create.isPending} type="submit">
              <Plus size={14} />
              {create.isPending ? "Creating…" : "Create project"}
            </Button>
          </form>
        </Panel>
        <Panel title="API connection" subtitle="Observed service liveness and dependency readiness">
          <div className="connection-row">
            <Globe size={17} />
            <span>Backend API</span>
            <strong className={health.data ? "text-emerald" : "text-amber"}>
              {health.isPending ? "Checking" : health.data ? "Connected" : "Unavailable"}
            </strong>
          </div>
          <div className="connection-row">
            <Database size={17} />
            <span>Database & broker</span>
            <strong className={ready.data ? "text-emerald" : "text-amber"}>
              {ready.isPending ? "Checking" : ready.data ? "Ready" : "Not ready"}
            </strong>
          </div>
          <div className="connection-row">
            <Server size={17} />
            <span>Engine revision</span>
            <code>{health.data?.version ?? "Not observed"}</code>
          </div>
          <div className="notice notice-neutral">
            <KeyRound size={16} />
            <p>
              Credentials are server-side environment configuration. They cannot be viewed or edited
              in this interface.
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              void health.refetch();
              void ready.refetch();
            }}
          >
            Check connection
          </Button>
        </Panel>
      </div>
      {projectId && (
        <>
          <Panel
            title="Registered services"
            subtitle="Local allowlisted identities only; registration never accepts a destination URL"
          >
            {graph.error ? (
              <ErrorState
                error={graph.error}
                retry={() => {
                  void graph.refetch();
                }}
              />
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Service</th>
                      <th>Version</th>
                      <th>Operations</th>
                      <th>Shared resources</th>
                    </tr>
                  </thead>
                  <tbody>
                    {graph.data?.nodes.map((node) => (
                      <tr key={node.id}>
                        <td>
                          <strong>{node.name}</strong>
                          <small className="cell-subtitle mono">{shortId(node.id)}</small>
                        </td>
                        <td className="mono">{node.version}</td>
                        <td>
                          {(node.operations ?? [])
                            .map((operation) => `${operation.method} ${operation.path}`)
                            .join(", ") || "None"}
                        </td>
                        <td>{(node.resources ?? []).join(", ") || "None"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <details className="registration-details">
              <summary>
                <Plus size={14} />
                Register a managed service
              </summary>
              <form
                onSubmit={serviceForm.handleSubmit((values) => service.mutate(values))}
                className="registration-form"
              >
                <div className="form-grid">
                  <label className="form-field">
                    <span>Service identity</span>
                    <select {...serviceForm.register("name")}>
                      {["gateway", "order", "payment", "inventory"].map((name) => (
                        <option key={name}>{name}</option>
                      ))}
                    </select>
                  </label>
                  <label className="form-field">
                    <span>Service version</span>
                    <input
                      placeholder="Image revision or build identifier"
                      {...serviceForm.register("version")}
                    />
                  </label>
                  <label className="form-field">
                    <span>HTTP method</span>
                    <select {...serviceForm.register("method")}>
                      {["GET", "POST", "PUT", "DELETE"].map((method) => (
                        <option key={method}>{method}</option>
                      ))}
                    </select>
                  </label>
                  <label className="form-field">
                    <span>Operation path</span>
                    <input {...serviceForm.register("path")} />
                  </label>
                  <label className="form-field">
                    <span>Shared resource label (optional)</span>
                    <input {...serviceForm.register("resource")} />
                  </label>
                </div>
                {Object.values(serviceForm.formState.errors).map((error, index) => (
                  <p key={index} className="field-error" role="alert">
                    {error.message}
                  </p>
                ))}
                <Button control="manage" disabled={service.isPending}>
                  Register service
                </Button>
              </form>
            </details>
          </Panel>
          <div className="two-columns">
            <Panel
              title="Dependency registration"
              subtitle="Explicit directed edges; no automatic discovery"
            >
              <form
                className="registration-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  edge.mutate();
                }}
              >
                <div className="form-grid">
                  <label className="form-field">
                    <span>Source service</span>
                    <select
                      required
                      value={dependency.source_id}
                      onChange={(event) =>
                        setDependency({ ...dependency, source_id: event.target.value })
                      }
                    >
                      <option value="">Select source</option>
                      {graph.data?.nodes.map((node) => (
                        <option key={node.id} value={node.id}>
                          {node.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="form-field">
                    <span>Target service</span>
                    <select
                      required
                      value={dependency.target_id}
                      onChange={(event) =>
                        setDependency({ ...dependency, target_id: event.target.value })
                      }
                    >
                      <option value="">Select target</option>
                      {graph.data?.nodes.map((node) => (
                        <option key={node.id} value={node.id}>
                          {node.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="form-field">
                    <span>Relationship kind</span>
                    <select
                      value={dependency.kind}
                      onChange={(event) =>
                        setDependency({
                          ...dependency,
                          kind: event.target.value as typeof dependency.kind,
                        })
                      }
                    >
                      {["http", "shared_resource", "workflow"].map((kind) => (
                        <option key={kind}>{kind}</option>
                      ))}
                    </select>
                  </label>
                  <label className="form-field">
                    <span>Operation</span>
                    <input
                      required
                      maxLength={160}
                      value={dependency.operation}
                      onChange={(event) =>
                        setDependency({ ...dependency, operation: event.target.value })
                      }
                    />
                  </label>
                  <label className="form-field">
                    <span>Workflow label</span>
                    <input
                      required
                      maxLength={80}
                      value={dependency.workflow}
                      onChange={(event) =>
                        setDependency({ ...dependency, workflow: event.target.value })
                      }
                    />
                  </label>
                </div>
                <Button
                  variant="secondary"
                  control="manage"
                  disabled={edge.isPending || dependency.source_id === dependency.target_id}
                >
                  Register dependency
                </Button>
              </form>
            </Panel>
            <Panel
              title="Executable invariants"
              subtitle={`${invariants.data?.length ?? 0} loaded registrations; backend validates the safe rule AST`}
            >
              <div className="registered-rules">
                {invariants.data?.map((rule) => (
                  <details key={rule.id}>
                    <summary>
                      {rule.name}
                      <span className="subtle-chip">{rule.rule.kind}</span>
                    </summary>
                    <JsonView value={rule.rule} />
                  </details>
                ))}
              </div>
              {invariants.error && (
                <p role="alert" className="inline-error">
                  {invariants.error.message}
                </p>
              )}
              <details className="registration-details">
                <summary>
                  <Plus size={14} />
                  Register a declarative rule
                </summary>
                <form
                  className="registration-form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    setRuleError("");
                    try {
                      const rule: Schema["InvariantCreate"]["rule"] = JSON.parse(ruleText);
                      invariant.mutate(rule);
                    } catch {
                      setRuleError(
                        "Enter valid JSON. Rules are never executed as JavaScript or Python.",
                      );
                    }
                  }}
                >
                  <label className="form-field">
                    <span>Invariant name</span>
                    <input
                      required
                      maxLength={120}
                      value={ruleName}
                      onChange={(event) => setRuleName(event.target.value)}
                    />
                  </label>
                  <label className="form-field">
                    <span>Safe declarative rule JSON</span>
                    <textarea
                      className="mono"
                      rows={7}
                      maxLength={16000}
                      required
                      value={ruleText}
                      onChange={(event) => setRuleText(event.target.value)}
                    />
                  </label>
                  {ruleError && (
                    <p className="field-error" role="alert">
                      {ruleError}
                    </p>
                  )}
                  <Button control="manage" disabled={invariant.isPending} variant="secondary">
                    Register invariant
                  </Button>
                </form>
              </details>
            </Panel>
          </div>
        </>
      )}
      <div className="two-columns">
        <Panel title="Execution safety" subtitle="Capabilities reported by the connected backend">
          {capabilities.error ? (
            <ErrorState
              error={capabilities.error}
              retry={() => {
                void capabilities.refetch();
              }}
            />
          ) : capabilities.data ? (
            <>
              <dl className="detail-list">
                <div>
                  <dt>Managed sandbox</dt>
                  <dd>{capabilities.data.sandbox_id}</dd>
                </div>
                <div>
                  <dt>Allowed service identities</dt>
                  <dd>{capabilities.data.allowed_services.join(", ")}</dd>
                </div>
                <div>
                  <dt>Fault targets</dt>
                  <dd>{capabilities.data.fault_targets.join(", ")}</dd>
                </div>
                <div>
                  <dt>Maximum fault lease</dt>
                  <dd>{capabilities.data.max_fault_seconds}s</dd>
                </div>
                <div>
                  <dt>Maximum run duration</dt>
                  <dd>{capabilities.data.max_run_seconds}s</dd>
                </div>
              </dl>
              <p className="microcopy">
                Read-only safety limits. No production targets, arbitrary shell execution, secret
                editing, or unsafe network destinations are offered.
              </p>
            </>
          ) : (
            <p className="panel-empty">Loading capabilities…</p>
          )}
        </Panel>
        <Panel
          title="Interface preferences"
          subtitle="Local browser preferences; execution settings remain unchanged"
        >
          <label className="form-field">
            <span>Dark theme contrast</span>
            <select value={contrast} onChange={(event) => setContrast(event.target.value)}>
              <option value="standard">Midnight · standard contrast</option>
              <option value="high">Midnight · high contrast</option>
            </select>
          </label>
          <p className="body-copy">
            Keyboard shortcuts: <kbd>⌘ / Ctrl K</kbd> opens navigation. Dialogs support Escape and
            keyboard focus management. Motion follows your operating system&apos;s reduced-motion
            preference.
          </p>
          <p className="microcopy">
            Project, service and invariant registration are supported. Deletion, secret management
            and safety-limit editing are not exposed by the current backend.
          </p>
        </Panel>
      </div>
    </div>
  );
}
