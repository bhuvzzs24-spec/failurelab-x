"use client";
import { useOverview, useSummary } from "@/hooks/data";
import { asObject, asText, relativeTime, shortId } from "@/lib/utils";
import type { Artifact } from "@/types/domain";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Box,
  FlaskConical,
  GitBranch,
  ShieldAlert,
  Zap,
} from "lucide-react";
import Link from "next/link";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useProject } from "./providers";
import { SystemGraph } from "./system-graph";
import { EmptyState, ErrorState, Loading, Panel } from "./ui/states";
import { StatusBadge } from "./ui/status";
export function TimelineList({ events, limit = 8 }: { events: Artifact[]; limit?: number }) {
  if (!events.length) return <p className="panel-empty">No recorded execution events.</p>;
  return (
    <ol className="timeline-list">
      {events
        .slice(-limit)
        .reverse()
        .map((event) => (
          <li key={event.id}>
            <span
              className={`timeline-point ${event.kind === "evaluation" ? "point-violet" : ""}`}
            />
            <div>
              <strong>{event.kind.replaceAll("_", " ")}</strong>
              <span>
                {asText(
                  event.payload.status,
                  asText(
                    event.payload.stage,
                    event.payload.activated_at
                      ? "Fault activated"
                      : event.payload.removed_at
                        ? "Fault removed"
                        : "Evidence recorded",
                  ),
                )}
              </span>
            </div>
            <time dateTime={new Date(event.created_at * 1000).toISOString()}>
              {relativeTime(event.created_at)}
            </time>
          </li>
        ))}
    </ol>
  );
}
export function Dashboard() {
  const { projectId } = useProject();
  const query = useOverview(projectId);
  const overview = query.data;
  const latest = useSummary(overview?.latest_runs[0]?.id ?? "");
  if (query.isPending) return <Loading />;
  if (query.error)
    return (
      <ErrorState
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      />
    );
  if (!overview) return null;
  const metrics = [
    {
      label: "Registered services",
      value: overview.service_count,
      icon: GitBranch,
      detail: "Explicitly modeled dependencies",
      tone: "violet",
    },
    {
      label: "Total experiments",
      value: overview.run_count,
      icon: FlaskConical,
      detail: `${overview.experiment_count} registered definitions`,
      tone: "cyan",
    },
    {
      label: "Active executions",
      value: overview.active_run_count,
      icon: Activity,
      detail: "Created, queued, running, verifying",
      tone: "emerald",
    },
    {
      label: "Invariant violations",
      value: overview.violation_count,
      icon: ShieldAlert,
      detail: "Persisted deterministic FAIL findings",
      tone: "red",
    },
  ];
  const faults =
    latest.data?.artifacts.filter((artifact) => artifact.kind === "fault_schedule") ?? [];
  return (
    <div className="page-stack">
      <div className="metric-grid">
        {metrics.map(({ label, value, icon: Icon, detail, tone }) => (
          <div className={`metric-card metric-${tone}`} key={label}>
            <div className="metric-top">
              <span>{label}</span>
              <span className={`metric-icon ${tone}`}>
                <Icon size={16} />
              </span>
            </div>
            <strong>{value.toLocaleString()}</strong>
            <small>{detail}</small>
          </div>
        ))}
      </div>
      <Panel
        title="Research activity"
        subtitle="Persisted research jobs and deduplicated invariant signatures · refreshed from the backend"
      >
        <div className="research-summary">
          <span>
            <strong>{overview.research_job_count ?? "—"}</strong> research jobs
          </span>
          <span>
            <strong>{overview.active_research_count ?? "—"}</strong> active research jobs
          </span>
          <span>
            <strong>{overview.research_violation_count ?? "—"}</strong> research violation patterns
          </span>
          <Link href="/explorer">
            Open adaptive explorer <ArrowRight size={14} />
          </Link>
        </div>
        <p className="microcopy">
          The four cards above describe the original experiment engine. Research findings are
          counted separately to preserve their deduplication semantics.
        </p>
      </Panel>
      <div className="dashboard-primary">
        <Panel
          title="System topology"
          subtitle="The system you know. The boundaries you can test."
          className="graph-panel"
        >
          <SystemGraph compact />
        </Panel>
        <Panel
          title="Experiment activity"
          subtitle="Run creation · last 14 days · UTC"
          action={<span className="subtle-chip">14 days</span>}
        >
          <div className="chart-total">
            <strong>{overview.activity.reduce((total, point) => total + point.runs, 0)}</strong>
            <span>recorded runs</span>
          </div>
          <div
            className="activity-chart"
            role="img"
            aria-label={`Run activity: ${overview.activity.map((point) => `${point.day}: ${point.runs}`).join(", ")}`}
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={overview.activity}
                margin={{ left: -24, right: 8, top: 8, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="activity-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#8b7cf8" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#8b7cf8" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#242b3e" vertical={false} strokeDasharray="3 4" />
                <XAxis
                  dataKey="day"
                  tickFormatter={(value: string) => value.slice(5)}
                  minTickGap={32}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#8e9bb1", fontSize: 10 }}
                />
                <YAxis
                  allowDecimals={false}
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "#8e9bb1", fontSize: 10 }}
                />
                <Tooltip
                  contentStyle={{
                    background: "#161d2c",
                    border: "1px solid #384057",
                    borderRadius: 10,
                    color: "#eef1ff",
                  }}
                />
                <Area
                  dataKey="runs"
                  type="monotone"
                  stroke="#a499ff"
                  fill="url(#activity-fill)"
                  strokeWidth={2}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="chart-statuses">
            {Object.entries(overview.status_counts).map(([status, count]) => (
              <span key={status}>
                <StatusBadge small status={status} />
                <b>{count}</b>
              </span>
            ))}
            {!overview.run_count && (
              <span className="muted">Run an experiment to begin recording activity.</span>
            )}
          </div>
        </Panel>
      </div>
      <div className="dashboard-secondary">
        <Panel
          title="Recent experiments"
          subtitle="Real executions, from creation to verification"
          action={
            <Link href="/experiments" className="text-link">
              View studio <ArrowUpRight size={13} />
            </Link>
          }
        >
          {overview.latest_runs.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Execution</th>
                    <th>Fault</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th>
                      <span className="sr-only">Open</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {overview.latest_runs.slice(0, 5).map((run) => (
                    <tr key={run.id}>
                      <td>
                        <Link className="table-run" href={`/experiments?run=${run.id}`}>
                          <span className="small-icon">
                            <FlaskConical size={14} />
                          </span>
                          <span>
                            <strong>{shortId(run.id)}</strong>
                            <small>{run.config && asText(asObject(run.config.fault).target)}</small>
                          </span>
                        </Link>
                      </td>
                      <td className="mono muted">{asText(asObject(run.config.fault).kind)}</td>
                      <td>
                        <StatusBadge small status={run.status} />
                      </td>
                      <td className="muted nowrap">{relativeTime(run.created_at)}</td>
                      <td>
                        <Link
                          href={`/experiments?run=${run.id}`}
                          aria-label={`Open run ${shortId(run.id)}`}
                        >
                          <ArrowUpRight size={15} />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="No executions yet"
              description="Launch a controlled experiment against the registered sandbox."
              href="/experiments"
              action="Open experiment studio"
            />
          )}
        </Panel>
        <Panel
          title="Latest execution timeline"
          subtitle={
            overview.latest_runs[0]
              ? `Run ${shortId(overview.latest_runs[0].id)}`
              : "Waiting for your first execution"
          }
        >
          {latest.error ? (
            <p className="inline-error">Timeline could not be loaded.</p>
          ) : latest.data ? (
            <TimelineList events={latest.data.artifacts} limit={5} />
          ) : (
            <p className="panel-empty">Events will appear after an experiment starts.</p>
          )}
        </Panel>
      </div>
      <div className="dashboard-tertiary">
        <Panel
          title="Recent findings"
          subtitle="Business correctness, verified against executable rules"
          action={
            <Link href="/findings" className="text-link">
              Investigate <ArrowUpRight size={13} />
            </Link>
          }
        >
          {overview.latest_findings.length ? (
            <div className="finding-preview-list">
              {overview.latest_findings.slice(0, 3).map((finding) => (
                <Link
                  key={finding.id}
                  href={`/findings?run=${finding.run_id}&finding=${finding.id}`}
                >
                  <span className="finding-mark">
                    <ShieldAlert size={17} />
                  </span>
                  <div>
                    <strong>{finding.summary}</strong>
                    <small>
                      Invariant {shortId(finding.invariant_id)} · run {shortId(finding.run_id)}
                    </small>
                  </div>
                  <StatusBadge status="FAIL" small />
                  <ArrowRight size={15} />
                </Link>
              ))}
            </div>
          ) : (
            <div className="quiet-state">
              <ShieldAlert size={23} />
              <div>
                <strong>No invariant violations recorded</strong>
                <p>This is an absence of findings, not a claim that the system is failure-free.</p>
              </div>
            </div>
          )}
        </Panel>
        <Panel
          title="Evidence & fault activity"
          subtitle="Recorded facts from the latest execution"
        >
          <div className="evidence-metric">
            <Box size={17} />
            <strong>{overview.artifact_count}</strong>
            <span>persisted artifacts across this project</span>
          </div>
          {faults.length ? (
            faults.map((fault) => (
              <div className="fault-record" key={fault.id}>
                <Zap size={13} />
                <span>
                  {fault.payload.activated_at
                    ? `${asText(asObject(fault.payload.fault).kind)} activated`
                    : "Fault removed"}
                </span>
                <time>{relativeTime(fault.created_at)}</time>
              </div>
            ))
          ) : (
            <p className="panel-empty">No fault schedule recorded in the latest run.</p>
          )}
          <p className="microcopy">
            Recorded activity does not assert a fault is currently active.
          </p>
        </Panel>
      </div>
    </div>
  );
}
